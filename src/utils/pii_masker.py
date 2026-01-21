"""
PII (Personally Identifiable Information) masking utility.
Masks sensitive data in API traffic samples before processing.
"""

import re
from typing import Any


class PIIMasker:
    """Mask PII in API traffic data."""
    
    # Common PII patterns
    PATTERNS = {
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
        "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
        "date_of_birth": re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    }
    
    # Fields that commonly contain PII (case-insensitive)
    SENSITIVE_FIELDS = {
        "password", "passwd", "secret", "token", "api_key", "apikey",
        "authorization", "auth", "credential", "private_key",
        "ssn", "social_security", "tax_id",
        "email", "mail", "phone", "mobile", "telephone",
        "address", "street", "city", "zip", "postal",
        "dob", "date_of_birth", "birthday", "birthdate",
        "credit_card", "card_number", "cvv", "ccv",
        "bank_account", "routing_number",
        "first_name", "last_name", "full_name", "name",
        "ip", "ip_address", "user_agent",
    }
    
    def __init__(self, mask_value: str = "[MASKED]"):
        """
        Initialize PII masker.
        
        Args:
            mask_value: Value to replace PII with
        """
        self.mask_value = mask_value
    
    def mask(self, data: Any, preserve_types: bool = True) -> Any:
        """
        Mask PII in data structure.
        
        Args:
            data: Data to mask (dict, list, or primitive)
            preserve_types: If True, preserve type info for analysis
            
        Returns:
            Masked data
        """
        if isinstance(data, dict):
            return self._mask_dict(data, preserve_types)
        elif isinstance(data, list):
            return self._mask_list(data, preserve_types)
        elif isinstance(data, str):
            return self._mask_string(data)
        else:
            return data
    
    def _mask_dict(self, data: dict, preserve_types: bool) -> dict:
        """Mask dictionary values."""
        masked = {}
        
        for key, value in data.items():
            key_lower = key.lower().replace("-", "_").replace(" ", "_")
            
            # Check if key is sensitive
            if any(s in key_lower for s in self.SENSITIVE_FIELDS):
                if preserve_types:
                    masked[key] = self._get_type_preserving_mask(value)
                else:
                    masked[key] = self.mask_value
            else:
                masked[key] = self.mask(value, preserve_types)
        
        return masked
    
    def _mask_list(self, data: list, preserve_types: bool) -> list:
        """Mask list items."""
        return [self.mask(item, preserve_types) for item in data]
    
    def _mask_string(self, data: str) -> str:
        """Mask PII patterns in strings."""
        result = data
        
        for pattern_name, pattern in self.PATTERNS.items():
            result = pattern.sub(f"[MASKED_{pattern_name.upper()}]", result)
        
        return result
    
    def _get_type_preserving_mask(self, value: Any) -> Any:
        """Return a masked value that preserves type information."""
        if value is None:
            return None
        elif isinstance(value, bool):
            return True  # Preserve boolean type
        elif isinstance(value, int):
            return 0
        elif isinstance(value, float):
            return 0.0
        elif isinstance(value, str):
            return self.mask_value
        elif isinstance(value, list):
            if len(value) > 0:
                return [self._get_type_preserving_mask(value[0])]
            return []
        elif isinstance(value, dict):
            return {k: self._get_type_preserving_mask(v) for k, v in value.items()}
        else:
            return self.mask_value
    
    def is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field name indicates sensitive data."""
        field_lower = field_name.lower().replace("-", "_").replace(" ", "_")
        return any(s in field_lower for s in self.SENSITIVE_FIELDS)


# Global masker instance
pii_masker = PIIMasker()
