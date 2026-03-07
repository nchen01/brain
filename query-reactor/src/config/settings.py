"""Pydantic settings for QueryReactor system."""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional


class QueryReactorSettings(BaseSettings):
    """QueryReactor system settings with environment variable support."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"  # Allow extra fields from .env
    )
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_org_id: Optional[str] = None
    
    # LangSmith Configuration
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_project: str = "queryreactor"
    
    # Model Configuration
    default_model: str = "gpt-5-mini-2025-08-07"  # Use latest GPT-5 mini by default
    fallback_model: str = "gpt-4o-mini"  # Fallback to GPT-4o-mini if GPT-5 unavailable
    
    # System Configuration
    debug: bool = False
    log_level: str = "INFO"


# Global settings instance
settings = QueryReactorSettings()