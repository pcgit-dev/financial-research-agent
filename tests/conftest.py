"""Shared test fixtures.

A dummy OPENAI_API_KEY lets the app start (the OpenAI client is constructed but
never called — the agent is overridden with a fake), so tests run fully offline.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("SEARCH_PROVIDER", "duckduckgo")

import pytest
from fastapi.testclient import TestClient

from app.agent.agent import AgentResult
from app.api.dependencies import get_agent
from app.main import create_app


class FakeAgent:
    """Deterministic stand-in for FinanceResearchAgent (no network)."""

    async def arun(self, query: str, conversation_id=None) -> AgentResult:
        cid = conversation_id or "test-conversation"
        if "diversification" in query.lower():
            return AgentResult(
                answer="Diversification spreads risk across assets.",
                route="direct",
                route_reason="Conceptual question.",
                citations=[],
                search_provider=None,
                conversation_id=cid,
            )
        return AgentResult(
            answer="The EUR/USD rate is 1.0847 [1].\n\n---\n**Sources:**\n[1] FX feed\n    https://example.com",
            route="search",
            route_reason="Time-sensitive query.",
            citations=[{"index": 1, "title": "FX feed", "url": "https://example.com", "published_date": None}],
            search_provider="duckduckgo",
            conversation_id=cid,
        )

    async def astream(self, query: str, conversation_id=None):
        cid = conversation_id or "test-conversation"
        yield {"type": "metadata", "conversation_id": cid}
        yield {"type": "route", "route": "direct", "reason": "Conceptual question."}
        yield {"type": "token", "content": "Diversification "}
        yield {"type": "token", "content": "spreads risk."}
        yield {"type": "done", "answer": "Diversification spreads risk."}


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_agent] = lambda: FakeAgent()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
