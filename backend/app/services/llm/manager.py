"""
LLM Manager

Central manager for LLM providers with failover, load balancing,
and unified interface for the agent system.
"""

from typing import Dict, List, Optional, Type

from app.core.config import get_settings
from app.core.exceptions import LLMProviderException
from app.core.logging import get_logger
from app.services.llm.base import BaseLLMProvider, LLMConfig, LLMResponse, Message, ProviderType
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.anthropic_provider import AnthropicProvider

logger = get_logger(__name__)
settings = get_settings()

# Provider registry
_PROVIDER_REGISTRY: Dict[ProviderType, Type[BaseLLMProvider]] = {
    ProviderType.OPENAI: OpenAIProvider,
    ProviderType.ANTHROPIC: AnthropicProvider,
}


class LLMManager:
    """Manages LLM providers with caching and failover."""

    def __init__(self):
        self._providers: Dict[ProviderType, BaseLLMProvider] = {}
        self._default_provider = ProviderType(settings.default_llm_provider)
        self._default_model = settings.default_llm_model

    def _get_provider(self, provider_type: Optional[ProviderType] = None) -> BaseLLMProvider:
        """Get or create a provider instance."""
        pt = provider_type or self._default_provider

        if pt not in self._providers:
            provider_class = _PROVIDER_REGISTRY.get(pt)
            if not provider_class:
                raise LLMProviderException(provider=pt.value, detail="Provider not registered")

            provider = provider_class()
            if not provider.validate_config():
                raise LLMProviderException(provider=pt.value, detail="Invalid configuration")

            self._providers[pt] = provider

        return self._providers[pt]

    async def complete(
        self,
        messages: List[Message],
        provider: Optional[ProviderType] = None,
        model: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Send a completion request with automatic failover."""
        cfg = config or LLMConfig()
        if model:
            cfg.model = model

        # Try primary provider
        providers_to_try = [provider, self._default_provider] if provider else [self._default_provider]
        # Add fallback providers
        for pt in ProviderType:
            if pt not in providers_to_try:
                providers_to_try.append(pt)

        last_error = None
        for pt in providers_to_try:
            if pt is None:
                continue
            try:
                llm = self._get_provider(pt)
                return await llm.complete(messages, cfg)
            except LLMProviderException as e:
                last_error = e
                logger.warning(
                    "LLM provider failed, trying next",
                    provider=pt.value,
                    error=str(e),
                )
                continue

        raise LLMProviderException(
            provider="all",
            detail=f"All providers failed. Last error: {str(last_error)}",
        )

    async def stream(
        self,
        messages: List[Message],
        provider: Optional[ProviderType] = None,
        model: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ):
        """Stream completion from the specified provider."""
        cfg = config or LLMConfig()
        cfg.streaming = True
        if model:
            cfg.model = model

        llm = self._get_provider(provider)
        async for chunk in llm.stream(messages, cfg):
            yield chunk

    async def embed(self, texts: List[str], provider: Optional[ProviderType] = None) -> List[List[float]]:
        """Generate embeddings (defaults to OpenAI for embeddings)."""
        # Use OpenAI for embeddings by default
        embed_provider = provider if provider == ProviderType.OPENAI else ProviderType.OPENAI
        llm = self._get_provider(embed_provider)
        return await llm.embed(texts)

    def count_tokens(self, messages: List[Message], provider: Optional[ProviderType] = None) -> int:
        """Count tokens for the specified provider."""
        llm = self._get_provider(provider)
        return llm.count_tokens(messages)

    def get_available_providers(self) -> List[Dict]:
        """List available and configured providers."""
        available = []
        for pt, cls in _PROVIDER_REGISTRY.items():
            provider = cls()
            available.append({
                "type": pt.value,
                "name": pt.value.title(),
                "configured": provider.validate_config(),
                "default_model": settings.default_llm_model if pt == self._default_provider else None,
            })
        return available


# Global LLM manager instance
llm_manager = LLMManager()
