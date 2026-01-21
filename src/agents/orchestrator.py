"""
Agent Orchestrator - Coordinates the three agents for complete analysis.
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from ..models.schemas import AnalysisReport, ObservedSchema, ContractIssue, ImpactAssessment
from ..models.enums import RiskLevel
from ..config import config
from .traffic_observer import create_traffic_observer_agent, TrafficObserverAgent
from .contract_analyzer import create_contract_analyzer_agent, ContractAnalyzerAgent
from .impact_assessor import create_impact_assessor_agent, ImpactAssessorAgent


class AgentOrchestrator:
    """
    Orchestrates the three SchemaSentry agents to produce a complete analysis.
    
    Flow:
    1. Traffic Observer → Observes traffic, builds observed schemas
    2. Contract Analyzer → Compares against OpenAPI spec, detects issues
    3. Impact Assessor → Determines who will be affected, recommends actions
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_id: Optional[str] = None,
    ):
        """
        Initialize the orchestrator with all three agents.
        
        Args:
            api_key: Groq API key
            model_id: Model ID for all agents
        """
        self.api_key = api_key or config.GROQ_API_KEY
        self.model_id = model_id or config.get_model_id()
        
        # Lazy initialization of agents
        self._traffic_observer: Optional[TrafficObserverAgent] = None
        self._contract_analyzer: Optional[ContractAnalyzerAgent] = None
        self._impact_assessor: Optional[ImpactAssessorAgent] = None
    
    @property
    def traffic_observer(self) -> TrafficObserverAgent:
        """Get or create the Traffic Observer agent."""
        if self._traffic_observer is None:
            self._traffic_observer = create_traffic_observer_agent(
                api_key=self.api_key,
                model_id=self.model_id,
            )
        return self._traffic_observer
    
    @property
    def contract_analyzer(self) -> ContractAnalyzerAgent:
        """Get or create the Contract Analyzer agent."""
        if self._contract_analyzer is None:
            self._contract_analyzer = create_contract_analyzer_agent(
                api_key=self.api_key,
                model_id=self.model_id,
            )
        return self._contract_analyzer
    
    @property
    def impact_assessor(self) -> ImpactAssessorAgent:
        """Get or create the Impact Assessor agent."""
        if self._impact_assessor is None:
            self._impact_assessor = create_impact_assessor_agent(
                api_key=self.api_key,
                model_id=self.model_id,
            )
        return self._impact_assessor
    
    def run_full_analysis(
        self,
        traffic_data: list[dict],
        openapi_spec: str,
        client_logs: list[dict],
        endpoint: str,
        method: str = "GET",
        sample_rate: float = 0.1,
    ) -> AnalysisReport:
        """
        Run a complete analysis through all three agents.
        
        Args:
            traffic_data: API traffic records
            openapi_spec: OpenAPI specification content
            client_logs: Client usage logs
            endpoint: Endpoint to analyze
            method: HTTP method
            sample_rate: Traffic sampling rate
            
        Returns:
            Complete AnalysisReport with all findings
        """
        report_id = str(uuid.uuid4())[:8]
        print(f"\n{'='*60}")
        print(f"SchemaSentry Analysis Report: {report_id}")
        print(f"Endpoint: {method} {endpoint}")
        print(f"{'='*60}\n")
        
        # Step 1: Traffic Observer
        print("🔍 Step 1: Traffic Observation")
        print("-" * 40)
        observed_result = self.traffic_observer.observe(
            traffic_data=traffic_data,
            sample_rate=sample_rate,
        )
        print(f"Observation complete.\n")
        
        # Step 2: Contract Analyzer
        print("📋 Step 2: Contract Analysis")
        print("-" * 40)
        analysis_result = self.contract_analyzer.analyze(
            observed_schema_json=observed_result,
            openapi_spec=openapi_spec,
            endpoint=endpoint,
            method=method,
        )
        print(f"Analysis complete.\n")
        
        # Step 3: Impact Assessor
        print("💥 Step 3: Impact Assessment")
        print("-" * 40)
        impact_result = self.impact_assessor.assess(
            issues_json=analysis_result,
            client_logs=client_logs,
            endpoint=f"{method} {endpoint}",
        )
        print(f"Assessment complete.\n")
        
        # Build the report
        report = AnalysisReport(
            report_id=report_id,
            generated_at=datetime.now(),
        )
        
        # Parse results (best effort)
        try:
            observed_data = json.loads(observed_result) if isinstance(observed_result, str) else observed_result
            if isinstance(observed_data, dict):
                # Try to extract observed schema
                pass
        except:
            pass
        
        try:
            issues_data = json.loads(analysis_result) if isinstance(analysis_result, str) else analysis_result
            if isinstance(issues_data, dict):
                issues = issues_data.get("classified_issues", issues_data.get("issues", []))
                for issue in issues:
                    try:
                        ci = ContractIssue(**issue)
                        report.contract_issues.append(ci)
                    except:
                        pass
        except:
            pass
        
        try:
            impact_data = json.loads(impact_result) if isinstance(impact_result, str) else impact_result
            if isinstance(impact_data, dict):
                assessment = impact_data.get("final_assessment", impact_data.get("assessment", {}))
                if assessment:
                    try:
                        report.impact_assessment = ImpactAssessment(**assessment)
                    except:
                        pass
        except:
            pass
        
        report.calculate_summary()
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"Analysis Complete!")
        print(f"{'='*60}")
        print(f"📊 Endpoints analyzed: {report.total_endpoints_analyzed}")
        print(f"⚠️  Total issues: {report.total_issues_found}")
        print(f"🔴 Critical issues: {report.critical_issues}")
        print(f"🟠 High risk issues: {report.high_risk_issues}")
        
        if report.impact_assessment:
            print(f"\n📣 Recommendation: {report.impact_assessment.recommended_action}")
        
        return report
    
    def observe_traffic(
        self,
        traffic_data: list[dict],
        sample_rate: float = 0.1,
    ) -> str:
        """Run only the Traffic Observer agent."""
        return self.traffic_observer.observe(traffic_data, sample_rate)
    
    def analyze_contract(
        self,
        observed_schema_json: str,
        openapi_spec: str,
        endpoint: str,
        method: str = "GET",
    ) -> str:
        """Run only the Contract Analyzer agent."""
        return self.contract_analyzer.analyze(
            observed_schema_json,
            openapi_spec,
            endpoint,
            method,
        )
    
    def assess_impact(
        self,
        issues_json: str,
        client_logs: list[dict],
        endpoint: str,
    ) -> str:
        """Run only the Impact Assessor agent."""
        return self.impact_assessor.assess(
            issues_json,
            client_logs,
            endpoint,
        )
