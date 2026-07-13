"""
Anthropic LLM Provider

Real integration with Anthropic's Claude API for completions and streaming.
"""

from typing import AsyncGenerator, List, Optional

from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.core.exceptions import LLMProviderException
from app.core.logging import get_logger
from app.services.llm.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMResponse,
    Message,
    ProviderType,
)

logger = get_logger(__name__)
settings = get_settings()


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider implementation."""

    provider_type = ProviderType.ANTHROPIC

    def __init__(self, api_key: str = None, config: Optional[LLMConfig] = None):
        super().__init__(api_key or settings.anthropic_api_key, config)
        self.client = AsyncAnthropic(api_key=self.api_key)

    def _convert_messages(self, messages: List[Message]) -> tuple:
        """Convert generic messages to Anthropic format (system + messages)."""
        system_content = ""
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system_content += msg.content + "\n"
            else:
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        return system_content.strip(), anthropic_messages

    async def complete(self, messages: List[Message], config: Optional[LLMConfig] = None) -> LLMResponse:
        """Send a completion request to Anthropic."""
        cfg = config or self.config
        system, anthropic_messages = self._convert_messages(messages)

        try:
            logger.debug(
                "Anthropic completion request",
                model=cfg.model,
                message_count=len(messages),
            )

            kwargs = {
                "model": cfg.model,
                "messages": anthropic_messages,
                "max_tokens": cfg.max_tokens,
                "temperature": cfg.temperature,
                "top_p": cfg.top_p,
                "timeout": cfg.timeout,
            }
            if system:
                kwargs["system"] = system

            response = await self.client.messages.create(**kwargs)

            # Extract text content
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            result = LLMResponse(
                content=content,
                model=response.model,
                provider=self.provider_type.value,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
                finish_reason=response.stop_reason,
            )

            logger.debug(
                "Anthropic completion response",
                model=response.model,
                tokens_used=result.total_tokens,
                stop_reason=response.stop_reason,
            )

            return result

        except Exception as e:
            logger.error("Anthropic API error", error=str(e))
            raise LLMProviderException(provider="anthropic", detail=str(e))

    async def stream(self, messages: List[Message], config: Optional[LLMConfig] = None) -> AsyncGenerator[str, None]:
        """Stream completion chunks from Anthropic."""
        cfg = config or self.config
        system, anthropic_messages = self._convert_messages(messages)

        try:
            kwargs = {
                "model": cfg.model,
                "messages": anthropic_messages,
                "max_tokens": cfg.max_tokens,
                "temperature": cfg.temperature,
                "stream": True,
                "timeout": cfg.timeout,
            }
            if system:
                kwargs["system"] = system

            async with self.client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error("Anthropic streaming error", error=str(e))
            raise LLMProviderException(provider="anthropic", detail=f"Streaming error: {str(e)}")

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Anthropic doesn't have a direct embedding API - fallback needed."""
        # This would typically call OpenAI embeddings or a local model
        raise LLMProviderException(
            provider="anthropic",
            detail="Anthropic does not provide embeddings. Use OpenAI provider for embeddings.",
        )

    def count_tokens(self, messages: List[Message]) -> int:
        """Estimate token count (approximate for Anthropic)."""
        # Rough estimation: ~4 chars per token
        total_chars = sum(len(msg.content) for msg in messages)
        return total_chars // 4 + len(messages) * 3

    def validate_config(self) -> bool:
        """Validate Anthropic configuration."""
        if not self.api_key:
            logger.error("Anthropic API key not configured")
            return False
        return True
