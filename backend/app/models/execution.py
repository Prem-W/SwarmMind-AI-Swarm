"""
Execution Models

Tracks real-time execution state of workflows and agents.
"""

import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ExecutionStatus(str, enum.Enum):
    """Execution lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class Execution(UUIDMixin, TimestampMixin, Base):
    """Execution instance tracking a workflow run."""

    __tablename__ = "executions"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False, index=True
    )

    # Execution details
    triggered_by: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    trigger_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Timing
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Results
    input_snapshot: Mapped[dict] = mapped_column(default=dict, nullable=False)
    output_snapshot: Mapped[dict] = mapped_column(default=dict, nullable=False)
    metrics: Mapped[dict] = mapped_column(default=dict, nullable=False)

    # Agent participation
    agent_ids: Mapped[list[uuid.UUID]] = mapped_column(default=list, nullable=False)
    leader_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="executions")
    logs: Mapped[list["ExecutionLog"]] = relationship(
        "ExecutionLog", back_populates="execution", cascade="all, delete-orphan", order_by="ExecutionLog.timestamp"
    )

    def __repr__(self) -> str:
        return f"<Execution(id={self.id}, workflow={self.workflow_id}, status={self.status})>"


class ExecutionLog(UUIDMixin, Base):
    """Real-time execution log entry for streaming updates."""

    __tablename__ = "execution_logs"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("executions.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # INFO, WARN, ERROR, DEBUG
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(default=dict, nullable=False)

    # Relationships
    execution: Mapped["Execution"] = relationship("Execution", back_populates="logs")

    def __repr__(self) -> str:
        return f"<ExecutionLog(execution={self.execution_id}, level={self.level}, event={self.event_type})>"
