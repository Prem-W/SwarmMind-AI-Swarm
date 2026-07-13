"""
Base Agent Class

All specialized agents inherit from this base. Provides:
- LLM integration via the LLM manager
- Memory access (shared + episodic)
- Tool execution
- Message passing to other agents
- Status management
- Metrics tracking
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.exceptions import AgentExecutionException
from app.core.logging import get_logger
from app.services.llm.base import LLMConfig, LLMResponse, Message
from app.services.llm.manager import llm_manager

settings = get_settings()
logger = get_logger(__name__)


class AgentState(str, Enum):
    """Agent execution state."""

    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"
    DONE = "done"


@dataclass
class AgentContext:
    """Context passed to agents during execution."""

    task_id: str
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    team_id: Optional[str] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    shared_memory: Dict[str, Any] = field(default_factory=dict)
    parent_results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result from agent execution."""

    success: bool
    output: str
    data: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[Dict] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class BaseAgent(ABC):
    """Base class for all SwarmMind agents."""

    agent_type: str = "base"
    default_system_prompt: str = "You are a helpful AI agent."

    def __init__(
        self,
        agent_id: uuid.UUID,
        name: str,
        llm_provider: str = None,
        llm_model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        system_prompt: str = None,
        tools: List[str] = None,
        config: Dict = None,
    ):
        self.agent_id = agent_id
        self.name = name
        self.state = AgentState.IDLE
        self.llm_provider = llm_provider or settings.default_llm_provider
        self.llm_model = llm_model or settings.default_llm_model
        self.temperature = temperature or settings.llm_temperature
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.system_prompt = system_prompt or self.default_system_prompt
        self.tools = tools or []
        self.config = config or {}
        self._message_history: List[Dict] = []
        self._execution_count = 0
        self._total_tokens_used = 0

    def _build_messages(self, prompt: str, context: AgentContext) -> List[Message]:
        """Build message list for LLM completion."""
        messages = [Message(role="system", content=self.system_prompt)]

        # Add relevant memory context
        if context.shared_memory:
            memory_context = self._format_memory(context.shared_memory)
            if memory_context:
                messages.append(Message(role="system", content=memory_context))

        # Add parent results for context
        if context.parent_results:
            for agent_name, result in context.parent_results.items():
                messages.append(
                    Message(
                        role="system",
                        content=f"Previous result from {agent_name}:\n{result}",
                    )
                )

        # Add user prompt
        messages.append(Message(role="user", content=prompt))

        return messages

    def _format_memory(self, memory: Dict[str, Any]) -> str:
        """Format shared memory for inclusion in prompts."""
        if not memory:
            return ""
        parts = ["## Shared Context:"]
        for key, value in memory.items():
            parts.append(f"- {key}: {value}")
        return "\n".join(parts)

    async def _llm_complete(
        self,
        messages: List[Message],
        streaming: bool = False,
    ) -> LLMResponse:
        """Execute LLM completion with metrics tracking."""
        config = LLMConfig(
            model=self.llm_model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        from app.services.llm.base import ProviderType

        provider = ProviderType(self.llm_provider) if self.llm_provider else None

        if streaming:
            # Return the generator for streaming
            return llm_manager.stream(messages, provider=provider, config=config)

        response = await llm_manager.complete(messages, provider=provider, config=config)
        self._total_tokens_used += response.total_tokens
        return response

    async def send_message(
        self,
        target_agent_id: uuid.UUID,
        message: str,
        message_type: str = "direct",
    ) -> Dict:
        """Send a message to another agent via the message bus."""
        from app.services.messaging import MessageBus

        bus = MessageBus()
        return await bus.send(
            sender_id=self.agent_id,
            receiver_id=target_agent_id,
            content=message,
            message_type=message_type,
        )

    async def receive_messages(self) -> List[Dict]:
        """Receive pending messages for this agent."""
        from app.services.messaging import MessageBus

        bus = MessageBus()
        return await bus.receive_for_agent(self.agent_id)

    async def read_memory(
        self,
        query: str = None,
        memory_type: str = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Read from shared memory."""
        from app.services.memory import MemoryService

        service = MemoryService()
        return await service.search(
            query=query,
            agent_id=self.agent_id,
            memory_type=memory_type,
            limit=limit,
        )

    async def write_memory(self, content: str, memory_type: str = "short_term", metadata: Dict = None):
        """Write to shared memory."""
        from app.services.memory import MemoryService

        service = MemoryService()
        return await service.store(
            content=content,
            agent_id=self.agent_id,
            memory_type=memory_type,
            metadata=metadata or {},
        )

    @abstractmethod
    async def execute(self, prompt: str, context: AgentContext) -> AgentResult:
        """Execute the agent's primary function. Must be implemented by subclasses."""
        pass

    async def run(self, prompt: str, context: AgentContext) -> AgentResult:
        """Run the agent with full lifecycle management."""
        start_time = datetime.now(timezone.utc)
        self.state = AgentState.THINKING
        self._execution_count += 1

        try:
            logger.info(
                "Agent starting execution",
                agent_id=str(self.agent_id),
                agent_name=self.name,
                agent_type=self.agent_type,
                task_id=context.task_id,
            )

            self.state = AgentState.EXECUTING
            result = await self.execute(prompt, context)

            if result.success:
                self.state = AgentState.DONE
            else:
                self.state = AgentState.ERROR

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            result.metrics.update({
                "execution_time_seconds": execution_time,
                "agent_type": self.agent_type,
                "agent_name": self.name,
                "tokens_used": self._total_tokens_used,
            })

            logger.info(
                "Agent execution completed",
                agent_id=str(self.agent_id),
                agent_name=self.name,
                success=result.success,
                execution_time=execution_time,
            )

            return result

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(
                "Agent execution failed",
                agent_id=str(self.agent_id),
                agent_name=self.name,
                error=str(e),
                exc_info=True,
            )
            raise AgentExecutionException(
                agent_id=str(self.agent_id),
                task_id=context.task_id,
                detail=str(e),
            )

    def to_dict(self) -> Dict:
        """Serialize agent to dictionary."""
        return {
            "id": str(self.agent_id),
            "name": self.name,
            "agent_type": self.agent_type,
            "state": self.state.value,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "tools": self.tools,
            "execution_count": self._execution_count,
            "total_tokens_used": self._total_tokens_used,
        }
