"""
Base LLM Provider Interface

Defines the contract that all LLM providers must implement.
This allows seamless switching between OpenAI, Anthropic, and other providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional


class ProviderType(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    # Future providers: AZURE, GEMINI, LOCAL, etc.


@dataclass
class Message:
    """A chat message."""

    role: str  # system, user, assistant, tool
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class LLMResponse:
    """Standardized LLM response."""

    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def input_tokens(self) -> int:
        return self.usage.get("prompt_tokens", 0) or self.usage.get("input_tokens", 0)

    @property
    def output_tokens(self) -> int:
        return self.usage.get("completion_tokens", 0) or self.usage.get("output_tokens", 0)

    @property
    def total_tokens(self) -> int:
        return self.usage.get("total_tokens", self.input_tokens + self.output_tokens)


@dataclass
class LLMConfig:
    """Configuration for LLM requests."""

    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    timeout: int = 120
    streaming: bool = False
    tools: Optional[List[Dict]] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    provider_type: ProviderType

    def __init__(self, api_key: str, config: Optional[LLMConfig] = None):
        self.api_key = api_key
        self.config = config or LLMConfig()

    @abstractmethod
    async def complete(self, messages: List[Message], config: Optional[LLMConfig] = None) -> LLMResponse:
        """Send a completion request to the LLM."""
        pass

    @abstractmethod
    async def stream(self, messages: List[Message], config: Optional[LLMConfig] = None) -> AsyncGenerator[str, None]:
        """Stream completion chunks from the LLM."""
        pass

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for the given texts."""
        pass

    @abstractmethod
    def count_tokens(self, messages: List[Message]) -> int:
        """Count tokens in the given messages."""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate the provider configuration."""
        pass

    def format_messages(self, messages: List[Message]) -> List[Dict]:
        """Format messages for the provider's API. Override per provider."""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                **({"name": msg.name} if msg.name else {}),
            }
            for msg in messages
        ]
