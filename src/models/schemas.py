"""
Pydantic schemas for SchemaSentry data models.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field

from .enums import IssueType, RiskLevel, FieldType


class FieldInfo(BaseModel):
    """Information about an observed field in API responses."""
    
    name: str = Field(..., description="Field name")
    field_type: FieldType = Field(..., description="Inferred field type")
    nullable: bool = Field(default=False, description="Whether field can be null")
    presence_rate: float = Field(
        default=1.0, 
        ge=0.0, 
        le=1.0,
        description="Rate at which field appears in responses (0.0 to 1.0)"
    )
    sample_values: list[Any] = Field(
        default_factory=list,
        description="Sample values observed (for debugging)"
    )
    
    class Config:
        use_enum_values = True


class TrafficSample(BaseModel):
    """A single API traffic sample."""
    
    endpoint: str = Field(..., description="API endpoint path")
    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    status_code: int = Field(..., description="HTTP response status code")
    request_body: Optional[dict[str, Any]] = Field(
        default=None, 
        description="Request body (if applicable)"
    )
    response_body: Optional[dict[str, Any]] = Field(
        default=None,
        description="Response body"
    )
    headers: Optional[dict[str, str]] = Field(
        default=None,
        description="Request headers"
    )
    client_id: Optional[str] = Field(
        default=None,
        description="Client identifier (from token, header, etc.)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the request was made"
    )


class ObservedSchema(BaseModel):
    """Schema inferred from observed API traffic."""
    
    endpoint: str = Field(..., description="API endpoint path")
    method: str = Field(..., description="HTTP method")
    observed_fields: dict[str, FieldInfo] = Field(
        default_factory=dict,
        description="Map of field path to field info"
    )
    field_presence_rate: dict[str, float] = Field(
        default_factory=dict,
        description="Map of field path to presence rate"
    )
    sample_count: int = Field(default=0, description="Number of samples analyzed")
    status_codes_observed: list[int] = Field(
        default_factory=list,
        description="HTTP status codes observed"
    )
    timestamp_start: datetime = Field(
        default_factory=datetime.now,
        description="Start of observation window"
    )
    timestamp_end: datetime = Field(
        default_factory=datetime.now,
        description="End of observation window"
    )
    
    def to_summary_dict(self) -> dict:
        """Convert to summary format for agent output."""
        return {
            "endpoint": f"{self.method} {self.endpoint}",
            "observed_response": {
                name: f"{info.field_type}" + (" | null" if info.nullable else "")
                for name, info in self.observed_fields.items()
            },
            "field_presence_rate": {
                name: round(rate, 2)
                for name, rate in self.field_presence_rate.items()
                if rate < 1.0  # Only show fields that aren't always present
            },
            "sample_count": self.sample_count,
        }


class ContractIssue(BaseModel):
    """A detected contract violation or drift."""
    
    issue_type: IssueType = Field(..., description="Type of issue detected")
    endpoint: str = Field(..., description="Affected endpoint")
    method: str = Field(default="GET", description="HTTP method")
    field_path: Optional[str] = Field(
        default=None,
        description="Path to the affected field (e.g., 'response.data.id')"
    )
    detail: str = Field(..., description="Detailed description of the issue")
    risk: RiskLevel = Field(..., description="Risk severity level")
    explanation: str = Field(
        default="",
        description="AI-generated human-readable explanation"
    )
    observed_value: Optional[Any] = Field(
        default=None,
        description="What was observed in traffic"
    )
    expected_value: Optional[Any] = Field(
        default=None,
        description="What was expected from contract"
    )
    detected_at: datetime = Field(
        default_factory=datetime.now,
        description="When the issue was detected"
    )
    
    class Config:
        use_enum_values = True
    
    def to_summary_dict(self) -> dict:
        """Convert to summary format for agent output."""
        return {
            "issue": self.issue_type,
            "endpoint": f"{self.method} {self.endpoint}",
            "detail": self.detail,
            "risk": self.risk,
            "explanation": self.explanation,
        }


class ClientUsage(BaseModel):
    """Client usage data for impact assessment."""
    
    client_id: str = Field(..., description="Client identifier")
    client_name: Optional[str] = Field(
        default=None,
        description="Human-readable client name"
    )
    endpoints_used: list[str] = Field(
        default_factory=list,
        description="Endpoints this client uses"
    )
    request_count: int = Field(
        default=0,
        description="Total requests in observation period"
    )
    last_seen: datetime = Field(
        default_factory=datetime.now,
        description="Last time this client was seen"
    )


class ImpactAssessment(BaseModel):
    """Assessment of who will be affected by contract issues."""
    
    issues_analyzed: int = Field(
        default=0,
        description="Number of issues analyzed"
    )
    affected_clients: list[str] = Field(
        default_factory=list,
        description="List of affected client identifiers"
    )
    client_details: dict[str, ClientUsage] = Field(
        default_factory=dict,
        description="Detailed client usage data"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the assessment"
    )
    blast_radius: int = Field(
        default=0,
        description="Number of clients potentially affected"
    )
    critical_clients: list[str] = Field(
        default_factory=list,
        description="High-priority clients that would be affected"
    )
    recommended_action: str = Field(
        default="",
        description="AI-generated recommended action"
    )
    assessed_at: datetime = Field(
        default_factory=datetime.now,
        description="When the assessment was performed"
    )
    
    def to_summary_dict(self) -> dict:
        """Convert to summary format for agent output."""
        return {
            "affected_clients": self.affected_clients,
            "confidence": round(self.confidence, 2),
            "blast_radius": self.blast_radius,
            "recommended_action": self.recommended_action,
        }


class AnalysisReport(BaseModel):
    """Complete analysis report combining all agent outputs."""
    
    report_id: str = Field(..., description="Unique report identifier")
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="When the report was generated"
    )
    
    # Agent 1 output
    observed_schemas: list[ObservedSchema] = Field(
        default_factory=list,
        description="Schemas observed from traffic"
    )
    
    # Agent 2 output
    contract_issues: list[ContractIssue] = Field(
        default_factory=list,
        description="Detected contract issues"
    )
    
    # Agent 3 output
    impact_assessment: Optional[ImpactAssessment] = Field(
        default=None,
        description="Impact assessment results"
    )
    
    # Summary
    total_endpoints_analyzed: int = Field(default=0)
    total_issues_found: int = Field(default=0)
    critical_issues: int = Field(default=0)
    high_risk_issues: int = Field(default=0)
    
    def calculate_summary(self) -> None:
        """Calculate summary statistics."""
        self.total_endpoints_analyzed = len(self.observed_schemas)
        self.total_issues_found = len(self.contract_issues)
        self.critical_issues = sum(
            1 for i in self.contract_issues if i.risk == RiskLevel.CRITICAL
        )
        self.high_risk_issues = sum(
            1 for i in self.contract_issues if i.risk == RiskLevel.HIGH
        )
