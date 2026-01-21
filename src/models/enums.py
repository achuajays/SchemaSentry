"""
Enums for SchemaSentry data types.
"""

from enum import Enum


class IssueType(str, Enum):
    """Types of contract issues that can be detected."""
    
    BREAKING_CHANGE = "BREAKING_CHANGE"
    FIELD_MISSING = "FIELD_MISSING"
    FIELD_ADDED_UNDOCUMENTED = "FIELD_ADDED_UNDOCUMENTED"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    OPTIONAL_TO_REQUIRED = "OPTIONAL_TO_REQUIRED"
    REQUIRED_TO_OPTIONAL = "REQUIRED_TO_OPTIONAL"
    STATUS_CODE_CHANGE = "STATUS_CODE_CHANGE"
    NULLABILITY_CHANGE = "NULLABILITY_CHANGE"
    FORMAT_CHANGE = "FORMAT_CHANGE"


class RiskLevel(str, Enum):
    """Risk severity levels for contract issues."""
    
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class FieldType(str, Enum):
    """Inferred field types from observed traffic."""
    
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    NULL = "null"
    MIXED = "mixed"  # When multiple types are observed
    UNKNOWN = "unknown"
