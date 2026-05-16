"""
Solver-internal Pydantic models — the JSON contract between backend and solver.

Each service owns its own schema. The solver doesn't import backend models.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Weekday(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"


class SolverStatus(str, Enum):
    OPTIMAL = "optimal"
    INFEASIBLE = "infeasible"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class EmployeeInput(BaseModel):
    model_config = ConfigDict(frozen=True)
    employee_id: str
    name: str
    department: str
    min_days: int = Field(ge=0, le=5)
    max_days: int = Field(ge=0, le=5)


class AvailabilityInput(BaseModel):
    model_config = ConfigDict(frozen=True)
    employee_id: str
    day: Weekday
    available: bool


class PreferenceInput(BaseModel):
    model_config = ConfigDict(frozen=True)
    employee_id: str
    day: Weekday
    preferred: bool = False
    avoid: bool = False


class CapacityInput(BaseModel):
    model_config = ConfigDict(frozen=True)
    day: Weekday
    capacity: int = Field(gt=0)


class CollaborationInput(BaseModel):
    model_config = ConfigDict(frozen=True)
    department: str
    day: Weekday
    min_required: int = Field(ge=0)


class WeightsInput(BaseModel):
    model_config = ConfigDict(frozen=True)
    w_miss: float = Field(default=10.0, gt=0)
    w_idle: float = Field(default=1.0, gt=0)
    w_pref: float = Field(default=2.0, gt=0)


class SolveRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    employees: list[EmployeeInput]
    availability: list[AvailabilityInput]
    preferences: list[PreferenceInput] = []
    capacity: list[CapacityInput]
    collaboration: list[CollaborationInput] = []
    weights: WeightsInput = WeightsInput()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class EmployeeScheduleOutput(BaseModel):
    employee_id: str
    department: str
    assigned_days: dict[Weekday, bool]
    total_assigned: int
    missing_days: float


class DaySummaryOutput(BaseModel):
    day: Weekday
    used_capacity: int
    idle_capacity: float


class EmployeeMetricsOutput(BaseModel):
    employee_id: str
    preference_satisfaction: float = Field(ge=0.0, le=1.0)


class TeamAttendanceOutput(BaseModel):
    department: str
    day: Weekday
    count: int


class CollaborationGapOutput(BaseModel):
    department: str
    day: Weekday
    required: int = Field(ge=0)
    actual: int = Field(ge=0)
    shortfall: int = Field(ge=0)


class ScheduleWarningOutput(BaseModel):
    code: str
    message: str


class SolveResponse(BaseModel):
    status: SolverStatus
    objective_value: float | None = None
    schedules: list[EmployeeScheduleOutput] = []
    day_summaries: list[DaySummaryOutput] = []
    employee_metrics: list[EmployeeMetricsOutput] = []
    team_attendance: list[TeamAttendanceOutput] = []
    total_missing: float = 0.0
    total_preference_violations: int = 0
    total_avoid_violations: int = 0
    collaboration_gaps: list[CollaborationGapOutput] = []
    warnings: list[ScheduleWarningOutput] = []
    solve_time_seconds: float = 0.0
    infeasibility_explanation: str | None = None
