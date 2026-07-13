"""
Workflow Models

Defines workflows that orchestrate multiple agents and tasks.
"""

import enum
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class WorkflowStatus(str, enum.Enum):
    """Workflow execution lifecycle."""

    DRAFT = "draft"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class Workflow(UUIDMixin, TimestampMixin, Base):
    """Workflow model representing a multi-agent orchestration pipeline."""

    __tablename__ = "workflows"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus), default=WorkflowStatus.DRAFT, nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Ownership
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )

    # Configuration
    input_data: Mapped[dict] = mapped_column(default=dict, nullable=False)
    output_data: Mapped[dict] = mapped_column(default=dict, nullable=False)
    config: Mapped[dict] = mapped_column(default=dict, nullable=False)
    schedule: Mapped[str] = mapped_column(String(255), nullable=True)  # Cron expression
    is_template: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Execution tracking
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_execution_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Parallelism
    max_parallel_agents: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    enable_dynamic_agents: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_failure_recovery: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_human_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="owned_workflows")
    team: Mapped["Team"] = relationship("Team", back_populates="workflows")
    steps: Mapped[list["WorkflowStep"]] = relationship(
        "WorkflowStep", back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowStep.order"
    )
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="workflow")
    executions: Mapped[list["Execution"]] = relationship(
        "Execution", back_populates="workflow"
    )

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name={self.name}, status={self.status})>"


class WorkflowStep(UUIDMixin, TimestampMixin, Base):
    """A step within a workflow that maps to an agent and task template."""

    __tablename__ = "workflow_steps"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Step configuration
    input_mapping: Mapped[dict] = mapped_column(default=dict, nullable=False)
    output_mapping: Mapped[dict] = mapped_column(default=dict, nullable=False)
    conditions: Mapped[dict] = mapped_column(default=dict, nullable=False)  # Conditional logic
    retry_policy: Mapped[dict] = mapped_column(default=dict, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Parallel execution
    parallel_with: Mapped[list[uuid.UUID]] = mapped_column(default=list, nullable=False)
    depends_on: Mapped[list[uuid.UUID]] = mapped_column(default=list, nullable=False)

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="steps")
    agent: Mapped["Agent"] = relationship("Agent", back_populates="workflow_steps")

    def __repr__(self) -> str:
        return f"<WorkflowStep(id={self.id}, name={self.name}, order={self.order})>"
