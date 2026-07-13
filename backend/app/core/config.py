"""
SwarmMind Application Configuration

Pydantic Settings with environment variable support.
All configuration is centralized here for type safety and validation.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "SwarmMind"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    api_v1_prefix: str = "/api/v1"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # --- Database ---
    database_url: PostgresDsn = "postgresql+asyncpg://swarmmind:swarmmind@localhost:5432/swarmmind"

    # --- Redis ---
    redis_url: RedisDsn = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_worker_concurrency: int = 4

    # --- Qdrant ---
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: Optional[str] = None
    qdrant_collection: str = "swarmmind_memory"

    # --- LLM Providers ---
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096

    # --- Authentication ---
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # --- CORS ---
    frontend_url: str = "http://localhost:5173"
    allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Logging ---
    log_level: str = "INFO"
    log_format: str = "json"

    # --- Feature Flags ---
    human_approval_mode: bool = True
    max_retry_attempts: int = 3
    task_timeout_seconds: int = 300
    swarm_max_agents: int = 10

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def sync_database_url(self) -> str:
        """Return synchronous database URL for Alembic/ Celery."""
        return str(self.database_url).replace("+asyncpg", "")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
