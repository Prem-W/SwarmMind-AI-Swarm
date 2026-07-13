"""
OpenAI LLM Provider

Real integration with OpenAI's API for completions, streaming, and embeddings.
"""

from typing import AsyncGenerator, List, Optional

import tiktoken
from openai import AsyncOpenAI

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


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider implementation."""

    provider_type = ProviderType.OPENAI

    def __init__(self, api_key: str = None, config: Optional[LLMConfig] = None):
        super().__init__(api_key or settings.openai_api_key, config)
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.tokenizer = self._get_tokenizer()

    def _get_tokenizer(self):
        """Get the appropriate tokenizer for the model."""
        try:
            return tiktoken.encoding_for_model(self.config.model)
        except KeyError:
            return tiktoken.get_encoding("cl100k_base")

    async def complete(self, messages: List[Message], config: Optional[LLMConfig] = None) -> LLMResponse:
        """Send a completion request to OpenAI."""
        cfg = config or self.config
        formatted_messages = self.format_messages(messages)

        try:
            logger.debug(
                "OpenAI completion request",
                model=cfg.model,
                message_count=len(messages),
            )

            response = await self.client.chat.completions.create(
                model=cfg.model,
                messages=formatted_messages,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                top_p=cfg.top_p,
                frequency_penalty=cfg.frequency_penalty,
                presence_penalty=cfg.presence_penalty,
                stop=cfg.stop_sequences,
                timeout=cfg.timeout,
                tools=cfg.tools,
            )

            choice = response.choices[0]
            result = LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                provider=self.provider_type.value,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                finish_reason=choice.finish_reason,
                metadata={
                    "system_fingerprint": getattr(response, "system_fingerprint", None),
                },
            )

            logger.debug(
                "OpenAI completion response",
                model=response.model,
                tokens_used=result.total_tokens,
                finish_reason=choice.finish_reason,
            )

            return result

        except Exception as e:
            logger.error("OpenAI API error", error=str(e))
            raise LLMProviderException(provider="openai", detail=str(e))

    async def stream(self, messages: List[Message], config: Optional[LLMConfig] = None) -> AsyncGenerator[str, None]:
        """Stream completion chunks from OpenAI."""
        cfg = config or self.config
        formatted_messages = self.format_messages(messages)

        try:
            stream = await self.client.chat.completions.create(
                model=cfg.model,
                messages=formatted_messages,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                stream=True,
                timeout=cfg.timeout,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error("OpenAI streaming error", error=str(e))
            raise LLMProviderException(provider="openai", detail=f"Streaming error: {str(e)}")

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI's embedding model."""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
            )
            return [item.embedding for item in response.data]

        except Exception as e:
            logger.error("OpenAI embedding error", error=str(e))
            raise LLMProviderException(provider="openai", detail=f"Embedding error: {str(e)}")

    def count_tokens(self, messages: List[Message]) -> int:
        """Count tokens in messages using tiktoken."""
        count = 0
        for message in messages:
            count += len(self.tokenizer.encode(message.content))
            count += 3  # Role tokens overhead
        count += 3  # Reply priming
        return count

    def validate_config(self) -> bool:
        """Validate OpenAI configuration."""
        if not self.api_key:
            logger.error("OpenAI API key not configured")
            return False
        return True
