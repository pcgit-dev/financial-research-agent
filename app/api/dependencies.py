"""FastAPI dependency providers.

The agent and store are expensive to construct (LLM clients, DB engine), so we
build them once at startup, stash them on `app.state`, and hand them to routes
via dependency injection. Optional API-key auth is enforced here too.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status

from app.agent.agent import FinanceResearchAgent
from app.config import Settings, get_settings


def get_agent(request: Request) -> FinanceResearchAgent:
    """Return the singleton agent created during application startup."""
    agent = getattr(request.app.state, "agent", None)
    if agent is None:  # pragma: no cover — guarded by lifespan startup
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent is not initialised.",
        )
    return agent


def verify_api_key(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Enforce the optional X-API-Key gate (no-op when API_AUTH_KEY is unset)."""
    if not settings.api_auth_key:
        return
    if x_api_key != settings.api_auth_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
