"""
Memory Models

Short-term and long-term memory for agents and the swarm.
Vector embeddings stored in Qdrant, metadata in PostgreSQL.
"""

import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class MemoryType(str, enum.Enum):
    """Types of memory entries."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryEntry(UUIDMixin, TimestampMixin, Base):
    """Memory entry for agent and swarm shared memory."""

    __tablename__ = "memory_entries"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[MemoryType] = mapped_column(
        Enum(MemoryType), default=MemoryType.SHORT_TERM, nullable=False
    )

    # Source
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Embedding (reference to Qdrant)
    embedding_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=True)

    # Metadata
    importance: Mapped[float] = mapped_column(default=1.0, nullable=False)
    access_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_accessed: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list[str]] = mapped_column(default=list, nullable=False)
    metadata: Mapped[dict] = mapped_column(default=dict, nullable=False)

    # TTL for short-term memory
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<MemoryEntry(id={self.id}, type={self.memory_type}, agent={self.agent_id})>"
