"""Application settings loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://urie_app:urie@localhost:5432/urie"
    # Superuser URL for Alembic migrations (optional; falls back to database_url)
    database_url_admin: str = "postgresql+asyncpg://urie:urie@localhost:5432/urie"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    app_env: str = "development"
    log_level: str = "INFO"
    embedding_dim: int = 64

    # LLM gateway — default mock so offline/dev works with zero config
    llm_provider: str = "mock"  # mock | openai | anthropic
    llm_api_key: str = ""
    llm_base_url: str = ""  # optional OpenAI-compatible gateway override
    llm_model: str = ""  # provider default if empty
    llm_temperature: float = 0.2
    llm_timeout_s: float = 45.0
    llm_max_retries: int = 3
    llm_max_interview_turns: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
