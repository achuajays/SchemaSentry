"""
Traffic observation tools for Agent 1 (Traffic Observer Agent).
These tools observe real API traffic and build observed contracts.
"""

import json
from datetime import datetime
from typing import Any, Optional
from collections import defaultdict

from smolagents import tool

from ..models.schemas import TrafficSample, ObservedSchema, FieldInfo
from ..models.enums import FieldType
from ..utils.pii_masker import PIIMasker


def infer_field_type(value: Any) -> FieldType:
    """
    Infer the field type from an observed value.
    
    Args:
        value: The observed value
        
    Returns:
        Inferred FieldType
    """
    if value is None:
        return FieldType.NULL
    elif isinstance(value, bool):
        return FieldType.BOOLEAN
    elif isinstance(value, int):
        return FieldType.INTEGER
    elif isinstance(value, float):
        return FieldType.NUMBER
    elif isinstance(value, str):
        return FieldType.STRING
    elif isinstance(value, list):
        return FieldType.ARRAY
    elif isinstance(value, dict):
        return FieldType.OBJECT
    else:
        return FieldType.UNKNOWN


@tool
def sample_traffic(
    traffic_data: list[dict],
    sample_rate: float = 0.1,
    mask_pii: bool = True
) -> dict:
    """
    Sample API traffic at a configurable rate with optional PII masking.
    
    This tool takes raw API traffic data and samples it to reduce volume
    while preserving statistical significance. It also masks sensitive
    personally identifiable information (PII) to ensure privacy.
    
    Args:
        traffic_data: List of raw traffic records with keys like 'endpoint', 
                      'method', 'status_code', 'request_body', 'response_body'
        sample_rate: Fraction of traffic to sample (0.0 to 1.0), default 0.1 (10%)
        mask_pii: Whether to mask PII in the sampled data, default True
    
    Returns:
        Dictionary containing the sampled and optionally masked traffic data
    """
    import random
    
    if not traffic_data:
        return {"samples": [], "sample_count": 0, "original_count": 0}
    
    # Sample the traffic
    sample_count = max(1, int(len(traffic_data) * sample_rate))
    sampled = random.sample(traffic_data, min(sample_count, len(traffic_data)))
    
    # Mask PII if requested
    if mask_pii:
        masker = PIIMasker()
        sampled = [masker.mask(record) for record in sampled]
    
    # Convert to TrafficSample objects for validation
    samples = []
    for record in sampled:
        try:
            sample = TrafficSample(
                endpoint=record.get("endpoint", "/unknown"),
                method=record.get("method", "GET").upper(),
                status_code=record.get("status_code", 200),
                request_body=record.get("request_body"),
                response_body=record.get("response_body"),
                headers=record.get("headers"),
                client_id=record.get("client_id"),
                timestamp=datetime.fromisoformat(record["timestamp"]) 
                    if "timestamp" in record else datetime.now(),
            )
            samples.append(sample.model_dump(mode="json"))
        except Exception as e:
            print(f"Warning: Skipping invalid traffic record: {e}")
            continue
    
    result = {
        "samples": samples,
        "sample_count": len(samples),
        "original_count": len(traffic_data),
        "sample_rate": sample_rate,
        "pii_masked": mask_pii,
    }
    
    print(f"Sampled {len(samples)} records from {len(traffic_data)} total (rate: {sample_rate})")
    
    return result


@tool
def extract_field_info(payload: dict, path_prefix: str = "") -> dict:
    """
    Extract field presence, types, and nullability from an API response payload.
    
    This tool recursively analyzes a response payload to extract information
    about each field including its type, whether it can be null, and sample values.
    
    Args:
        payload: The API response payload (dict) to analyze
        path_prefix: Internal use - prefix for nested field paths, leave empty
    
    Returns:
        Dictionary with field information including path, type, nullable status
    """
    if not isinstance(payload, dict):
        return {
            "error": "Payload must be a dictionary",
            "fields": {}
        }
    
    fields = {}
    
    def extract_recursive(data: Any, prefix: str) -> None:
        if isinstance(data, dict):
            for key, value in data.items():
                field_path = f"{prefix}.{key}" if prefix else key
                field_type = infer_field_type(value)
                
                fields[field_path] = {
                    "type": field_type.value,
                    "nullable": value is None,
                    "sample_value": str(value)[:100] if value is not None else None,
                }
                
                # Recurse into nested structures
                if isinstance(value, dict):
                    extract_recursive(value, field_path)
                elif isinstance(value, list) and len(value) > 0:
                    # Check first item in array
                    first_item = value[0]
                    if isinstance(first_item, dict):
                        extract_recursive(first_item, f"{field_path}[]")
        
        elif isinstance(data, list) and len(data) > 0:
            first_item = data[0]
            if isinstance(first_item, dict):
                extract_recursive(first_item, f"{prefix}[]")
    
    extract_recursive(payload, path_prefix)
    
    print(f"Extracted info for {len(fields)} fields from payload")
    
    return {
        "fields": fields,
        "field_count": len(fields),
    }


