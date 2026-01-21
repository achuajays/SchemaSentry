"""
Impact Assessor Agent - Agent 3
Responsibility: Answer "Who will break if this ships?"
"""

import os
from typing import Optional

from smolagents import CodeAgent, LiteLLMModel

from ..config import config
from ..tools.impact_tools import (
    map_client_usage,
    calculate_blast_radius,
    identify_critical_clients,
    generate_recommendations,
)


class ImpactAssessorAgent:
    """
    Agent 3: Impact Assessor
    
    Answers the most important question: "Who will break if this ships?"
    
    - Maps endpoints to consuming clients
    - Scores blast radius
    - Identifies critical clients
    - Generates actionable recommendations
    """
    
    def __init__(self, agent: CodeAgent):
        self.agent = agent
        self.name = "impact_assessor"
        self.description = (
            "Assesses the impact of contract changes on client applications. "
            "Maps endpoints to consumers, calculates blast radius, and generates actionable recommendations."
        )
    
    def assess(
        self,
        issues_json: str,
        client_logs: list[dict],
        endpoint: str
    ) -> str:
        """
        Assess the impact of detected issues on client applications.
        
        Args:
            issues_json: JSON string of classified issues from Contract Analyzer
            client_logs: List of client usage logs
            endpoint: The endpoint being analyzed
            
        Returns:
            JSON string with impact assessment and recommendations
        """
        task = f"""
        You are the Impact Assessor Agent. Your job is to answer the critical question:
        "Who will break if this ships?"
        
        Analyze the impact for endpoint: {endpoint}
        
        Please do the following:
        1. Use map_client_usage to identify which clients are using this endpoint
        2. Use identify_critical_clients to find the most important clients
        3. Use calculate_blast_radius to determine how many clients would be affected
        4. Use generate_recommendations to create actionable recommendations
        
        Consider:
        - Which clients have the highest traffic to this endpoint?
        - Are any critical services (billing, auth, frontend) affected?
        - What is the confidence level of your assessment?
        - What specific actions should the team take?
        
        The issues and client logs are provided as additional args.
        """
        
        result = self.agent.run(
            task,
            additional_args={
                "issues_json": issues_json,
                "client_logs": client_logs,
                "endpoint": endpoint,
            }
        )
        
        return str(result)


def create_impact_assessor_agent(
    api_key: Optional[str] = None,
    model_id: Optional[str] = None,
) -> ImpactAssessorAgent:
    """
    Create an Impact Assessor Agent.
    
    Args:
        api_key: Groq API key (defaults to env var)
        model_id: Model ID (defaults to config)
        
    Returns:
        Configured ImpactAssessorAgent
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
        tools=[
            map_client_usage,
            calculate_blast_radius,
            identify_critical_clients,
            generate_recommendations,
        ],
        model=model,
        name="impact_assessor",
        description=(
            "Assesses impact of API changes on client applications. "
            "Calculates blast radius and generates actionable recommendations."
        ),
        max_steps=10,
    )
    
    return ImpactAssessorAgent(agent)
