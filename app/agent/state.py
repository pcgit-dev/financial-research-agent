"""Typed state shared across LangGraph nodes.

The state is the single source of truth that flows through the graph: each node
reads what it needs and writes back a partial update, which LangGraph merges.
"""
from __future__ import annotations

from typing import Literal, TypedDict

from app.tools.base import SearchResult

Route = Literal["search", "direct"]


class Citation(TypedDict):
    index: int       # 1-based number used in the answer text, e.g. "[1]"
    title: str
    url: str


class AgentState(TypedDict, total=False):
    """State object passed between graph nodes."""

    # ---- Inputs ----
    query: str
    conversation_id: str
    history: list[dict]            # prior turns: [{"role": ..., "content": ...}]

    # ---- Routing ----
    route: Route
    route_reason: str

    # ---- Search ----
    search_results: list[SearchResult]
    search_provider: str

    # ---- Output ----
    answer: str
    sources: list[Citation]
