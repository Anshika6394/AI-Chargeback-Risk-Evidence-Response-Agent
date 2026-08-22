"""Environment-driven application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Chargeback Risk & Evidence Response Agent"
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./chargeback_risk.db"
    gemini_api_key: str | None = None
    backend_cors_origins: str = "http://localhost:5173"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("DATABASE_URL must not be empty")
        supported_prefixes = ("sqlite:///", "sqlite+pysqlite:///", "postgresql://", "postgresql+psycopg://")
        if not value.startswith(supported_prefixes):
            raise ValueError("DATABASE_URL must be a SQLite or PostgreSQL-compatible SQLAlchemy URL")
        return value

    @field_validator("backend_cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [o.strip() for o in value.split(",") if o.strip()]
        if not origins:
            raise ValueError("BACKEND_CORS_ORIGINS must contain at least one origin")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
