"""FastAPI dependency injection wiring."""

from __future__ import annotations

from functools import lru_cache

from backend.application.optimization_service import OptimizationService
from backend.infrastructure.gurobi_adapter import GurobiHttpAdapter


@lru_cache(maxsize=1)
def get_optimization_service() -> OptimizationService:
    """Singleton service wired with the HTTP solver adapter."""
    solver = GurobiHttpAdapter()
    return OptimizationService(solver=solver)
