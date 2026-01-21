"""
SchemaSentry FastAPI Application
Smart API Contract Guardian - Detect breaking API changes before clients do.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

from src.config import config
from src.agents.orchestrator import AgentOrchestrator
from src.models.schemas import TrafficSample, AnalysisReport


# --- Pydantic Models for API ---

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    timestamp: str


class ObserveRequest(BaseModel):
    """Request to observe traffic."""
    traffic_data: list[dict]
    sample_rate: float = 0.1
    mask_pii: bool = True


class AnalyzeRequest(BaseModel):
    """Request to analyze contract drift."""
    observed_schema_json: str
    openapi_spec: str
    endpoint: str
    method: str = "GET"


class AssessRequest(BaseModel):
    """Request to assess impact."""
    issues_json: str
    client_logs: list[dict]
    endpoint: str


class FullReportRequest(BaseModel):
    """Request for full analysis report."""
    traffic_data: list[dict]
    openapi_spec: str
    client_logs: list[dict]
    endpoint: str
    method: str = "GET"
    sample_rate: float = 0.1


class DashboardData(BaseModel):
    """Dashboard data response."""
    total_endpoints: int
    total_issues: int
    critical_issues: int
    high_risk_issues: int
    recent_issues: list[dict]
    client_impact: dict
    health_score: float


# --- Application Factory ---

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="SchemaSentry - Smart API Contract Guardian",
        description=(
            "Detect breaking API changes before clients do. "
            "A multi-agent system that observes API traffic, compares against contracts, "
            "and assesses impact on client applications."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Store for recent reports
    app.state.recent_reports: list[AnalysisReport] = []
    app.state.orchestrator: Optional[AgentOrchestrator] = None
    
    def get_orchestrator() -> AgentOrchestrator:
        """Get or create the agent orchestrator."""
        if app.state.orchestrator is None:
            try:
                app.state.orchestrator = AgentOrchestrator()
            except ValueError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to initialize agents: {str(e)}"
                )
        return app.state.orchestrator
    
    # --- Routes ---
    
    @app.get("/", response_class=FileResponse)
    async def serve_dashboard():
        """Serve the dashboard UI."""
        ui_path = Path(__file__).parent.parent / "ui" / "index.html"
        if ui_path.exists():
            return FileResponse(ui_path)
        return JSONResponse(
            {"message": "SchemaSentry API is running. Visit /docs for API documentation."}
        )
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Check service health."""
        return HealthResponse(
            status="healthy",
            service="SchemaSentry",
            version="1.0.0",
            timestamp=datetime.now().isoformat(),
        )
    
    @app.post("/api/observe")
    async def observe_traffic(request: ObserveRequest):
        """
        Submit API traffic for observation.
        
        The Traffic Observer Agent will:
        - Sample traffic at the specified rate
        - Mask PII for security
        - Extract field information
        - Build observed schemas
        """
        orchestrator = get_orchestrator()
        
        try:
            result = orchestrator.observe_traffic(
                traffic_data=request.traffic_data,
                sample_rate=request.sample_rate,
            )
            return {"status": "success", "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/analyze")
    async def analyze_contract(request: AnalyzeRequest):
        """
        Analyze contract drift between observed and declared schemas.
        
        The Contract Analyzer Agent will:
        - Parse the OpenAPI specification
        - Compare against observed schema
        - Detect breaking changes
        - Classify risk levels
        """
        orchestrator = get_orchestrator()
        
        try:
            result = orchestrator.analyze_contract(
                observed_schema_json=request.observed_schema_json,
                openapi_spec=request.openapi_spec,
                endpoint=request.endpoint,
                method=request.method,
            )
            return {"status": "success", "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/assess")
    async def assess_impact(request: AssessRequest):
        """
        Assess the impact of detected issues on client applications.
        
        The Impact Assessor Agent will:
        - Map endpoints to consuming clients
        - Calculate blast radius
        - Identify critical clients
        - Generate recommendations
        """
        orchestrator = get_orchestrator()
        
        try:
            result = orchestrator.assess_impact(
                issues_json=request.issues_json,
                client_logs=request.client_logs,
                endpoint=request.endpoint,
            )
            return {"status": "success", "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/report")
    async def generate_full_report(request: FullReportRequest):
        """
        Generate a complete analysis report.
        
        Runs all three agents in sequence:
        1. Traffic Observer → Observe and build schemas
        2. Contract Analyzer → Detect issues
        3. Impact Assessor → Assess client impact
        """
        orchestrator = get_orchestrator()
        
        try:
            report = orchestrator.run_full_analysis(
                traffic_data=request.traffic_data,
                openapi_spec=request.openapi_spec,
                client_logs=request.client_logs,
                endpoint=request.endpoint,
                method=request.method,
                sample_rate=request.sample_rate,
            )
            
            # Store for dashboard
            app.state.recent_reports.append(report)
            if len(app.state.recent_reports) > 10:
                app.state.recent_reports.pop(0)
            
            return {
                "status": "success",
                "report_id": report.report_id,
                "summary": {
                    "total_issues": report.total_issues_found,
                    "critical_issues": report.critical_issues,
                    "high_risk_issues": report.high_risk_issues,
                },
                "report": report.model_dump(mode="json"),
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/issues")
    async def list_issues():
        """List all detected issues from recent analyses."""
        all_issues = []
        for report in app.state.recent_reports:
            for issue in report.contract_issues:
                all_issues.append(issue.model_dump(mode="json"))
        
        return {
            "total": len(all_issues),
            "issues": all_issues,
        }
    
    @app.get("/api/dashboard-data", response_model=DashboardData)
    async def get_dashboard_data():
        """Get aggregated data for the dashboard UI."""
        reports = app.state.recent_reports
        
        total_issues = sum(r.total_issues_found for r in reports)
        critical_issues = sum(r.critical_issues for r in reports)
        high_risk_issues = sum(r.high_risk_issues for r in reports)
        
        # Collect recent issues
        recent_issues = []
        for report in reversed(reports[-5:]):
            for issue in report.contract_issues[:5]:
                recent_issues.append(issue.model_dump(mode="json"))
        
        # Client impact summary
        client_impact = {}
        for report in reports:
            if report.impact_assessment:
                for client in report.impact_assessment.affected_clients:
                    client_impact[client] = client_impact.get(client, 0) + 1
        
        # Health score (inverse of issue severity)
        if total_issues == 0:
            health_score = 100.0
        else:
            severity_penalty = (critical_issues * 20) + (high_risk_issues * 10) + (total_issues * 2)
            health_score = max(0, 100 - severity_penalty)
        
        return DashboardData(
            total_endpoints=len(reports),
            total_issues=total_issues,
            critical_issues=critical_issues,
            high_risk_issues=high_risk_issues,
            recent_issues=recent_issues[:10],
            client_impact=client_impact,
            health_score=round(health_score, 1),
        )
    
    # Mount static files for UI
    ui_dir = Path(__file__).parent.parent / "ui"
    if ui_dir.exists():
        app.mount("/static", StaticFiles(directory=str(ui_dir)), name="static")
    
    return app


# Create the app instance
app = create_app()
