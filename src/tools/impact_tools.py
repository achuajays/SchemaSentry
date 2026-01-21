"""
Impact assessment tools for Agent 3 (Impact Assessor Agent).
These tools answer: "Who will break if this ships?"
"""

import json
from datetime import datetime
from typing import Any, Optional
from collections import defaultdict

from smolagents import tool

from ..models.schemas import ClientUsage, ImpactAssessment, ContractIssue
from ..models.enums import RiskLevel


@tool
def map_client_usage(
    endpoint: str,
    client_logs: list[dict]
) -> dict:
    """
    Map an API endpoint to its consuming clients based on usage logs.
    
    This tool analyzes client usage logs to identify which clients/services
    are consuming specific API endpoints.
    
    Args:
        endpoint: The API endpoint path (e.g., "/patients" or "GET /patients")
        client_logs: List of log entries with client identification info.
                     Each entry should have 'client_id' or identifiable headers,
                     'endpoint', 'method', and optionally 'timestamp' and 'count'
    
    Returns:
        Dictionary with mapping of clients to their usage of this endpoint
    """
    if not client_logs:
        return {
            "endpoint": endpoint,
            "clients": [],
            "message": "No client logs provided"
        }
    
    # Normalize endpoint (remove method prefix if present)
    endpoint_path = endpoint.split()[-1] if " " in endpoint else endpoint
    
    # Track client usage
    client_usage: dict[str, dict] = defaultdict(lambda: {
        "request_count": 0,
        "endpoints_used": set(),
        "last_seen": None,
        "methods_used": set(),
    })
    
    for log in client_logs:
        client_id = log.get("client_id")
        if not client_id:
            # Try to extract from headers
            headers = log.get("headers", {})
            client_id = (
                headers.get("X-Client-ID") or 
                headers.get("X-API-Key", "")[:8] or
                headers.get("User-Agent", "unknown")[:20] or
                "anonymous"
            )
        
        log_endpoint = log.get("endpoint", "")
        log_method = log.get("method", "GET")
        
        # Check if this log is for the target endpoint
        if endpoint_path in log_endpoint or log_endpoint in endpoint_path:
            usage = client_usage[client_id]
            usage["request_count"] += log.get("count", 1)
            usage["endpoints_used"].add(f"{log_method} {log_endpoint}")
            usage["methods_used"].add(log_method)
            
            timestamp = log.get("timestamp")
            if timestamp:
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    except:
                        timestamp = None
                if timestamp and (usage["last_seen"] is None or timestamp > usage["last_seen"]):
                    usage["last_seen"] = timestamp
    
    # Convert to list format
    clients = []
    for client_id, usage in client_usage.items():
        if usage["request_count"] > 0:
            clients.append({
                "client_id": client_id,
                "request_count": usage["request_count"],
                "endpoints_used": list(usage["endpoints_used"]),
                "methods_used": list(usage["methods_used"]),
                "last_seen": usage["last_seen"].isoformat() if usage["last_seen"] else None,
            })
    
    # Sort by request count (most active first)
    clients.sort(key=lambda x: x["request_count"], reverse=True)
    
    result = {
        "endpoint": endpoint,
        "client_count": len(clients),
        "clients": clients,
        "total_requests": sum(c["request_count"] for c in clients),
    }
    
    print(f"Client usage mapping for {endpoint}")
    print(f"  - Found {len(clients)} unique clients")
    print(f"  - Total requests: {result['total_requests']}")
    
    return result


