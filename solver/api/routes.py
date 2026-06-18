"""Solver service HTTP endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from solver.domain.models import SolveRequest, SolveResponse
from solver.engine.model_builder import build_model
from solver.engine.result_extractor import extract_results
from solver.engine.solver import run_optimization

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/solve", response_model=SolveResponse)
def solve(request: SolveRequest) -> SolveResponse:
    """Run the optimization and return the schedule."""
    logger.info(
        "Solve request: %d employees, %d days",
        len(request.employees),
        len(request.capacity),
    )

    try:
        components = build_model(request)
        outcome = run_optimization(components, request)
        response = extract_results(request, components, outcome)
    except Exception as exc:
        logger.exception("Solver internal error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info("Solve completed: status=%s, time=%.2fs", response.status, response.solve_time_seconds)
    return response


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check — verifies Gurobi is importable."""
    try:
        import gurobipy  # noqa: F401
        return {"status": "healthy", "solver": "gurobi"}
    except ImportError:
        raise HTTPException(status_code=503, detail="gurobipy not available")
