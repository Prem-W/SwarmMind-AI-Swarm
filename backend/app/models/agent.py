"""
Agent Models

Defines the agent types, statuses, and agent configurations.
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class AgentType(str, enum.Enum):
    """Types of specialized agents in the swarm."""

    PLANNER = "planner"
    RESEARCH = "research"
    CODING = "coding"
    REVIEWER = "reviewer"
    TESTING = "testing"
    MEMORY = "memory"
    TOOL = "tool"
    CUSTOM = "custom"


class AgentStatus(str, enum.Enum):
    """Agent lifecycle statuses."""

    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    ERROR = "error"
    OFFLINE = "offline"
    LEADER = "leader"


class Agent(UUIDMixin, TimestampMixin, Base):
    """Agent model representing a specialized AI agent in the swarm."""

    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType), nullable=False)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), default=AgentStatus.IDLE, nullable=False, index=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # LLM Configuration
    llm_provider: Mapped[str] = mapped_column(String(50), default="openai", nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), default="gpt-4o", nullable=False)
    temperature: Mapped[float] = mapped_column(default=0.7, nullable=False)
    max_tokens: Mapped[int] = mapped_column(default=4096, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=True)

    # Capabilities & Tools
    tools: Mapped[list[str]] = mapped_column(default=list, nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(default=list, nullable=False)
    config: Mapped[dict] = mapped_column(default=dict, nullable=False)

    # Execution stats
    total_tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tasks_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_execution_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="agents")
    owner: Mapped["User"] = relationship("User")
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="assigned_agent", foreign_keys="Task.assigned_agent_id"
    )
    workflow_steps: Mapped[list["WorkflowStep"]] = relationship(
        "WorkflowStep", back_populates="agent"
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name}, type={self.agent_type}, status={self.status})>"

    @property
    def is_available(self) -> bool:
        """Check if agent is available for task assignment."""
        return self.status in [AgentStatus.IDLE, AgentStatus.LEADER] and self.is_active
