"""
Contract analysis tools for Agent 2 (Contract Analyzer Agent).
These tools compare observed schemas against OpenAPI specs to detect drift.
"""

import json
from datetime import datetime
from typing import Any, Optional

from smolagents import tool

from ..models.schemas import ObservedSchema, ContractIssue
from ..models.enums import IssueType, RiskLevel, FieldType
from ..utils.openapi_parser import OpenAPIParser


@tool
def parse_openapi_spec(spec_content: str) -> dict:
    """
    Parse an OpenAPI/Swagger specification into a structured format.
    
    This tool parses the OpenAPI spec (YAML or JSON format provided as string)
    and extracts endpoint definitions, schemas, and field information.
    
    Args:
        spec_content: The OpenAPI specification content as a YAML or JSON string
    
    Returns:
        Dictionary containing parsed endpoints with their request/response schemas
    """
    import yaml
    
    try:
        # Try parsing as YAML first (also handles JSON)
        spec_dict = yaml.safe_load(spec_content)
    except Exception as e:
        return {
            "error": f"Failed to parse spec: {str(e)}",
            "endpoints": [],
        }
    
    parser = OpenAPIParser(spec_content=spec_dict)
    
    endpoints = parser.get_endpoints()
    
    # Extract schema fields for each endpoint
    enriched_endpoints = []
    for endpoint in endpoints:
        endpoint_info = {
            "path": endpoint["path"],
            "method": endpoint["method"],
            "summary": endpoint.get("summary", ""),
            "parameters": endpoint.get("parameters", []),
            "request_schema": None,
            "response_schema": None,
            "response_fields": {},
        }
        
        # Get response schema
        responses = endpoint.get("responses", {})
        for status in ["200", "201"]:
            if status in responses and responses[status].get("schema"):
                schema = responses[status]["schema"]
                endpoint_info["response_schema"] = schema
                endpoint_info["response_fields"] = parser.get_schema_fields(schema)
                break
        
        # Get request schema
        if endpoint.get("request_body"):
            endpoint_info["request_schema"] = endpoint["request_body"]
        
        enriched_endpoints.append(endpoint_info)
    
    result = {
        "version": parser.get_version(),
        "endpoint_count": len(enriched_endpoints),
        "endpoints": enriched_endpoints,
    }
    
    print(f"Parsed OpenAPI spec version {parser.get_version()}")
    print(f"Found {len(enriched_endpoints)} endpoint definitions")
    
    return result


