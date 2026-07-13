"""
Task Models

Defines tasks that agents execute, including status tracking,
priorities, and results.
"""

import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class TaskStatus(str, enum.Enum):
    """Task execution lifecycle."""

    PENDING = "pending"
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class TaskPriority(str, enum.Enum):
    """Task priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Task(UUIDMixin, TimestampMixin, Base):
    """Task model representing a unit of work for an agent."""

    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False
    )

    # Assignment
    assigned_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=True
    )
    parent_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("executions.id", ondelete="SET NULL"), nullable=True
    )

    # Task details
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    input_data: Mapped[dict] = mapped_column(default=dict, nullable=False)
    output_data: Mapped[dict] = mapped_column(default=dict, nullable=False)
    context: Mapped[dict] = mapped_column(default=dict, nullable=False)

    # Execution tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Human approval
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Metadata
    tags: Mapped[list[str]] = mapped_column(default=list, nullable=False)
    metadata: Mapped[dict] = mapped_column(default=dict, nullable=False)

    # Relationships
    assigned_agent: Mapped["Agent"] = relationship(
        "Agent", back_populates="tasks", foreign_keys=[assigned_agent_id]
    )
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="tasks")
    subtasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="parent_task", remote_side="Task.id"
    )
    parent_task: Mapped["Task"] = relationship(
        "Task", back_populates="subtasks", remote_side="Task.parent_task_id"
    )
    result: Mapped["TaskResult"] = relationship(
        "TaskResult", back_populates="task", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title}, status={self.status})>"


class TaskResult(UUIDMixin, TimestampMixin, Base):
    """Task execution result with output and artifacts."""

    __tablename__ = "task_results"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    output: Mapped[str] = mapped_column(Text, nullable=True)
    output_data: Mapped[dict] = mapped_column(default=dict, nullable=False)
    artifacts: Mapped[list[dict]] = mapped_column(default=list, nullable=False)
    metrics: Mapped[dict] = mapped_column(default=dict, nullable=False)
    token_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_estimate: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="result")

    def __repr__(self) -> str:
        return f"<TaskResult(task_id={self.task_id})>"
