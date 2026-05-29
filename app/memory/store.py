"""Conversation memory store.

`ConversationStore` is an interface; `SqlConversationStore` is the SQLAlchemy
implementation. The agent depends on the interface, so an in-memory store (for
tests) or a Redis/DynamoDB store (for scale) can be substituted freely.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.logging import get_logger
from app.memory.models import Base, Conversation, Message

logger = get_logger(__name__)


@dataclass(slots=True)
class ChatTurn:
    role: str
    content: str


class ConversationStore(ABC):
    """Interface for conversation persistence."""

    @abstractmethod
    def get_history(self, conversation_id: str, *, limit: int = 10) -> list[ChatTurn]:
        ...

    @abstractmethod
    def append(self, conversation_id: str, role: str, content: str) -> None:
        ...


class SqlConversationStore(ConversationStore):
    """SQLAlchemy-backed store (SQLite for demo, Postgres-ready for prod)."""

    def __init__(self, database_url: str) -> None:
        self._ensure_sqlite_path(database_url)
        connect_args = (
            {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        )
        self._engine = create_engine(
            database_url, connect_args=connect_args, pool_pre_ping=True
        )
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)
        Base.metadata.create_all(self._engine)
        logger.info("conversation_store_ready", backend=database_url.split(":", 1)[0])

    @staticmethod
    def _ensure_sqlite_path(database_url: str) -> None:
        """Create the parent directory for a file-backed SQLite DB."""
        prefix = "sqlite:///"
        if database_url.startswith(prefix):
            path = database_url[len(prefix):]
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)

    def _get_or_create(self, session: Session, conversation_id: str) -> Conversation:
        convo = session.scalar(
            select(Conversation).where(Conversation.conversation_id == conversation_id)
        )
        if convo is None:
            convo = Conversation(conversation_id=conversation_id)
            session.add(convo)
            session.flush()
        return convo

    def get_history(self, conversation_id: str, *, limit: int = 10) -> list[ChatTurn]:
        with self._session_factory() as session:
            convo = session.scalar(
                select(Conversation).where(
                    Conversation.conversation_id == conversation_id
                )
            )
            if convo is None:
                return []
            # Most recent `limit` turns, returned in chronological order.
            recent = convo.messages[-limit:]
            return [ChatTurn(role=m.role, content=m.content) for m in recent]

    def append(self, conversation_id: str, role: str, content: str) -> None:
        with self._session_factory() as session:
            convo = self._get_or_create(session, conversation_id)
            session.add(
                Message(conversation_pk=convo.id, role=role, content=content)
            )
            session.commit()
