"""Environment-driven configuration using pydantic-settings.

All runtime knobs live here. Reads from a .env file and the environment;
never from hard-coded paths inside the code.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = Field(default="dev-only-change-me", min_length=8)
    api_reload: bool = False

    # CORS
    frontend_origin: str = "http://localhost:3000"
    cors_allow_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ])

    # Rate limiting (per client IP)
    rate_limit_predict: str = "60/minute"
    rate_limit_batch: str = "300/minute"

    # Database
    database_url: str = f"sqlite+aiosqlite:///{PROJECT_ROOT / 'data' / 'ids.db'}"

    # Audit
    jsonl_audit_enabled: bool = False  # DB is authoritative; JSONL optional

    # Logging
    log_level: str = "INFO"

    # Model selection
    default_model: str | None = None  # None -> auto pick best by cv_score


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
