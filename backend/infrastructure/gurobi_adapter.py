"""
Gurobi solver adapter — infrastructure layer.

Implements SolverInterface by calling the solver service over HTTP.
This is the only place in the backend that knows the solver service exists.
"""

from __future__ import annotations

import logging

import httpx

from backend.config import settings
from backend.domain.enums import SolverStatus, Weekday
from backend.domain.exceptions import (
    InfeasibleError,
    SolverError,
    SolverTimeoutError,
)
from backend.domain.interfaces import SolverInterface
from backend.domain.models import (
    CollaborationGap,
    DaySummary,
    EmployeeMetrics,
    EmployeeSchedule,
    ScheduleWarning,
    SchedulingInput,
    SchedulingResult,
    TeamAttendance,
)

logger = logging.getLogger(__name__)


def _solver_error_from_response(resp: httpx.Response) -> SolverError:
    """Map solver HTTP errors to user-facing SolverError messages."""
    detail = ""
    try:
        body = resp.json()
        detail = str(body.get("detail", body.get("error", "")))
    except ValueError:
        detail = resp.text[:500]

    detail_lower = detail.lower()
    if "hostid mismatch" in detail_lower or "license" in detail_lower:
        return SolverError(
            f"Solver HTTP {resp.status_code}: {detail}",
            user_message=(
                "The Gurobi license is not valid in this environment. Your license "
                "may be bound to a different machine than the solver container. "
                "Run the solver locally on port 8001 and use docker compose for "
                "backend/web services. Details: " + detail
            ),
        )
    if resp.status_code == 503:
        return SolverError(
            f"Solver unavailable: {detail}",
            user_message="The optimization service is unavailable. Is the solver running?",
        )

    return SolverError(
        f"Solver returned HTTP {resp.status_code}: {detail}",
        user_message=detail or "An error occurred in the optimization service.",
    )


class GurobiHttpAdapter(SolverInterface):
    """Calls the standalone solver service via HTTP POST /solve."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        self._base_url = (base_url or settings.solver_url).rstrip("/")
        self._timeout = timeout or settings.solver_timeout_seconds

    def solve(self, problem: SchedulingInput) -> SchedulingResult:
        payload = self._serialize_request(problem)

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(f"{self._base_url}/solve", json=payload)
        except httpx.TimeoutException as exc:
            raise SolverTimeoutError(elapsed_seconds=self._timeout) from exc
        except httpx.ConnectError as exc:
            raise SolverError(
                f"Cannot connect to solver at {self._base_url}: {exc}",
                user_message=(
                    "Cannot connect to the optimization service (port 8001). "
                    "In a separate terminal run: ./scripts/run-solver-local.sh "
                    "— then try again."
                ),
            ) from exc
        except httpx.HTTPError as exc:
            raise SolverError(
                f"HTTP error calling solver: {exc}",
                user_message=f"Communication error with solver: {exc}",
            ) from exc

        if resp.status_code != 200:
            raise _solver_error_from_response(resp)

        data = resp.json()
        return self._deserialize_response(data)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _serialize_request(self, problem: SchedulingInput) -> dict:
        return {
            "employees": [
                {
                    "employee_id": e.employee_id,
                    "name": e.name,
                    "department": e.department,
                    "min_days": e.min_days,
                    "max_days": e.max_days,
                }
                for e in problem.employees
            ],
            "availability": [
                {
                    "employee_id": a.employee_id,
                    "day": a.day.value,
                    "available": a.available,
                }
                for a in problem.availability
            ],
            "preferences": [
                {
                    "employee_id": p.employee_id,
                    "day": p.day.value,
                    "preferred": bool(p.preferred),
                    "avoid": bool(p.avoid),
                }
                for p in problem.preferences
            ],
            "capacity": [
                {"day": c.day.value, "capacity": c.capacity}
                for c in problem.capacity
            ],
            "collaboration": [
                {
                    "department": c.department,
                    "day": c.day.value,
                    "min_required": c.min_required,
                }
                for c in problem.collaboration
            ],
            "weights": {
                "w_miss": problem.weights.w_miss,
                "w_idle": problem.weights.w_idle,
                "w_pref": problem.weights.w_pref,
            },
        }

    def _deserialize_response(self, data: dict) -> SchedulingResult:
        status = SolverStatus(data["status"])

        if status == SolverStatus.INFEASIBLE:
            raise InfeasibleError(
                explanation=data.get(
                    "infeasibility_explanation",
                    "The submitted rules conflict; no feasible schedule exists.",
                ),
                rules=data.get("infeasibility_rules") or [],
            )
        if status == SolverStatus.TIMEOUT:
            raise SolverTimeoutError(
                elapsed_seconds=data.get("solve_time_seconds", 0.0),
                best_objective=data.get("objective_value"),
            )

        schedules = tuple(
            EmployeeSchedule(
                employee_id=s["employee_id"],
                department=s["department"],
                assigned_days={Weekday(k): v for k, v in s["assigned_days"].items()},
                total_assigned=s["total_assigned"],
                missing_days=s["missing_days"],
            )
            for s in data.get("schedules", [])
        )

        day_summaries = tuple(
            DaySummary(
                day=Weekday(ds["day"]),
                used_capacity=ds["used_capacity"],
                idle_capacity=ds["idle_capacity"],
            )
            for ds in data.get("day_summaries", [])
        )

        employee_metrics = tuple(
            EmployeeMetrics(
                employee_id=em["employee_id"],
                preference_satisfaction=em["preference_satisfaction"],
            )
            for em in data.get("employee_metrics", [])
        )

        team_attendance = tuple(
            TeamAttendance(
                department=ta["department"],
                day=Weekday(ta["day"]),
                count=ta["count"],
            )
            for ta in data.get("team_attendance", [])
        )

        collaboration_gaps = tuple(
            CollaborationGap(
                department=g["department"],
                day=Weekday(g["day"]),
                required=g["required"],
                actual=g["actual"],
                shortfall=g["shortfall"],
            )
            for g in data.get("collaboration_gaps", [])
        )

        warnings = tuple(
            ScheduleWarning(code=w["code"], message=w["message"])
            for w in data.get("warnings", [])
        )

        return SchedulingResult(
            status=status,
            objective_value=data.get("objective_value"),
            schedules=schedules,
            day_summaries=day_summaries,
            employee_metrics=employee_metrics,
            team_attendance=team_attendance,
            total_missing=data.get("total_missing", 0.0),
            total_preference_violations=data.get("total_preference_violations", 0),
            total_avoid_violations=data.get("total_avoid_violations", 0),
            collaboration_gaps=collaboration_gaps,
            warnings=warnings,
            solve_time_seconds=data.get("solve_time_seconds", 0.0),
            infeasibility_explanation=data.get("infeasibility_explanation"),
        )
