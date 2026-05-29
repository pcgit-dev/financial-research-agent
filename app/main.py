"""Application entry point — composition root for the REST service.

Wires configuration, logging, the agent and global error handling into a single
FastAPI app. Heavy singletons are built once in the lifespan handler.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.agent.agent import FinanceResearchAgent
from app.api.routes import router
from app.config import get_settings
from app.core.exceptions import AgentError
from app.core.logging import configure_logging, get_logger
from app.memory.store import SqlConversationStore

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build expensive singletons on startup; dispose on shutdown."""
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=settings.is_production)
    logger.info("startup", app=settings.app_name, env=settings.app_env)

    store = SqlConversationStore(settings.database_url)
    app.state.agent = FinanceResearchAgent(settings=settings, store=store)
    logger.info("agent_ready")

    yield

    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Finance Research Agent API",
        version=__version__,
        description=(
            "An LLM-powered internet-search agent for investment research. "
            "Routes queries between live web search and direct knowledge, "
            "synthesises grounded answers with in-text citations, and streams "
            "responses token-by-token."
        ),
        lifespan=lifespan,
    )

    # CORS — tighten `allow_origins` to known frontends in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.exception_handler(AgentError)
    async def handle_agent_error(_: Request, exc: AgentError) -> JSONResponse:
        logger.warning("agent_error", code=exc.error_code, message=str(exc))
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "message": str(exc)},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_error", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"error_code": "internal_error", "message": "Unexpected error."},
        )

    return app


app = create_app()
