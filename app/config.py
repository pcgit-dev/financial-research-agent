"""Centralised, validated application configuration.

Uses pydantic-settings so every setting is type-checked and overridable via
environment variables or a local `.env` file. A single cached `Settings`
instance is exposed through `get_settings()` (dependency-injection friendly).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings loaded from env / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----
    app_name: str = "finance-research-agent"
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_auth_key: str | None = None  # optional X-API-Key gate; None disables auth

    # ---- LLM ----
    openai_api_key: str = Field(default="", description="OpenAI API key")
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1

    # ---- Search ----
    search_provider: Literal["auto", "tavily", "duckduckgo"] = "auto"
    tavily_api_key: str | None = None
    search_max_results: int = 3

    # ---- Memory ----
    database_url: str = "sqlite:///./data/conversations.db"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()
