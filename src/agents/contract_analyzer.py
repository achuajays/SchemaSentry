"""
Contract Analyzer Agent - Agent 2
Responsibility: Compare Observed Schema vs OpenAPI Spec and detect drift.
"""

import os
from typing import Optional

from smolagents import CodeAgent, LiteLLMModel

from ..config import config
from ..tools.contract_tools import (
    parse_openapi_spec,
    compare_schemas,
    detect_breaking_changes,
    classify_risk,
)


class ContractAnalyzerAgent:
    """
    Agent 2: Contract Analyzer
    
    Compares observed schemas against declared OpenAPI contracts to detect:
    - Missing fields
    - Type mismatches
    - Optional → required drift
    - Undocumented fields
    - Status code changes
    
    Uses LLM reasoning for risk classification and human-readable explanations.
    """
    
    def __init__(self, agent: CodeAgent):
        self.agent = agent
        self.name = "contract_analyzer"
        self.description = (
            "Compares observed schemas against declared contracts and detects breaking changes. "
            "Uses AI reasoning to classify risks and generate human-readable explanations."
        )
    
    def analyze(
        self,
        observed_schema_json: str,
        openapi_spec: str,
        endpoint: str,
        method: str = "GET"
    ) -> str:
        """
        Analyze contract drift between observed and declared schemas.
        
        Args:
            observed_schema_json: JSON string of observed schema from Traffic Observer
            openapi_spec: OpenAPI spec content (YAML or JSON string)
            endpoint: Endpoint path to analyze
            method: HTTP method
            
        Returns:
            JSON string with detected issues and risk classifications
        """
        task = f"""
        You are the Contract Analyzer Agent. Your job is to compare observed API behavior 
        against the declared OpenAPI contract and detect any drift or breaking changes.
        
        Analyze the endpoint: {method} {endpoint}
        
        Please do the following:
        1. Use parse_openapi_spec to parse the provided OpenAPI specification
        2. Use compare_schemas to compare the observed schema against the declared contract
        3. Use detect_breaking_changes to identify issues that would break clients
        4. Use classify_risk to generate human-readable explanations for each issue
        
        Focus on detecting:
        - Fields that are missing or have changed type
        - Required fields that are sometimes absent
        - Undocumented fields appearing in responses
        - Any inconsistencies between spec and reality
        
        The observed schema and OpenAPI spec are provided as additional args.
        """
        
        result = self.agent.run(
            task,
            additional_args={
                "observed_schema_json": observed_schema_json,
                "openapi_spec": openapi_spec,
                "endpoint": endpoint,
                "method": method,
            }
        )
        
        return str(result)


def create_contract_analyzer_agent(
    api_key: Optional[str] = None,
    model_id: Optional[str] = None,
) -> ContractAnalyzerAgent:
    """
    Create a Contract Analyzer Agent.
    
    Args:
        api_key: Groq API key (defaults to env var)
        model_id: Model ID (defaults to config)
        
    Returns:
        Configured ContractAnalyzerAgent
    """
    api_key = api_key or config.GROQ_API_KEY
    model_id = model_id or config.get_model_id()
    
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is required. Set it in .env or pass as argument."
        )
    
    model = LiteLLMModel(
        model_id=model_id,
        api_key=api_key,
    )
    
    agent = CodeAgent(
        tools=[parse_openapi_spec, compare_schemas, detect_breaking_changes, classify_risk],
        model=model,
        name="contract_analyzer",
        description=(
            "Compares observed schemas against OpenAPI contracts. "
            "Detects breaking changes, type mismatches, and missing fields."
        ),
        max_steps=10,
    )
    
    return ContractAnalyzerAgent(agent)
