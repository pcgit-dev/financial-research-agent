"""HTTP routes for the Finance Research Agent."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agent.agent import FinanceResearchAgent
from app.api.dependencies import get_agent, verify_api_key
from app.api.schemas import (
    HealthResponse,
    QueryRequest,
    QueryResponse,
)
from app.config import get_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness/readiness probe for load balancers and orchestrators."""
    settings = get_settings()
    from app import __version__

    return HealthResponse(
        app=settings.app_name,
        version=__version__,
        environment=settings.app_env,
    )


@router.post(
    "/query",
    response_model=QueryResponse,
    tags=["agent"],
    dependencies=[Depends(verify_api_key)],
    summary="Ask the agent a financial research question (buffered response).",
)
async def query(
    payload: QueryRequest,
    agent: FinanceResearchAgent = Depends(get_agent),
) -> QueryResponse:
    """Run the agent and return the complete answer once generation finishes."""
    result = await agent.arun(payload.query, payload.conversation_id)
    return QueryResponse(
        conversation_id=result.conversation_id,
        query=payload.query,
        answer=result.answer,
        route=result.route,
        route_reason=result.route_reason,
        sources=result.sources,
    )


@router.post(
    "/query/stream",
    tags=["agent"],
    dependencies=[Depends(verify_api_key)],
    summary="Ask the agent and stream the answer token-by-token (SSE).",
    response_class=StreamingResponse,
)
async def query_stream(
    payload: QueryRequest,
    agent: FinanceResearchAgent = Depends(get_agent),
) -> StreamingResponse:
    """Stream the agent's response as Server-Sent Events.

    Each SSE `data:` line carries one JSON event (see `astream` event shapes:
    metadata, route, token, sources, done, error).
    """

    async def event_generator() -> AsyncIterator[str]:
        async for event in agent.astream(payload.query, payload.conversation_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering (nginx)
        },
    )
