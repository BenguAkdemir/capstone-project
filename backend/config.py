"""Application configuration — loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    solver_url: str = "http://solver:8001"
    solver_timeout_seconds: float = 120.0
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg2://scheduler:scheduler@localhost:5432/hybrid_scheduler"
    weekly_refresh_enabled: bool = True
    weekly_refresh_day: str = "mon"  # APScheduler cron: mon, tue, ...
    weekly_refresh_hour: int = 6

    class Config:
        env_prefix = "APP_"


settings = AppSettings()