@tool
def calculate_blast_radius(
    issues_data: dict,
    client_mapping: dict
) -> dict:
    """
    Calculate how many clients are affected by each detected issue.
    
    This tool combines contract issues with client usage data to determine
    the "blast radius" - how many clients would be impacted if these issues
    are shipped to production.
    
    Args:
        issues_data: Dictionary with classified contract issues
        client_mapping: Dictionary with client usage mapping
    
    Returns:
        Dictionary with impact assessment including affected clients and blast radius
    """
    issues = issues_data.get("classified_issues", issues_data.get("issues", []))
    clients = client_mapping.get("clients", [])
    
    # Get unique affected clients
    affected_client_ids = set()
    client_details = {}
    
    for client in clients:
        client_id = client.get("client_id", "unknown")
        affected_client_ids.add(client_id)
        
        client_details[client_id] = ClientUsage(
            client_id=client_id,
            client_name=client.get("client_name"),
            endpoints_used=client.get("endpoints_used", []),
            request_count=client.get("request_count", 0),
            last_seen=datetime.now(),
        ).model_dump(mode="json")
    
    # Identify critical clients (high request count or specific naming patterns)
    critical_patterns = ["billing", "payment", "auth", "frontend", "mobile", "core"]
    critical_clients = []
    
    for client_id in affected_client_ids:
        client_lower = client_id.lower()
        if any(pattern in client_lower for pattern in critical_patterns):
            critical_clients.append(client_id)
        elif client_details.get(client_id, {}).get("request_count", 0) > 1000:
            critical_clients.append(client_id)
    
    # Calculate confidence based on data quality
    confidence = min(1.0, len(clients) / 10) * 0.5  # Basic confidence from client count
    
    if len(clients) > 5:
        confidence += 0.2
    if any(c.get("last_seen") for c in clients):
        confidence += 0.2
    if len(issues) > 0:
        confidence += 0.1
    
    confidence = min(confidence, 0.95)  # Cap at 95%
    
    # Build impact assessment
    assessment = ImpactAssessment(
        issues_analyzed=len(issues),
        affected_clients=list(affected_client_ids),
        client_details=client_details,
        confidence=round(confidence, 2),
        blast_radius=len(affected_client_ids),
        critical_clients=critical_clients,
        recommended_action="",  # Will be filled by generate_recommendations
    )
    
    result = {
        "assessment": assessment.model_dump(mode="json"),
        "summary": {
            "issues_analyzed": len(issues),
            "total_clients_affected": len(affected_client_ids),
            "critical_clients_affected": len(critical_clients),
            "confidence": round(confidence, 2),
            "severity": "CRITICAL" if len(critical_clients) > 0 else (
                "HIGH" if len(affected_client_ids) > 5 else "MEDIUM"
            ),
        }
    }
    
    print(f"Blast radius calculation complete")
    print(f"  - Issues analyzed: {len(issues)}")
    print(f"  - Clients affected: {len(affected_client_ids)}")
    print(f"  - Critical clients: {len(critical_clients)}")
    print(f"  - Confidence: {confidence:.0%}")
    
    return result


@tool
def identify_critical_clients(
    client_mapping: dict,
    priority_patterns: Optional[list[str]] = None
) -> dict:
    """
    Identify critical clients that would have highest impact if affected.
    
    This tool analyzes client usage data to identify which clients are
    most critical (e.g., high traffic, payment services, core infrastructure).
    
    Args:
        client_mapping: Dictionary with client usage mapping
        priority_patterns: Optional list of string patterns to identify priority clients
                          (e.g., ["billing", "payment", "auth"]). Defaults to common patterns.
    
    Returns:
        Dictionary with prioritized list of critical clients
    """
    clients = client_mapping.get("clients", [])
    
    if priority_patterns is None:
        priority_patterns = [
            "billing", "payment", "checkout", "auth", "login",
            "frontend", "mobile", "ios", "android", "web",
            "core", "internal", "admin",
            "partner", "enterprise",
        ]
    
    # Score each client
    scored_clients = []
    
    for client in clients:
        client_id = client.get("client_id", "unknown")
        client_lower = client_id.lower()
        
        score = 0
        reasons = []
        
        # Pattern matching
        for pattern in priority_patterns:
            if pattern in client_lower:
                score += 20
                reasons.append(f"matches priority pattern '{pattern}'")
                break
        
        # Request volume scoring
        request_count = client.get("request_count", 0)
        if request_count > 10000:
            score += 30
            reasons.append(f"very high traffic ({request_count} requests)")
        elif request_count > 1000:
            score += 20
            reasons.append(f"high traffic ({request_count} requests)")
        elif request_count > 100:
            score += 10
            reasons.append(f"moderate traffic ({request_count} requests)")
        
        # Endpoint diversity (uses many endpoints = more integrated)
        endpoints_count = len(client.get("endpoints_used", []))
        if endpoints_count > 5:
            score += 15
            reasons.append(f"heavily integrated ({endpoints_count} endpoints)")
        
        scored_clients.append({
            "client_id": client_id,
            "priority_score": score,
            "request_count": request_count,
            "endpoints_used": client.get("endpoints_used", []),
            "is_critical": score >= 30,
            "reasons": reasons,
        })
    
    # Sort by score
    scored_clients.sort(key=lambda x: x["priority_score"], reverse=True)
    
    critical = [c for c in scored_clients if c["is_critical"]]
    
    result = {
        "total_clients": len(scored_clients),
        "critical_count": len(critical),
        "critical_clients": critical,
        "all_clients_scored": scored_clients[:20],  # Top 20
    }
    
    print(f"Critical client identification complete")
    print(f"  - Total clients: {len(scored_clients)}")
    print(f"  - Critical clients: {len(critical)}")
    
    return result


