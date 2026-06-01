"""Pydantic request/response schemas for the REST API.

These double as the OpenAPI contract (auto-rendered at /docs) and the single
source of truth for validation.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's financial research question.",
        examples=["What is the latest Fed interest rate decision?"],
    )
    conversation_id: str | None = Field(
        default=None,
        description=(
            "Optional. Pass an existing id to continue a conversation and reuse "
            "its memory; omit it to start a new one (the response returns a new id)."
        ),
        examples=["3f9a1c2e8b7d4f06a1c2e8b7d4f06a1c"],
    )


class CitationModel(BaseModel):
    index: int = Field(..., description="1-based number used inline in the answer.")
    title: str
    url: str


class QueryResponse(BaseModel):
    conversation_id: str = Field(..., description="Id to reuse for follow-up turns.")
    query: str
    answer: str = Field(..., description="Final answer, incl. inline [n] citations and a source list.")
    route: Literal["search", "direct"] = Field(..., description="Path the agent took.")
    route_reason: str = Field(..., description="Why the agent chose that path.")
    sources: list[CitationModel] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    app: str
    version: str
    environment: str


class ErrorResponse(BaseModel):
    error_code: str = Field(..., examples=["search_provider_error"])
    message: str = Field(..., examples=["Tavily search failed: rate limited"])
