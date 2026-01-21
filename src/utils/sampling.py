"""
Traffic sampling strategies for API observation.
Provides configurable sampling to handle high-volume traffic.
"""

import random
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional
from collections import defaultdict

from ..models.schemas import TrafficSample


class TrafficSampler:
    """Sample API traffic with various strategies."""
    
    def __init__(
        self,
        sample_rate: float = 0.1,
        max_samples_per_endpoint: int = 1000,
        time_window_minutes: int = 60,
    ):
        """
        Initialize traffic sampler.
        
        Args:
            sample_rate: Fraction of traffic to sample (0.0 to 1.0)
            max_samples_per_endpoint: Maximum samples to keep per endpoint
            time_window_minutes: Time window for aggregation
        """
        self.sample_rate = sample_rate
        self.max_samples_per_endpoint = max_samples_per_endpoint
        self.time_window_minutes = time_window_minutes
        
        # Storage: endpoint -> list of samples
        self._samples: dict[str, list[TrafficSample]] = defaultdict(list)
        self._window_start: datetime = datetime.now()
    
    def should_sample(self, request_id: Optional[str] = None) -> bool:
        """
        Determine if a request should be sampled.
        
        Args:
            request_id: Optional request ID for consistent sampling
            
        Returns:
            True if request should be sampled
        """
        if request_id:
            # Consistent sampling based on request ID hash
            hash_val = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
            return (hash_val % 100) < (self.sample_rate * 100)
        else:
            # Random sampling
            return random.random() < self.sample_rate
    
    def add_sample(self, sample: TrafficSample) -> bool:
        """
        Add a traffic sample to the buffer.
        
        Args:
            sample: Traffic sample to add
            
        Returns:
            True if sample was added, False if skipped
        """
        endpoint_key = f"{sample.method} {sample.endpoint}"
        
        # Check if we're over the limit
        if len(self._samples[endpoint_key]) >= self.max_samples_per_endpoint:
            # Reservoir sampling: replace random existing sample
            idx = random.randint(0, self.max_samples_per_endpoint - 1)
            self._samples[endpoint_key][idx] = sample
        else:
            self._samples[endpoint_key].append(sample)
        
        return True
    
    def get_samples(
        self,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
    ) -> list[TrafficSample]:
        """
        Get collected samples.
        
        Args:
            endpoint: Filter by endpoint path
            method: Filter by HTTP method
            
        Returns:
            List of matching samples
        """
        if endpoint and method:
            key = f"{method} {endpoint}"
            return list(self._samples.get(key, []))
        
        # Return all samples
        all_samples = []
        for samples in self._samples.values():
            all_samples.extend(samples)
        
        return all_samples
    
    def get_endpoints(self) -> list[str]:
        """Get list of observed endpoints."""
        return list(self._samples.keys())
    
    def get_window_info(self) -> dict:
        """Get information about the current sampling window."""
        return {
            "window_start": self._window_start.isoformat(),
            "window_end": datetime.now().isoformat(),
            "window_minutes": self.time_window_minutes,
            "total_samples": sum(len(s) for s in self._samples.values()),
            "endpoints_observed": len(self._samples),
        }
    
    def clear(self) -> None:
        """Clear all samples and reset window."""
        self._samples.clear()
        self._window_start = datetime.now()
    
    def rotate_window(self) -> dict:
        """
        Rotate the sampling window, returning old samples.
        
        Returns:
            Dict with old samples and window info
        """
        old_samples = dict(self._samples)
        old_window = self.get_window_info()
        
        self.clear()
        
        return {
            "samples": old_samples,
            "window": old_window,
        }
    
    def should_rotate(self) -> bool:
        """Check if the current window should be rotated."""
        window_duration = datetime.now() - self._window_start
        return window_duration > timedelta(minutes=self.time_window_minutes)


class AdaptiveSampler(TrafficSampler):
    """
    Adaptive sampler that adjusts rate based on traffic volume.
    """
    
    def __init__(
        self,
        target_samples_per_minute: int = 100,
        min_sample_rate: float = 0.01,
        max_sample_rate: float = 1.0,
        **kwargs
    ):
        """
        Initialize adaptive sampler.
        
        Args:
            target_samples_per_minute: Target number of samples per minute
            min_sample_rate: Minimum sampling rate
            max_sample_rate: Maximum sampling rate
        """
        super().__init__(**kwargs)
        
        self.target_samples_per_minute = target_samples_per_minute
        self.min_sample_rate = min_sample_rate
        self.max_sample_rate = max_sample_rate
        
        self._request_count = 0
        self._last_adjustment = datetime.now()
    
    def should_sample(self, request_id: Optional[str] = None) -> bool:
        """Sample with adaptive rate based on traffic volume."""
        self._request_count += 1
        
        # Adjust rate every minute
        if (datetime.now() - self._last_adjustment).seconds >= 60:
            self._adjust_rate()
        
        return super().should_sample(request_id)
    
    def _adjust_rate(self) -> None:
        """Adjust sampling rate based on recent traffic."""
        elapsed_minutes = max(1, (datetime.now() - self._last_adjustment).seconds / 60)
        requests_per_minute = self._request_count / elapsed_minutes
        
        if requests_per_minute > 0:
            ideal_rate = self.target_samples_per_minute / requests_per_minute
            self.sample_rate = max(
                self.min_sample_rate,
                min(self.max_sample_rate, ideal_rate)
            )
        
        self._request_count = 0
        self._last_adjustment = datetime.now()
