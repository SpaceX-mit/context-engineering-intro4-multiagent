"""Settings configuration for multi-agent code review system."""

from typing import Optional

from dotenv import load_dotenv
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Configuration
    llm_provider: str = Field(
        default="openai",
        description="LLM provider (openai, anthropic, etc.)",
    )

    llm_api_key: Optional[str] = Field(
        default=None,
        description="API key for the LLM provider",
    )

    llm_model: str = Field(
        default="gpt-4o-mini",
        description="Model to use for code review",
    )

    llm_base_url: Optional[str] = Field(
        default="https://api.openai.com/v1",
        description="Base URL for the LLM API",
    )

    # Review Configuration
    max_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum review iterations",
    )

    auto_fix_enabled: bool = Field(
        default=True,
        description="Enable automatic code fixes",
    )

    # Analysis Configuration
    include_security: bool = Field(
        default=True,
        description="Include security scanning",
    )

    include_complexity: bool = Field(
        default=True,
        description="Include complexity analysis",
    )

    # Ruff Configuration
    ruff_config_path: Optional[str] = Field(
        default=None,
        description="Path to ruff configuration file",
    )

    # Bandit Configuration
    bandit_config_path: Optional[str] = Field(
        default=None,
        description="Path to bandit configuration file",
    )

    # WebUI Configuration
    webui_port: int = Field(
        default=7860,
        ge=1024,
        le=65535,
        description="Port for WebUI server",
    )

    webui_host: str = Field(
        default="0.0.0.0",
        description="Host for WebUI server",
    )

    webui_share: bool = Field(
        default=False,
        description="Create public share link",
    )

    # Project Configuration
    project_root: Optional[str] = Field(
        default=None,
        description="Root path for code projects",
    )

    # Safety Configuration
    sandbox_enabled: bool = Field(
        default=True,
        description="Enable sandbox for code execution",
    )

    max_file_size: int = Field(
        default=1024 * 1024,  # 1MB
        description="Maximum file size to process",
    )


def load_settings() -> Settings:
    """Load settings with proper error handling."""
    try:
        return Settings()
    except Exception as e:
        error_msg = f"Failed to load settings: {e}"
        if "llm_api_key" in str(e).lower():
            error_msg += "\nMake sure to set LLM_API_KEY in your .env file"
        raise ValueError(error_msg) from e
