"""Tavily search provider — purpose-built for LLM agents.

Returns ranked, de-duplicated snippets with relevance scores and source URLs,
which makes downstream citation generation clean and reliable.
"""
from __future__ import annotations

from app.core.exceptions import SearchProviderError
from app.core.logging import get_logger
from app.tools.base import SearchProvider, SearchResponse, SearchResult

logger = get_logger(__name__)


class TavilySearchProvider(SearchProvider):
    name = "tavily"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise SearchProviderError("TAVILY_API_KEY is required for the Tavily provider.")
        # Imported lazily so the dependency is only needed when actually used.
        from tavily import TavilyClient

        self._client = TavilyClient(api_key=api_key)

    def search(self, query: str, *, max_results: int = 3) -> SearchResponse:
        try:
            raw = self._client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_answer=False,
            )
        except Exception as exc:  # noqa: BLE001 — normalise any SDK error
            logger.error("tavily_search_failed", error=str(exc))
            raise SearchProviderError(f"Tavily search failed: {exc}") from exc

        results = [
            SearchResult(
                title=item.get("title", "Untitled"),
                url=item.get("url", ""),
                content=item.get("content", ""),
                score=float(item.get("score", 0.0)),
            )
            for item in raw.get("results", [])
        ]
        logger.info("tavily_search_ok", query=query, hits=len(results))
        return SearchResponse(query=query, results=results, provider=self.name)
