"""Domain-specific exception hierarchy.

Keeping a small, explicit hierarchy lets the API layer map errors to the right
HTTP status codes without leaking implementation detail to clients.
"""
from __future__ import annotations


class AgentError(Exception):
    """Base class for all application errors."""

    status_code: int = 500
    error_code: str = "internal_error"


class ConfigurationError(AgentError):
    """Raised when the service is misconfigured (e.g. missing API keys)."""

    status_code = 500
    error_code = "configuration_error"


class SearchProviderError(AgentError):
    """Raised when the web-search backend fails or is unavailable."""

    status_code = 502
    error_code = "search_provider_error"


class LLMError(AgentError):
    """Raised when the LLM provider call fails."""

    status_code = 502
    error_code = "llm_error"


class InvalidRequestError(AgentError):
    """Raised for semantically invalid client input."""

    status_code = 422
    error_code = "invalid_request"
