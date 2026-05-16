"""DTO ↔ Domain mapping — application layer."""

from __future__ import annotations

from backend.application.dtos import (
    CollaborationGapDTO,
    DaySummaryDTO,
    EmployeeMetricsDTO,
    EmployeeScheduleDTO,
    ScheduleWarningDTO,
    SchedulingRequestDTO,
    SchedulingResponseDTO,
    TeamAttendanceDTO,
)
from backend.domain.models import (
    Availability,
    CollaborationRequirement,
    DayCapacity,
    Employee,
    OptimizationWeights,
    Preference,
    SchedulingInput,
    SchedulingResult,
)


def request_to_domain(request: SchedulingRequestDTO) -> SchedulingInput:
    return SchedulingInput(
        employees=tuple(
            Employee(
                employee_id=e.employee_id,
                name=e.name,
                department=e.department,
                min_days=e.min_days,
                max_days=e.max_days,
            )
            for e in request.employees
        ),
        availability=tuple(
            Availability(
                employee_id=a.employee_id,
                day=a.day,
                available=bool(a.available),
            )
            for a in request.availability
        ),
        preferences=tuple(
            Preference(
                employee_id=p.employee_id,
                day=p.day,
                preferred=bool(p.preferred),
                avoid=bool(p.avoid),
            )
            for p in request.preferences
        ),
        capacity=tuple(
            DayCapacity(day=c.day, capacity=c.capacity) for c in request.capacity
        ),
        collaboration=tuple(
            CollaborationRequirement(
                department=c.department,
                day=c.day,
                min_required=c.min_required,
            )
            for c in request.collaboration
        ),
        weights=OptimizationWeights(
            w_miss=request.weights.w_miss,
            w_idle=request.weights.w_idle,
            w_pref=request.weights.w_pref,
        ),
    )


def result_to_response(result: SchedulingResult) -> SchedulingResponseDTO:
    return SchedulingResponseDTO(
        status=result.status,
        objective_value=result.objective_value,
        schedules=[
            EmployeeScheduleDTO(
                employee_id=s.employee_id,
                department=s.department,
                assigned_days=dict(s.assigned_days),
                total_assigned=s.total_assigned,
                missing_days=s.missing_days,
            )
            for s in result.schedules
        ],
        day_summaries=[
            DaySummaryDTO(
                day=ds.day,
                used_capacity=ds.used_capacity,
                idle_capacity=ds.idle_capacity,
            )
            for ds in result.day_summaries
        ],
        employee_metrics=[
            EmployeeMetricsDTO(
                employee_id=em.employee_id,
                preference_satisfaction=em.preference_satisfaction,
            )
            for em in result.employee_metrics
        ],
        team_attendance=[
            TeamAttendanceDTO(
                department=ta.department,
                day=ta.day,
                count=ta.count,
            )
            for ta in result.team_attendance
        ],
        total_missing=result.total_missing,
        total_preference_violations=result.total_preference_violations,
        total_avoid_violations=result.total_avoid_violations,
        collaboration_gaps=[
            CollaborationGapDTO(
                department=g.department,
                day=g.day,
                required=g.required,
                actual=g.actual,
                shortfall=g.shortfall,
            )
            for g in result.collaboration_gaps
        ],
        warnings=[
            ScheduleWarningDTO(code=w.code, message=w.message)
            for w in result.warnings
        ],
        solve_time_seconds=result.solve_time_seconds,
        infeasibility_explanation=result.infeasibility_explanation,
    )
