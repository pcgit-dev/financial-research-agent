"""Factory that selects a search provider from configuration.

`SEARCH_PROVIDER=auto` resolves to Tavily when a key is present and falls back
to DuckDuckGo otherwise — production uses Tavily, local demos work key-free.
"""
from __future__ import annotations

from app.config import Settings
from app.core.logging import get_logger
from app.tools.base import SearchProvider
from app.tools.duckduckgo_search import DuckDuckGoSearchProvider
from app.tools.tavily_search import TavilySearchProvider

logger = get_logger(__name__)


def build_search_provider(settings: Settings) -> SearchProvider:
    """Return the configured search provider instance."""
    choice = settings.search_provider

    if choice == "auto":
        choice = "tavily" if settings.tavily_api_key else "duckduckgo"
        logger.info("search_provider_auto_resolved", resolved=choice)

    if choice == "tavily":
        return TavilySearchProvider(api_key=settings.tavily_api_key or "")
    if choice == "duckduckgo":
        return DuckDuckGoSearchProvider()

    raise ValueError(f"Unknown search provider: {settings.search_provider}")
