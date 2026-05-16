"""
Solution extraction and metrics computation.

Extracts variable values from the solved Gurobi model and packages them
into the SolveResponse format including schedules, summaries, and metrics.
"""

from __future__ import annotations

from solver.domain.models import (
    CollaborationGapOutput,
    DaySummaryOutput,
    EmployeeMetricsOutput,
    EmployeeScheduleOutput,
    ScheduleWarningOutput,
    SolveRequest,
    SolveResponse,
    SolverStatus,
    TeamAttendanceOutput,
    Weekday,
)
from solver.engine.model_builder import ModelComponents
from solver.engine.solver import SolveOutcome


def extract_results(
    request: SolveRequest,
    components: ModelComponents,
    outcome: SolveOutcome,
) -> SolveResponse:
    """Build a full SolveResponse from the solved model."""

    if outcome.status in (SolverStatus.INFEASIBLE, SolverStatus.ERROR, SolverStatus.TIMEOUT):
        warnings = []
        if outcome.infeasibility_explanation:
            warnings.append(
                ScheduleWarningOutput(
                    code="infeasible",
                    message=outcome.infeasibility_explanation,
                )
            )
        return SolveResponse(
            status=outcome.status,
            objective_value=outcome.objective_value,
            solve_time_seconds=outcome.solve_time_seconds,
            infeasibility_explanation=outcome.infeasibility_explanation,
            warnings=warnings,
        )

    emp_lookup = {e.employee_id: e for e in request.employees}
    sorted_days = sorted(components.days, key=lambda d: list(Weekday).index(d))

    collab_req = {
        (c.department, c.day): c.min_required for c in request.collaboration
    }

    schedules: list[EmployeeScheduleOutput] = []
    total_missing = 0.0
    total_pref_violations = 0
    total_avoid_violations = 0

    for e_id in sorted(components.employees):
        emp = emp_lookup[e_id]
        assigned: dict[Weekday, bool] = {}
        total_assigned = 0

        for d in sorted_days:
            val = components.x[(e_id, d)].X
            is_assigned = val > 0.5
            assigned[d] = is_assigned
            if is_assigned:
                total_assigned += 1

        miss_val = components.miss[e_id].X
        total_missing += miss_val

        schedules.append(
            EmployeeScheduleOutput(
                employee_id=e_id,
                department=emp.department,
                assigned_days=assigned,
                total_assigned=total_assigned,
                missing_days=miss_val,
            )
        )

    day_summaries: list[DaySummaryOutput] = []
    for d in sorted_days:
        idle_val = components.idle[d].X
        used = sum(
            1 for e in components.employees if components.x[(e, d)].X > 0.5
        )
        day_summaries.append(
            DaySummaryOutput(day=d, used_capacity=used, idle_capacity=idle_val)
        )

    employee_metrics: list[EmployeeMetricsOutput] = []
    for e_id in sorted(components.employees):
        pref_days = [
            d for d in sorted_days if components.pref.get((e_id, d), False)
        ]
        if not pref_days:
            satisfaction = 1.0
        else:
            satisfied = sum(
                1 for d in pref_days if components.x[(e_id, d)].X > 0.5
            )
            satisfaction = satisfied / len(pref_days)

        for d in sorted_days:
            assigned = components.x[(e_id, d)].X > 0.5
            if components.pref.get((e_id, d), False) and not assigned:
                total_pref_violations += 1
            if components.avoid.get((e_id, d), False) and assigned:
                total_avoid_violations += 1

        employee_metrics.append(
            EmployeeMetricsOutput(
                employee_id=e_id,
                preference_satisfaction=round(satisfaction, 4),
            )
        )

    team_attendance: list[TeamAttendanceOutput] = []
    collaboration_gaps: list[CollaborationGapOutput] = []
    for dept in sorted(components.departments):
        for d in sorted_days:
            count = sum(
                1
                for e in components.dept_employees[dept]
                if components.x[(e, d)].X > 0.5
            )
            team_attendance.append(
                TeamAttendanceOutput(department=dept, day=d, count=count)
            )
            required = collab_req.get((dept, d))
            if required is not None and count < required:
                collaboration_gaps.append(
                    CollaborationGapOutput(
                        department=dept,
                        day=d,
                        required=required,
                        actual=count,
                        shortfall=required - count,
                    )
                )

    warnings: list[ScheduleWarningOutput] = []
    if total_missing > 0:
        warnings.append(
            ScheduleWarningOutput(
                code="unmet_minimum_days",
                message=f"Total unmet minimum office days: {total_missing:.2f}",
            )
        )
    if total_pref_violations > 0:
        warnings.append(
            ScheduleWarningOutput(
                code="preference_violations",
                message=f"Unsatisfied preferred onsite days: {total_pref_violations}",
            )
        )
    if total_avoid_violations > 0:
        warnings.append(
            ScheduleWarningOutput(
                code="avoid_violations",
                message=f"Assignments on avoid-preference days: {total_avoid_violations}",
            )
        )
    for gap in collaboration_gaps:
        warnings.append(
            ScheduleWarningOutput(
                code="collaboration_shortfall",
                message=(
                    f"{gap.department} on {gap.day.value}: "
                    f"need {gap.required}, got {gap.actual}"
                ),
            )
        )

    return SolveResponse(
        status=outcome.status,
        objective_value=outcome.objective_value,
        schedules=schedules,
        day_summaries=day_summaries,
        employee_metrics=employee_metrics,
        team_attendance=team_attendance,
        total_missing=round(total_missing, 4),
        total_preference_violations=total_pref_violations,
        total_avoid_violations=total_avoid_violations,
        collaboration_gaps=collaboration_gaps,
        warnings=warnings,
        solve_time_seconds=outcome.solve_time_seconds,
        infeasibility_explanation=outcome.infeasibility_explanation,
    )
