"""Application configuration — loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    solver_url: str = "http://solver:8001"
    solver_timeout_seconds: float = 120.0
    log_level: str = "INFO"

    class Config:
        env_prefix = "APP_"


settings = AppSettings()
