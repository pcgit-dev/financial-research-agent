"""FinanceResearchAgent — the public façade over the LangGraph pipeline.

Responsibilities:
- Wire together LLM, search, router, memory and the compiled graph (composition
  root for the agent subsystem).
- Load/persist conversation memory around each turn.
- Expose two entry points the API uses:
    * `arun`    — full, buffered response (for POST /query).
    * `astream` — token-by-token streaming events (for POST /query/stream).
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from app.agent.citations import format_reference_list
from app.agent.graph import build_graph
from app.agent.nodes import FINAL_ANSWER_TAG, AgentNodes
from app.agent.router import QueryRouter
from app.agent.state import AgentState, Citation
from app.config import Settings
from app.core.logging import get_logger
from app.llm.provider import LLMProvider, build_llm_provider
from app.memory.store import ConversationStore
from app.tools.base import SearchProvider
from app.tools.factory import build_search_provider

logger = get_logger(__name__)


@dataclass(slots=True)
class AgentResult:
    """Buffered (non-streaming) result of a single turn."""

    answer: str
    route: str
    route_reason: str
    citations: list[Citation]
    search_provider: str | None
    conversation_id: str


class FinanceResearchAgent:
    """High-level entry point used by the REST API."""

    def __init__(
        self,
        settings: Settings,
        store: ConversationStore,
        llm_provider: LLMProvider | None = None,
        search_provider: SearchProvider | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        llm_provider = llm_provider or build_llm_provider(settings)
        search_provider = search_provider or build_search_provider(settings)
        router = QueryRouter(llm_provider)
        nodes = AgentNodes(router, search_provider, llm_provider, settings)
        self._graph = build_graph(nodes)

    # ---- Public API -------------------------------------------------------
    async def arun(self, query: str, conversation_id: str | None = None) -> AgentResult:
        """Run one turn end-to-end and return the complete answer."""
        conversation_id = conversation_id or self._new_conversation_id()
        initial = self._build_initial_state(query, conversation_id)

        final_state: AgentState = await self._graph.ainvoke(initial)

        answer = final_state.get("answer", "")
        citations = final_state.get("citations", [])
        full_answer = answer + format_reference_list(citations)

        self._persist_turn(conversation_id, query, full_answer)

        return AgentResult(
            answer=full_answer,
            route=final_state.get("route", "direct"),
            route_reason=final_state.get("route_reason", ""),
            citations=citations,
            search_provider=final_state.get("search_provider"),
            conversation_id=conversation_id,
        )

    async def astream(
        self, query: str, conversation_id: str | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Run one turn and yield streaming events.

        Event shapes (all dicts with a "type" discriminator):
          {"type": "metadata", "conversation_id": ...}
          {"type": "route", "route": ..., "reason": ...}
          {"type": "token", "content": "..."}
          {"type": "sources", "citations": [...]}
          {"type": "done", "answer": "<full text incl. references>"}
          {"type": "error", "message": "..."}
        """
        conversation_id = conversation_id or self._new_conversation_id()
        initial = self._build_initial_state(query, conversation_id)

        yield {"type": "metadata", "conversation_id": conversation_id}

        answer_parts: list[str] = []
        citations: list[Citation] = []

        try:
            # Multiplex two stream modes: node "updates" for routing/citations,
            # "messages" for raw LLM tokens of the final-answer model.
            async for mode, chunk in self._graph.astream(
                initial, stream_mode=["updates", "messages"]
            ):
                if mode == "updates":
                    event = self._handle_update(chunk)
                    if event:
                        if event["type"] == "sources":
                            citations = event["citations"]
                        yield event
                elif mode == "messages":
                    token = self._extract_token(chunk)
                    if token:
                        answer_parts.append(token)
                        yield {"type": "token", "content": token}

            # Append the formatted reference list as a final token burst so the
            # client's rendered text matches the buffered endpoint exactly.
            reference_block = format_reference_list(citations)
            if reference_block:
                answer_parts.append(reference_block)
                yield {"type": "token", "content": reference_block}

            full_answer = "".join(answer_parts)
            self._persist_turn(conversation_id, query, full_answer)
            yield {"type": "done", "answer": full_answer}

        except Exception as exc:  # noqa: BLE001 — surface a clean stream error
            logger.error("stream_failed", error=str(exc))
            yield {"type": "error", "message": str(exc)}

    # ---- Internals --------------------------------------------------------
    def _build_initial_state(self, query: str, conversation_id: str) -> AgentState:
        history = [
            {"role": t.role, "content": t.content}
            for t in self._store.get_history(conversation_id, limit=10)
        ]
        return {
            "query": query,
            "conversation_id": conversation_id,
            "history": history,
        }

    @staticmethod
    def _handle_update(chunk: dict) -> dict | None:
        """Translate a node-update chunk into a client-facing event."""
        for node_name, update in chunk.items():
            if node_name == "classify":
                return {
                    "type": "route",
                    "route": update.get("route"),
                    "reason": update.get("route_reason"),
                }
            if node_name == "search":
                return {
                    "type": "sources",
                    "citations": update.get("citations", []),
                    "provider": update.get("search_provider"),
                }
        return None

    @staticmethod
    def _extract_token(chunk: Any) -> str:
        """Pull text from a 'messages' stream chunk, filtered to final answer."""
        # chunk is a (message_chunk, metadata) tuple.
        try:
            message_chunk, metadata = chunk
        except (TypeError, ValueError):
            return ""
        if FINAL_ANSWER_TAG not in (metadata or {}).get("tags", []):
            return ""
        content = getattr(message_chunk, "content", "")
        return content if isinstance(content, str) else ""

    def _persist_turn(self, conversation_id: str, query: str, answer: str) -> None:
        self._store.append(conversation_id, "user", query)
        self._store.append(conversation_id, "assistant", answer)

    @staticmethod
    def _new_conversation_id() -> str:
        return uuid.uuid4().hex
