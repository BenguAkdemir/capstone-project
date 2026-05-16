"""
Data Transfer Objects for the API boundary.

Pydantic models handle serialization, deserialization, and field-level
validation. Cross-collection business rules live in ``validators.py``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.domain.enums import SolverStatus, Weekday


# ---------------------------------------------------------------------------
# Request DTOs
# ---------------------------------------------------------------------------


class EmployeeDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    employee_id: str = Field(
        ..., min_length=1, max_length=64,
        description="Unique identifier for the employee.",
        examples=["E001"],
    )
    name: str = Field(
        ..., min_length=1, max_length=128,
        description="Display name.",
        examples=["Alice"],
    )
    department: str = Field(
        ..., min_length=1, max_length=64,
        description="Department the employee belongs to.",
        examples=["Engineering"],
    )
    min_days: int = Field(
        ..., ge=0, le=5,
        description="Minimum required onsite days per week.",
        examples=[2],
    )
    max_days: int = Field(
        ..., ge=0, le=5,
        description="Maximum allowed onsite days per week.",
        examples=[4],
    )

    @model_validator(mode="after")
    def _min_le_max(self) -> EmployeeDTO:
        if self.min_days > self.max_days:
            raise ValueError(
                f"min_days ({self.min_days}) must not exceed max_days ({self.max_days})"
            )
        return self


class AvailabilityDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    employee_id: str = Field(..., min_length=1, max_length=64)
    day: Weekday
    available: int = Field(
        ..., ge=0, le=1,
        description="1 if the employee can come onsite this day, 0 otherwise.",
    )


class PreferenceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    employee_id: str = Field(..., min_length=1, max_length=64)
    day: Weekday
    preferred: int = Field(
        default=0, ge=0, le=1,
        description="1 if the employee prefers to be onsite this day (preferred_onsite).",
    )
    avoid: int = Field(
        default=0, ge=0, le=1,
        description="1 if the employee prefers to avoid onsite this day (avoid_onsite).",
    )

    @model_validator(mode="after")
    def _pref_not_both(self) -> PreferenceDTO:
        if self.preferred and self.avoid:
            raise ValueError(
                f"employee {self.employee_id} on {self.day.value}: "
                "cannot set both preferred and avoid"
            )
        return self


class CapacityDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    day: Weekday
    capacity: int = Field(
        ..., gt=0,
        description="Maximum number of employees allowed onsite.",
    )


class CollaborationDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    department: str = Field(..., min_length=1, max_length=64)
    day: Weekday
    min_required: int = Field(
        ..., ge=0,
        description="Minimum employees from this department that must be onsite.",
    )


class WeightsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    w_miss: float = Field(
        default=10.0, gt=0,
        description="Penalty weight for each unmet minimum office day.",
    )
    w_idle: float = Field(
        default=1.0, gt=0,
        description="Penalty weight for each unused capacity slot.",
    )
    w_pref: float = Field(
        default=2.0, gt=0,
        description="Penalty weight for each preference violation.",
    )


class SchedulingRequestDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    employees: list[EmployeeDTO] = Field(..., min_length=1)
    availability: list[AvailabilityDTO] = Field(default_factory=list)
    preferences: list[PreferenceDTO] = Field(default_factory=list)
    capacity: list[CapacityDTO] = Field(..., min_length=1)
    collaboration: list[CollaborationDTO] = Field(default_factory=list)
    weights: WeightsDTO = Field(default_factory=WeightsDTO)


# ---------------------------------------------------------------------------
# Response DTOs
# ---------------------------------------------------------------------------


class EmployeeScheduleDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    employee_id: str
    department: str
    assigned_days: dict[Weekday, bool]
    total_assigned: int = Field(..., ge=0)
    missing_days: float = Field(..., ge=0)


class DaySummaryDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    day: Weekday
    used_capacity: int = Field(..., ge=0)
    idle_capacity: float = Field(..., ge=0)


class EmployeeMetricsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    employee_id: str
    preference_satisfaction: float = Field(
        ..., ge=0.0, le=1.0,
        description="Fraction of preferred days that were assigned (0.0–1.0).",
    )


class TeamAttendanceDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    department: str
    day: Weekday
    count: int = Field(..., ge=0)


class CollaborationGapDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    department: str
    day: Weekday
    required: int = Field(..., ge=0)
    actual: int = Field(..., ge=0)
    shortfall: int = Field(..., ge=0)


class ScheduleWarningDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str


class SchedulingResponseDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: SolverStatus
    objective_value: float | None
    schedules: list[EmployeeScheduleDTO]
    day_summaries: list[DaySummaryDTO]
    employee_metrics: list[EmployeeMetricsDTO]
    team_attendance: list[TeamAttendanceDTO]
    total_missing: float = Field(..., ge=0)
    total_preference_violations: int = Field(..., ge=0)
    total_avoid_violations: int = Field(default=0, ge=0)
    collaboration_gaps: list[CollaborationGapDTO] = Field(default_factory=list)
    warnings: list[ScheduleWarningDTO] = Field(default_factory=list)
    solve_time_seconds: float = Field(
        ..., ge=0,
        description="Wall-clock solver time in seconds.",
    )
    infeasibility_explanation: str | None = None


class ExportPayloadDTO(BaseModel):
    """Combined request + response for CSV export."""

    request: SchedulingRequestDTO
    response: SchedulingResponseDTO