@tool
def build_observed_schema(
    endpoint: str,
    method: str,
    samples: list[dict],
    time_window_minutes: int = 60
) -> dict:
    """
    Aggregate traffic samples into an observed schema with field presence rates.
    
    This tool analyzes multiple API response samples to build a comprehensive
    observed schema. It tracks how often each field appears (presence rate)
    to detect fields that are sometimes missing.
    
    Args:
        endpoint: The API endpoint path (e.g., "/patients")
        method: HTTP method (GET, POST, etc.)
        samples: List of traffic sample dicts, each with 'response_body' key
        time_window_minutes: Time window for the observation period
    
    Returns:
        Dictionary containing the observed schema with field presence rates
    """
    if not samples:
        return {
            "error": "No samples provided",
            "endpoint": endpoint,
            "method": method,
        }
    
    # Track field occurrences
    field_occurrences: dict[str, int] = defaultdict(int)
    field_types: dict[str, list[FieldType]] = defaultdict(list)
    field_null_count: dict[str, int] = defaultdict(int)
    field_samples: dict[str, list[Any]] = defaultdict(list)
    
    total_samples = 0
    status_codes = set()
    
    for sample in samples:
        response_body = sample.get("response_body")
        if response_body is None:
            continue
        
        total_samples += 1
        status_codes.add(sample.get("status_code", 200))
        
        # Extract fields from this sample
        def process_fields(data: Any, prefix: str = "") -> None:
            if isinstance(data, dict):
                for key, value in data.items():
                    field_path = f"{prefix}.{key}" if prefix else key
                    field_occurrences[field_path] += 1
                    field_types[field_path].append(infer_field_type(value))
                    
                    if value is None:
                        field_null_count[field_path] += 1
                    elif len(field_samples[field_path]) < 3:
                        field_samples[field_path].append(value)
                    
                    # Recurse
                    if isinstance(value, dict):
                        process_fields(value, field_path)
                    elif isinstance(value, list) and value:
                        if isinstance(value[0], dict):
                            process_fields(value[0], f"{field_path}[]")
        
        process_fields(response_body)
    
    if total_samples == 0:
        return {
            "error": "No valid response bodies in samples",
            "endpoint": endpoint,
            "method": method,
        }
    
    # Build observed fields
    observed_fields = {}
    field_presence_rate = {}
    
    for field_path, occurrences in field_occurrences.items():
        presence_rate = occurrences / total_samples
        field_presence_rate[field_path] = round(presence_rate, 4)
        
        # Determine predominant type
        types = field_types[field_path]
        type_counts = defaultdict(int)
        for t in types:
            type_counts[t] += 1
        
        predominant_type = max(type_counts, key=type_counts.get)
        is_mixed = len(set(types)) > 1
        
        null_rate = field_null_count[field_path] / occurrences if occurrences > 0 else 0
        
        observed_fields[field_path] = FieldInfo(
            name=field_path,
            field_type=FieldType.MIXED if is_mixed else predominant_type,
            nullable=null_rate > 0,
            presence_rate=presence_rate,
            sample_values=field_samples[field_path][:3],
        ).model_dump()
    
    # Build the schema
    schema = ObservedSchema(
        endpoint=endpoint,
        method=method.upper(),
        observed_fields=observed_fields,
        field_presence_rate=field_presence_rate,
        sample_count=total_samples,
        status_codes_observed=list(status_codes),
        timestamp_start=datetime.now(),
        timestamp_end=datetime.now(),
    )
    
    print(f"Built observed schema for {method} {endpoint}")
    print(f"  - Analyzed {total_samples} samples")
    print(f"  - Found {len(observed_fields)} unique fields")
    print(f"  - Status codes: {sorted(status_codes)}")
    
    # Highlight fields with low presence rate
    low_presence = {k: v for k, v in field_presence_rate.items() if v < 1.0}
    if low_presence:
        print(f"  - Fields with <100% presence: {low_presence}")
    
    return schema.model_dump(mode="json")
