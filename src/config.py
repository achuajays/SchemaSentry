"""
Configuration management for SchemaSentry.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


# Load .env file if it exists
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class Config:
    """Application configuration loaded from environment variables."""
    
    # Groq API Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Traffic Sampling Configuration
    TRAFFIC_SAMPLE_RATE: float = float(os.getenv("TRAFFIC_SAMPLE_RATE", "0.1"))
    TIME_WINDOW_MINUTES: int = int(os.getenv("TIME_WINDOW_MINUTES", "60"))
    
    # Paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present."""
        if not cls.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY environment variable is required. "
                "Get your key at https://console.groq.com/keys"
            )
        return True
    
    @classmethod
    def get_model_id(cls) -> str:
        """Get the full model ID for LiteLLM."""
        return f"groq/{cls.GROQ_MODEL}"


# Global config instance
config = Config()
