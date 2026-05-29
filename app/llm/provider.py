"""LLM provider abstraction.

The rest of the codebase depends on the `LLMProvider` *interface*, never on a
concrete vendor SDK (Dependency Inversion Principle). Swapping OpenAI for
Anthropic, Azure-OpenAI or a local Ollama model becomes a one-class change with
no ripple through the agent or API layers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import Settings
from app.core.exceptions import ConfigurationError


class LLMProvider(ABC):
    """Abstract factory for chat models used across the agent."""

    @abstractmethod
    def get_chat_model(self, *, streaming: bool = False, **overrides) -> BaseChatModel:
        """Return a configured LangChain chat model.

        Args:
            streaming: Enable token streaming for this instance.
            overrides: Per-call overrides (e.g. temperature) layered on defaults.
        """
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """OpenAI-backed implementation (default for this deployment)."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is not set. Add it to your environment or .env file."
            )
        self._settings = settings

    def get_chat_model(self, *, streaming: bool = False, **overrides) -> BaseChatModel:
        params = {
            "model": self._settings.llm_model,
            "temperature": self._settings.llm_temperature,
            "api_key": self._settings.openai_api_key,
            "streaming": streaming,
            "timeout": 60,
            "max_retries": 2,
        }
        params.update(overrides)
        return ChatOpenAI(**params)


def build_llm_provider(settings: Settings) -> LLMProvider:
    """Construct the configured LLM provider.

    Extension point: branch on a future `settings.llm_provider` field to return
    `AnthropicProvider`, `OllamaProvider`, etc.
    """
    return OpenAIProvider(settings)