@tool
def generate_recommendations(
    blast_radius_data: dict,
    issues_data: dict
) -> dict:
    """
    Generate actionable recommendations based on impact assessment.
    
    This tool uses AI reasoning to generate specific, actionable recommendations
    for addressing the detected contract issues based on their impact.
    
    Args:
        blast_radius_data: Dictionary with blast radius calculation results
        issues_data: Dictionary with classified contract issues
    
    Returns:
        Dictionary with recommendations and final impact assessment
    """
    assessment = blast_radius_data.get("assessment", {})
    summary = blast_radius_data.get("summary", {})
    issues = issues_data.get("classified_issues", issues_data.get("issues", []))
    
    affected_clients = assessment.get("affected_clients", [])
    critical_clients = assessment.get("critical_clients", [])
    blast_radius = assessment.get("blast_radius", 0)
    confidence = assessment.get("confidence", 0)
    
    # Generate recommendations based on severity
    recommendations = []
    
    severity = summary.get("severity", "MEDIUM")
    
    if severity == "CRITICAL":
        recommendations.append({
            "priority": "IMMEDIATE",
            "action": "Block deployment until issues are resolved",
            "reason": f"Critical clients ({', '.join(critical_clients[:3])}) would be affected",
        })
        recommendations.append({
            "priority": "HIGH",
            "action": "Notify affected client teams immediately",
            "reason": f"At least {len(critical_clients)} critical clients could experience outages",
        })
    
    elif severity == "HIGH":
        recommendations.append({
            "priority": "HIGH",
            "action": "Review changes with API team before deployment",
            "reason": f"{blast_radius} clients could be affected",
        })
        recommendations.append({
            "priority": "MEDIUM",
            "action": "Consider versioning the affected endpoints",
            "reason": "Breaking changes should not affect existing clients",
        })
    
    else:
        recommendations.append({
            "priority": "MEDIUM",
            "action": "Update OpenAPI spec to match actual behavior",
            "reason": "Keeping documentation in sync prevents future issues",
        })
    
    # Add issue-specific recommendations
    for issue in issues[:5]:  # Top 5 issues
        issue_type = issue.get("issue_type", "")
        field_path = issue.get("field_path", "unknown")
        
        if issue_type == "BREAKING_CHANGE":
            recommendations.append({
                "priority": "CRITICAL",
                "action": f"Ensure field '{field_path}' is consistently returned",
                "reason": issue.get("detail", "Breaking change detected"),
            })
        elif issue_type == "TYPE_MISMATCH":
            recommendations.append({
                "priority": "HIGH",
                "action": f"Fix type inconsistency for field '{field_path}'",
                "reason": f"Expected {issue.get('expected')}, got {issue.get('observed')}",
            })
    
    # Determine recommended action summary
    if severity == "CRITICAL":
        recommended_action = (
            f"STOP DEPLOYMENT. {len(critical_clients)} critical clients "
            f"({', '.join(critical_clients[:3])}) would be affected. "
            f"Fix breaking changes before proceeding."
        )
    elif severity == "HIGH":
        recommended_action = (
            f"Add backward-compatible handling or version the endpoint. "
            f"{blast_radius} clients could be impacted. Consider a deprecation period."
        )
    else:
        recommended_action = (
            f"Update OpenAPI spec to reflect actual API behavior. "
            f"Low risk but documentation drift can accumulate."
        )
    
    # Build final impact assessment
    final_assessment = ImpactAssessment(
        issues_analyzed=len(issues),
        affected_clients=affected_clients,
        confidence=confidence,
        blast_radius=blast_radius,
        critical_clients=critical_clients,
        recommended_action=recommended_action,
    )
    
    result = {
        "final_assessment": final_assessment.model_dump(mode="json"),
        "recommendations": recommendations,
        "summary": {
            "severity": severity,
            "affected_clients": affected_clients,
            "critical_clients": critical_clients,
            "confidence": confidence,
            "recommended_action": recommended_action,
        },
    }
    
    print(f"Recommendations generated")
    print(f"  - Severity: {severity}")
    print(f"  - Recommendations: {len(recommendations)}")
    print(f"  - Action: {recommended_action[:100]}...")
    
    return result
