"""LangGraph node implementations.

Each node is a pure function that takes an AgentState dict as input and returns a dict of outputs.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.citations import build_citations, format_sources_for_prompt
from app.agent.prompts import (
    DIRECT_SYSTEM_PROMPT,
    SEARCH_SYNTHESIS_SYSTEM_PROMPT,
    SEARCH_SYNTHESIS_USER_PROMPT,
)
from app.agent.router import QueryRouter
from app.agent.state import AgentState
from app.config import Settings
from app.core.logging import get_logger
from app.llm.provider import LLMProvider
from app.tools.base import SearchProvider

logger = get_logger(__name__)

# Tag applied to the final-answer model so the API layer can isolate its tokens
# when streaming (the router model is never tagged this way).
FINAL_ANSWER_TAG = "final_answer"


class AgentNodes:
    """Holds dependencies and exposes node callables for the graph."""

    def __init__(
        self,
        router: QueryRouter,
        search_provider: SearchProvider,
        llm_provider: LLMProvider,
        settings: Settings,
    ) -> None:
        self._router = router
        self._search = search_provider
        self._llm_provider = llm_provider
        self._settings = settings
        # Streaming chat model, tagged so the API can filter its tokens.
        self._answer_model = llm_provider.get_chat_model(streaming=True).with_config(
            tags=[FINAL_ANSWER_TAG]
        )

    # ---- Node: classify the query ----------------------------------------
    def route(self, state: AgentState) -> AgentState:
        decision = self._router.route(state["query"], state.get("history"))
        return {"route": decision.route, "route_reason": decision.reason}

    # ---- Node: web search -------------------------------------------------
    def search(self, state: AgentState) -> AgentState:
        max_results = self._settings.search_max_results
        response = self._search.search(state["query"], max_results=max_results)
        # Enforce the cap even if a provider returns more than requested, so the
        # answer's context and the `sources` list never exceed the configured max.
        results = response.results[:max_results]
        return {
            "search_results": results,
            "search_provider": response.provider,
            "sources": build_citations(results),
        }

    # ---- Node: answer from sources (grounded synthesis) -------------------
    def generate_with_context(self, state: AgentState) -> AgentState:
        results = state.get("search_results", [])
        if not results:
            messages = [
                SystemMessage(content=DIRECT_SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"A web search for '{state['query']}' returned no usable "
                        "results. Tell the user you couldn't retrieve live data "
                        "and suggest how they might refine the query."
                    )
                ),
            ]
        else:
            sources = format_sources_for_prompt(results)
            messages = self._with_history(
                state,
                SystemMessage(content=SEARCH_SYNTHESIS_SYSTEM_PROMPT),
                HumanMessage(
                    content=SEARCH_SYNTHESIS_USER_PROMPT.format(
                        query=state["query"], sources=sources
                    )
                ),
            )
        result = self._answer_model.invoke(messages)
        return {"answer": result.content}

    # ---- Node: answer from model knowledge --------------------------------
    def generate_direct(self, state: AgentState) -> AgentState:
        messages = self._with_history(
            state,
            SystemMessage(content=DIRECT_SYSTEM_PROMPT),
            HumanMessage(content=state["query"]),
        )
        result = self._answer_model.invoke(messages)
        return {"answer": result.content, "sources": []}

    # ---- Helpers ----------------------------------------------------------
    def _with_history(self, state: AgentState, system, user) -> list:
        """Prepend recent conversation turns for follow-up context."""
        messages = [system]
        for turn in state.get("history", [])[-6:]:
            role = turn.get("role")
            content = turn.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                from langchain_core.messages import AIMessage

                messages.append(AIMessage(content=content))
        messages.append(user)
        return messages
