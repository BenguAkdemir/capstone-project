"""Solver service configuration — loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class SolverSettings(BaseSettings):
    time_limit_seconds: float = 300.0
    mip_gap: float = 0.01
    log_output: bool = False
    threads: int = 0  # 0 = auto

    class Config:
        env_prefix = "SOLVER_"


settings = SolverSettings()
