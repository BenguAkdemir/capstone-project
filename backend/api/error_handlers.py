"""Global exception handlers — maps domain exceptions to HTTP responses."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.domain.exceptions import (
    InfeasibleError,
    InvalidInputError,
    SchedulingError,
    SolverError,
    SolverTimeoutError,
)

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Attach exception handlers to the FastAPI application."""

    @app.exception_handler(InvalidInputError)
    async def handle_invalid_input(request: Request, exc: InvalidInputError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": str(exc),
                "issues": exc.issues,
            },
        )

    @app.exception_handler(InfeasibleError)
    async def handle_infeasible(request: Request, exc: InfeasibleError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "error": "infeasible",
                "message": "The scheduling problem has no feasible solution",
                "explanation": exc.explanation,
            },
        )

    @app.exception_handler(SolverTimeoutError)
    async def handle_timeout(request: Request, exc: SolverTimeoutError) -> JSONResponse:
        return JSONResponse(
            status_code=504,
            content={
                "error": "solver_timeout",
                "message": str(exc),
                "elapsed_seconds": exc.elapsed_seconds,
                "best_objective": exc.best_objective,
            },
        )

    @app.exception_handler(SolverError)
    async def handle_solver_error(request: Request, exc: SolverError) -> JSONResponse:
        logger.error("Solver error: %s", exc)
        return JSONResponse(
            status_code=502,
            content={
                "error": "solver_error",
                "message": "The optimization solver encountered an internal error",
            },
        )

    @app.exception_handler(SchedulingError)
    async def handle_scheduling_error(request: Request, exc: SchedulingError) -> JSONResponse:
        logger.error("Unhandled scheduling error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
            },
        )