@tool
def compare_schemas(
    observed_schema: dict,
    declared_spec: dict,
    endpoint: str,
    method: str
) -> dict:
    """
    Compare an observed schema against a declared OpenAPI contract for an endpoint.
    
    This tool performs a detailed comparison between what was observed in real
    traffic and what was declared in the API contract, detecting any drifts.
    
    Args:
        observed_schema: Dictionary of the ObservedSchema from traffic observation
        declared_spec: Dictionary of the parsed OpenAPI spec
        endpoint: The endpoint path to compare (e.g., "/patients")
        method: HTTP method (GET, POST, etc.)
    
    Returns:
        Dictionary with list of detected differences and issues
    """
    observed = observed_schema
    declared = declared_spec
    
    issues = []
    
    # Find the declared endpoint
    declared_endpoint = None
    for ep in declared.get("endpoints", []):
        if ep["path"] == endpoint and ep["method"] == method.upper():
            declared_endpoint = ep
            break
    
    if not declared_endpoint:
        issues.append({
            "issue_type": IssueType.FIELD_ADDED_UNDOCUMENTED.value,
            "detail": f"Endpoint {method} {endpoint} not found in OpenAPI spec",
            "risk": RiskLevel.MEDIUM.value,
            "field_path": None,
        })
        return {"issues": issues, "endpoint": endpoint, "method": method}
    
    declared_fields = declared_endpoint.get("response_fields", {})
    observed_fields = observed.get("observed_fields", {})
    field_presence = observed.get("field_presence_rate", {})
    
    # Check for missing fields (in spec but not observed)
    for field_path, field_info in declared_fields.items():
        if field_path not in observed_fields:
            if field_info.get("required", False):
                issues.append({
                    "issue_type": IssueType.FIELD_MISSING.value,
                    "detail": f"Required field '{field_path}' declared in spec but never observed in traffic",
                    "risk": RiskLevel.HIGH.value,
                    "field_path": field_path,
                    "expected": field_info,
                    "observed": None,
                })
            else:
                issues.append({
                    "issue_type": IssueType.FIELD_MISSING.value,
                    "detail": f"Optional field '{field_path}' declared in spec but never observed",
                    "risk": RiskLevel.LOW.value,
                    "field_path": field_path,
                })
    
    # Check for undocumented fields (observed but not in spec)
    for field_path, field_info in observed_fields.items():
        if field_path not in declared_fields:
            issues.append({
                "issue_type": IssueType.FIELD_ADDED_UNDOCUMENTED.value,
                "detail": f"Field '{field_path}' observed in traffic but not in OpenAPI spec",
                "risk": RiskLevel.MEDIUM.value,
                "field_path": field_path,
                "observed": field_info,
            })
    
    # Check for type mismatches
    for field_path in set(declared_fields.keys()) & set(observed_fields.keys()):
        declared_type = declared_fields[field_path].get("type", "any")
        observed_type = observed_fields[field_path].get("field_type", "unknown")
        
        # Normalize types for comparison
        type_mapping = {
            "integer": ["integer", "number"],
            "number": ["number", "integer"],
            "string": ["string"],
            "boolean": ["boolean"],
            "array": ["array"],
            "object": ["object"],
        }
        
        compatible_types = type_mapping.get(declared_type, [declared_type])
        if observed_type not in compatible_types and observed_type != "mixed":
            issues.append({
                "issue_type": IssueType.TYPE_MISMATCH.value,
                "detail": f"Field '{field_path}' declared as '{declared_type}' but observed as '{observed_type}'",
                "risk": RiskLevel.HIGH.value,
                "field_path": field_path,
                "expected": declared_type,
                "observed": observed_type,
            })
        
        # Check nullability changes
        declared_nullable = declared_fields[field_path].get("nullable", False)
        observed_nullable = observed_fields[field_path].get("nullable", False)
        
        if not declared_nullable and observed_nullable:
            issues.append({
                "issue_type": IssueType.NULLABILITY_CHANGE.value,
                "detail": f"Field '{field_path}' is not nullable in spec but null values observed",
                "risk": RiskLevel.MEDIUM.value,
                "field_path": field_path,
            })
    
    # Check for low presence rates (potential breaking changes)
    for field_path, presence in field_presence.items():
        if field_path in declared_fields:
            declared_required = declared_fields[field_path].get("required", False)
            
            if declared_required and presence < 1.0:
                issues.append({
                    "issue_type": IssueType.BREAKING_CHANGE.value,
                    "detail": f"Required field '{field_path}' is missing in {(1-presence)*100:.1f}% of responses",
                    "risk": RiskLevel.CRITICAL.value,
                    "field_path": field_path,
                    "presence_rate": presence,
                })
            elif presence < 0.5:
                issues.append({
                    "issue_type": IssueType.OPTIONAL_TO_REQUIRED.value,
                    "detail": f"Field '{field_path}' appears in only {presence*100:.1f}% of responses (may have become optional)",
                    "risk": RiskLevel.MEDIUM.value,
                    "field_path": field_path,
                    "presence_rate": presence,
                })
    
    result = {
        "endpoint": endpoint,
        "method": method,
        "issues": issues,
        "issue_count": len(issues),
        "declared_fields_count": len(declared_fields),
        "observed_fields_count": len(observed_fields),
    }
    
    print(f"Compared schemas for {method} {endpoint}")
    print(f"  - Declared fields: {len(declared_fields)}")
    print(f"  - Observed fields: {len(observed_fields)}")
    print(f"  - Issues found: {len(issues)}")
    
    return result


@tool
def detect_breaking_changes(comparison_result: dict) -> dict:
    """
    Analyze comparison results to identify breaking changes that would affect clients.
    
    This tool filters and prioritizes the issues found during schema comparison
    to highlight the ones that would cause client applications to break.
    
    Args:
        comparison_result: Dictionary from compare_schemas with detected issues
    
    Returns:
        Dictionary with filtered breaking changes and severity assessment
    """
    comparison = comparison_result
    
    breaking_issue_types = {
        IssueType.BREAKING_CHANGE.value,
        IssueType.FIELD_MISSING.value,
        IssueType.TYPE_MISMATCH.value,
        IssueType.NULLABILITY_CHANGE.value,
    }
    
    high_risk_levels = {
        RiskLevel.CRITICAL.value,
        RiskLevel.HIGH.value,
    }
    
    breaking_changes = []
    warnings = []
    
    for issue in comparison.get("issues", []):
        issue_type = issue.get("issue_type", "")
        risk = issue.get("risk", "")
        
        if issue_type in breaking_issue_types or risk in high_risk_levels:
            breaking_changes.append(issue)
        else:
            warnings.append(issue)
    
    # Sort by risk level
    risk_order = {
        RiskLevel.CRITICAL.value: 0,
        RiskLevel.HIGH.value: 1,
        RiskLevel.MEDIUM.value: 2,
        RiskLevel.LOW.value: 3,
        RiskLevel.INFO.value: 4,
    }
    
    breaking_changes.sort(key=lambda x: risk_order.get(x.get("risk", ""), 5))
    
    result = {
        "endpoint": comparison.get("endpoint"),
        "method": comparison.get("method"),
        "breaking_changes": breaking_changes,
        "breaking_count": len(breaking_changes),
        "warnings": warnings,
        "warning_count": len(warnings),
        "severity": "CRITICAL" if any(
            c.get("risk") == RiskLevel.CRITICAL.value for c in breaking_changes
        ) else "HIGH" if breaking_changes else "LOW",
    }
    
    print(f"Breaking change analysis for {comparison.get('method')} {comparison.get('endpoint')}")
    print(f"  - Breaking changes: {len(breaking_changes)}")
    print(f"  - Warnings: {len(warnings)}")
    print(f"  - Overall severity: {result['severity']}")
    
    return result


