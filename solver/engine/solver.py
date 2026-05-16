"""
Solver execution and status handling.

Runs model.optimize(), interprets Gurobi status codes, and measures wall-clock time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from gurobipy import GRB

from solver.config import settings
from solver.domain.models import SolverStatus
from solver.engine.model_builder import ModelComponents


@dataclass(frozen=True)
class SolveOutcome:
    """Raw outcome from solver execution (before result extraction)."""

    status: SolverStatus
    objective_value: float | None
    solve_time_seconds: float
    infeasibility_explanation: str | None = None


def run_optimization(components: ModelComponents) -> SolveOutcome:
    """Configure and run the Gurobi optimizer, returning a typed outcome."""

    model = components.model

    # Solver parameters
    model.Params.TimeLimit = settings.time_limit_seconds
    model.Params.MIPGap = settings.mip_gap
    model.Params.Threads = settings.threads
    model.Params.LogToConsole = 1 if settings.log_output else 0

    start = time.perf_counter()
    model.optimize()
    elapsed = time.perf_counter() - start

    grb_status = model.Status

    if grb_status == GRB.OPTIMAL:
        return SolveOutcome(
            status=SolverStatus.OPTIMAL,
            objective_value=model.ObjVal,
            solve_time_seconds=elapsed,
        )

    if grb_status == GRB.INFEASIBLE:
        explanation = _compute_infeasibility_explanation(model)
        return SolveOutcome(
            status=SolverStatus.INFEASIBLE,
            objective_value=None,
            solve_time_seconds=elapsed,
            infeasibility_explanation=explanation,
        )

    if grb_status == GRB.TIME_LIMIT:
        obj_val = model.ObjVal if model.SolCount > 0 else None
        status = SolverStatus.PARTIAL if model.SolCount > 0 else SolverStatus.TIMEOUT
        return SolveOutcome(
            status=status,
            objective_value=obj_val,
            solve_time_seconds=elapsed,
            infeasibility_explanation=(
                f"Time limit ({settings.time_limit_seconds}s) reached"
                + (f" with {model.SolCount} solution(s) found" if model.SolCount > 0 else "")
            ),
        )

    if grb_status in (GRB.INF_OR_UNBD, GRB.UNBOUNDED):
        return SolveOutcome(
            status=SolverStatus.INFEASIBLE,
            objective_value=None,
            solve_time_seconds=elapsed,
            infeasibility_explanation="Model is infeasible or unbounded",
        )

    return SolveOutcome(
        status=SolverStatus.ERROR,
        objective_value=None,
        solve_time_seconds=elapsed,
        infeasibility_explanation=f"Unexpected Gurobi status code: {grb_status}",
    )


def _compute_infeasibility_explanation(model) -> str:
    """Attempt to compute IIS and return human-readable constraint names."""
    try:
        model.computeIIS()
        iis_constrs = [c.ConstrName for c in model.getConstrs() if c.IISConstr]
        if iis_constrs:
            limited = iis_constrs[:10]
            msg = "Irreducible Infeasible Subsystem (IIS) constraints: " + ", ".join(limited)
            if len(iis_constrs) > 10:
                msg += f" ... and {len(iis_constrs) - 10} more"
            return msg
    except Exception:
        pass
    return "Model is infeasible (IIS computation failed)"
