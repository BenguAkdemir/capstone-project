"""Global exception handlers — maps domain exceptions to HTTP responses."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.domain.exceptions import (
    InfeasibleError,
    InvalidInputError,
    SchedulingError,
    SolverError,
    SolverTimeoutError,
)

logger = logging.getLogger(__name__)

_FIELD_LABELS: dict[str, str] = {
    "employees": "Employees",
    "availability": "Availability",
    "preferences": "Preferences",
    "capacity": "Capacity",
    "collaboration": "Collaboration",
    "weights": "Weights",
}


def _pydantic_message(err: dict) -> str:
    loc = err.get("loc", ())
    field = str(loc[-1]) if loc else "input"
    field_label = _FIELD_LABELS.get(field, field)
    msg = err.get("msg", "Invalid value")

    if "min_days" in str(loc) and "max_days" in msg:
        return "Minimum office days cannot exceed maximum office days."
    if "preferred" in str(loc) and "avoid" in msg:
        return "Cannot set both 'prefer' and 'avoid' for the same day."
    if err.get("type") == "missing":
        return f"{field_label} is required."

    return f"{field_label}: {msg}"


def register_error_handlers(app: FastAPI) -> None:
    """Attach exception handlers to the FastAPI application."""

    @app.exception_handler(RequestValidationError)
    async def handle_pydantic_validation(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        issues = [
            {
                "field": str(err.get("loc", ["body"])[-1]),
                "message": _pydantic_message(err),
                "severity": "error",
                "code": err.get("type", "schema_error"),
            }
            for err in exc.errors()
        ]
        summary = issues[0]["message"] if len(issues) == 1 else (
            f"Input validation failed ({len(issues)} error(s)). "
            f"First issue: {issues[0]['message']}"
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": summary,
                "issues": issues,
            },
        )

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
                "message": exc.explanation,
                "explanation": exc.explanation,
                "rules": exc.rules,
            },
        )

    @app.exception_handler(SolverTimeoutError)
    async def handle_timeout(request: Request, exc: SolverTimeoutError) -> JSONResponse:
        return JSONResponse(
            status_code=504,
            content={
                "error": "solver_timeout",
                "message": (
                    f"Optimization did not finish within {exc.elapsed_seconds:.0f} seconds. "
                    "Try relaxing constraints or increasing the time limit."
                ),
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
                "message": exc.user_message,
            },
        )

    @app.exception_handler(SchedulingError)
    async def handle_scheduling_error(request: Request, exc: SchedulingError) -> JSONResponse:
        logger.error("Unhandled scheduling error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred. Please check your input and try again.",
            },
        )