@tool
def classify_risk(issues_data: dict) -> dict:
    """
    Use AI reasoning to classify risk levels and generate human-readable explanations.
    
    This tool takes detected issues and enhances them with detailed explanations
    of why each issue is risky and what could happen if not addressed.
    
    Args:
        issues_data: Dictionary containing list of detected issues
    
    Returns:
        Dictionary with enhanced issues including explanations and recommendations
    """
    data = issues_data
    
    issues = data.get("issues", data.get("breaking_changes", []))
    
    enhanced_issues = []
    
    for issue in issues:
        issue_type = issue.get("issue_type", "UNKNOWN")
        field_path = issue.get("field_path", "unknown field")
        risk = issue.get("risk", RiskLevel.MEDIUM.value)
        detail = issue.get("detail", "")
        
        # Generate explanation based on issue type
        explanation = ""
        recommendation = ""
        
        if issue_type == IssueType.BREAKING_CHANGE.value:
            explanation = (
                f"This is a critical breaking change. Clients expecting the field "
                f"'{field_path}' will fail when it's missing. This can cause "
                f"null pointer exceptions, parse errors, or incorrect business logic."
            )
            recommendation = (
                "Immediately investigate why this field is sometimes missing. "
                "Consider making the field reliably present or explicitly documenting it as optional."
            )
        
        elif issue_type == IssueType.FIELD_MISSING.value:
            explanation = (
                f"The field '{field_path}' is declared in your API contract but was "
                f"never seen in actual traffic. This could mean the field is deprecated, "
                f"conditionally returned, or there's a bug in the API implementation."
            )
            recommendation = (
                "Verify if this field should still be in the contract. "
                "If deprecated, update the OpenAPI spec. If it's conditional, document the conditions."
            )
        
        elif issue_type == IssueType.TYPE_MISMATCH.value:
            expected = issue.get("expected", "unknown")
            observed = issue.get("observed", "unknown")
            explanation = (
                f"The field '{field_path}' is declared as '{expected}' but the API "
                f"is returning '{observed}'. This type mismatch can cause client-side "
                f"parsing errors or unexpected behavior."
            )
            recommendation = (
                "Either update the API to return the correct type or update the "
                "OpenAPI spec to reflect the actual response format."
            )
        
        elif issue_type == IssueType.NULLABILITY_CHANGE.value:
            explanation = (
                f"The field '{field_path}' is not declared as nullable but null values "
                f"were observed. Clients may not handle null values correctly."
            )
            recommendation = (
                "Update the OpenAPI spec to mark this field as nullable, or fix the API "
                "to ensure it never returns null for this field."
            )
        
        elif issue_type == IssueType.FIELD_ADDED_UNDOCUMENTED.value:
            explanation = (
                f"The field '{field_path}' appears in API responses but is not "
                f"documented in the OpenAPI spec. While not immediately breaking, "
                f"clients may start depending on this undocumented field."
            )
            recommendation = (
                "Add this field to the OpenAPI spec to officially document it, "
                "or remove it from the API response if it was added accidentally."
            )
        
        else:
            explanation = detail
            recommendation = "Review this issue and determine appropriate action."
        
        enhanced_issue = {
            **issue,
            "explanation": explanation,
            "recommendation": recommendation,
            "detected_at": datetime.now().isoformat(),
        }
        enhanced_issues.append(enhanced_issue)
    
    # Create ContractIssue objects for structured output
    contract_issues = []
    for ei in enhanced_issues:
        try:
            ci = ContractIssue(
                issue_type=IssueType(ei.get("issue_type", "BREAKING_CHANGE")),
                endpoint=data.get("endpoint", "/unknown"),
                method=data.get("method", "GET"),
                field_path=ei.get("field_path"),
                detail=ei.get("detail", ""),
                risk=RiskLevel(ei.get("risk", "MEDIUM")),
                explanation=ei.get("explanation", ""),
                observed_value=ei.get("observed"),
                expected_value=ei.get("expected"),
            )
            contract_issues.append(ci.model_dump(mode="json"))
        except Exception as e:
            print(f"Warning: Failed to create ContractIssue: {e}")
            contract_issues.append(ei)
    
    result = {
        "endpoint": data.get("endpoint"),
        "method": data.get("method"),
        "classified_issues": contract_issues,
        "issue_count": len(contract_issues),
        "critical_count": sum(1 for i in contract_issues if i.get("risk") == RiskLevel.CRITICAL.value),
        "high_count": sum(1 for i in contract_issues if i.get("risk") == RiskLevel.HIGH.value),
    }
    
    print(f"Risk classification complete for {len(contract_issues)} issues")
    print(f"  - Critical: {result['critical_count']}")
    print(f"  - High: {result['high_count']}")
    
    return result
