"""DuckDuckGo search provider — zero-API-key fallback for local demos.

Lower structure/quality than Tavily and subject to occasional rate limiting,
but requires no signup, so the agent works out-of-the-box.
"""
from __future__ import annotations

from app.core.exceptions import SearchProviderError
from app.core.logging import get_logger
from app.tools.base import SearchProvider, SearchResponse, SearchResult

logger = get_logger(__name__)


class DuckDuckGoSearchProvider(SearchProvider):
    name = "duckduckgo"

    def search(self, query: str, *, max_results: int = 5) -> SearchResponse:
        from duckduckgo_search import DDGS  # lazy import

        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))
        except Exception as exc:  # noqa: BLE001
            logger.error("ddg_search_failed", error=str(exc))
            raise SearchProviderError(f"DuckDuckGo search failed: {exc}") from exc

        results = [
            SearchResult(
                title=item.get("title", "Untitled"),
                url=item.get("href", ""),
                content=item.get("body", ""),
                score=0.0,  # DDG does not expose relevance scores
            )
            for item in raw
        ]
        logger.info("ddg_search_ok", query=query, hits=len(results))
        return SearchResponse(query=query, results=results, provider=self.name)
