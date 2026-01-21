"""
Traffic Observer Agent - Agent 1
Responsibility: Observe real API traffic and build observed contracts.
"""

import os
from typing import Optional

from smolagents import CodeAgent, LiteLLMModel

from ..config import config
from ..tools.traffic_tools import (
    sample_traffic,
    extract_field_info,
    build_observed_schema,
)


class TrafficObserverAgent:
    """
    Agent 1: Traffic Observer
    
    Observes real API traffic and builds observed schemas by:
    - Sampling traffic at a configurable rate
    - Extracting field information from responses
    - Aggregating samples into observed schemas with presence rates
    - Masking PII for security
    """
    
    def __init__(self, agent: CodeAgent):
        self.agent = agent
        self.name = "traffic_observer"
        self.description = (
            "Observes API traffic and builds observed schemas. "
            "Samples traffic safely, extracts field types and presence rates, "
            "and builds comprehensive observed contracts from real traffic patterns."
        )
    
    def observe(self, traffic_data: list[dict], sample_rate: float = 0.1) -> str:
        """
        Observe traffic and build observed schemas.
        
        Args:
            traffic_data: List of traffic records
            sample_rate: Fraction of traffic to sample
            
        Returns:
            JSON string with observed schemas
        """
        task = f"""
        You are the Traffic Observer Agent. Your job is to observe API traffic and build observed schemas.
        
        I have {len(traffic_data)} traffic records to analyze.
        
        Please do the following:
        1. Use the sample_traffic tool to sample the traffic at rate {sample_rate} with PII masking enabled
        2. For each unique endpoint in the sampled data, use build_observed_schema to create an observed schema
        3. Report the observed schemas with field presence rates
        
        Focus on identifying:
        - Which fields are always present vs sometimes missing
        - What data types are being returned
        - Any fields that appear to be nullable
        
        The traffic data is provided as additional args.
        """
        
        result = self.agent.run(
            task,
            additional_args={"traffic_data": traffic_data, "sample_rate": sample_rate}
        )
        
        return str(result)


def create_traffic_observer_agent(
    api_key: Optional[str] = None,
    model_id: Optional[str] = None,
) -> TrafficObserverAgent:
    """
    Create a Traffic Observer Agent.
    
    Args:
        api_key: Groq API key (defaults to env var)
        model_id: Model ID (defaults to config)
        
    Returns:
        Configured TrafficObserverAgent
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
        tools=[sample_traffic, extract_field_info, build_observed_schema],
        model=model,
        name="traffic_observer",
        description=(
            "Observes API traffic and builds observed schemas. "
            "Samples traffic, extracts field info, and tracks presence rates."
        ),
        max_steps=10,
    )
    
    return TrafficObserverAgent(agent)
