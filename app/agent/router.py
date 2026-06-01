"""Smart query router.

Decides whether a query needs a live web search or can be answered directly.
We use the LLM with *structured output* rather than brittle keyword matching:
it generalises to phrasings we never hard-coded while staying cheap on a small
model. A fast keyword pre-check short-circuits the obvious time-sensitive cases
to save a round-trip.
"""
from __future__ import annotations

import re

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agent.prompts import ROUTER_SYSTEM_PROMPT, ROUTER_USER_PROMPT
from app.agent.state import Route
from app.core.logging import get_logger
from app.llm.provider import LLMProvider

logger = get_logger(__name__)

# Strong signals that a query is time-sensitive → skip the LLM, go straight to search.//This must be internationalization support.
_REALTIME_PATTERNS = re.compile(
    r"\b(current|latest|today|now|recent|live|breaking|this (week|month|year)|"
    r"stock price|exchange rate|yield|as of)\b",
    re.IGNORECASE,
)


class RouteDecision(BaseModel):
    """Structured routing verdict returned by the LLM."""

    route: Route = Field(description="Either 'search' or 'direct'.")
    reason: str = Field(description="One short sentence justifying the choice.")


class QueryRouter:
    """Classifies queries into 'search' vs 'direct'."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        # Routing is a classification task: force temperature 0 for determinism.
        model = llm_provider.get_chat_model(temperature=0)
        self._classifier = model.with_structured_output(RouteDecision)

    def route(self, query: str, history: list[dict] | None = None) -> RouteDecision:
        if _REALTIME_PATTERNS.search(query):
            decision = RouteDecision(
                route="search",
                reason="Query contains a time-sensitive signal (fast-path).",
            )
            logger.info("route_decision", route=decision.route, fast_path=True)
            return decision

        history_text = self._format_history(history or [])
        messages = [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(
                content=ROUTER_USER_PROMPT.format(history=history_text, query=query)
            ),
        ]
        decision: RouteDecision = self._classifier.invoke(messages)
        logger.info("route_decision", route=decision.route, fast_path=False)
        return decision

    @staticmethod
    def _format_history(history: list[dict]) -> str:
        if not history:
            return "(no prior messages)"
        return "\n".join(f"{turn['role']}: {turn['content']}" for turn in history[-4:])
