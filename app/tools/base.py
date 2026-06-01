"""Search-provider abstraction.

`SearchResult` is a provider-agnostic value object; `SearchProvider` is the
interface every backend must satisfy. The agent depends only on these, so new
providers (SerpAPI, Bing, internal data lake) plug in without touching agent
logic — Open/Closed + Dependency Inversion.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(slots=True)
class SearchResult:
    """A single normalised web-search hit."""

    title: str
    url: str
    content: str
    score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": self.score,
        }


@dataclass(slots=True)
class SearchResponse:
    """Aggregate result of a search call."""

    query: str
    results: list[SearchResult] = field(default_factory=list)
    provider: str = "unknown"

    @property
    def is_empty(self) -> bool:
        return len(self.results) == 0


class SearchProvider(ABC):
    """Interface for web-search backends."""

    name: str = "base"

    @abstractmethod
    def search(self, query: str, *, max_results: int = 5) -> SearchResponse:
        """Run a synchronous web search and return normalised results."""
        raise NotImplementedError
