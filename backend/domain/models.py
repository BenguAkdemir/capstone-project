"""
Core domain entities for the Hybrid Work Scheduling system.

Pure Python dataclasses — no framework dependencies.
All input entities are frozen (immutable) and use ``slots`` for
memory efficiency. Invariants are enforced eagerly in __post_init__.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import SolverStatus, Weekday


# ---------------------------------------------------------------------------
# Input Entities
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Employee:
    employee_id: str
    name: str
    department: str
    min_days: int
    max_days: int

    def __post_init__(self) -> None:
        if not self.employee_id or not self.employee_id.strip():
            raise ValueError("employee_id must not be blank")
        if not self.name or not self.name.strip():
            raise ValueError("name must not be blank")
        if not self.department or not self.department.strip():
            raise ValueError("department must not be blank")
        if self.min_days < 0:
            raise ValueError(f"min_days must be >= 0, got {self.min_days}")
        if self.max_days > 5:
            raise ValueError(f"max_days must be <= 5, got {self.max_days}")
        if self.max_days < self.min_days:
            raise ValueError(
                f"max_days ({self.max_days}) must be >= min_days ({self.min_days})"
            )


@dataclass(frozen=True, slots=True)
class Availability:
    employee_id: str
    day: Weekday
    available: bool

    def __post_init__(self) -> None:
        if not self.employee_id or not self.employee_id.strip():
            raise ValueError("employee_id must not be blank")


@dataclass(frozen=True, slots=True)
class Preference:
    employee_id: str
    day: Weekday
    preferred: bool

    def __post_init__(self) -> None:
        if not self.employee_id or not self.employee_id.strip():
            raise ValueError("employee_id must not be blank")


@dataclass(frozen=True, slots=True)
class DayCapacity:
    day: Weekday
    capacity: int

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError(f"capacity must be > 0, got {self.capacity}")


@dataclass(frozen=True, slots=True)
class CollaborationRequirement:
    department: str
    day: Weekday
    min_required: int

    def __post_init__(self) -> None:
        if not self.department or not self.department.strip():
            raise ValueError("department must not be blank")
        if self.min_required < 0:
            raise ValueError(f"min_required must be >= 0, got {self.min_required}")


@dataclass(frozen=True, slots=True)
class OptimizationWeights:
    """Configurable objective-function weights.

    Defaults match the specification:
        w_miss = 10  (unmet minimum office days — highest priority)
        w_idle = 1   (unused capacity — lowest priority)
        w_pref = 2   (preference violations — medium priority)
    """

    w_miss: float = 10.0
    w_idle: float = 1.0
    w_pref: float = 2.0

    def __post_init__(self) -> None:
        for attr in ("w_miss", "w_idle", "w_pref"):
            val = getattr(self, attr)
            if not isinstance(val, (int, float)) or val <= 0:
                raise ValueError(f"{attr} must be a positive number, got {val!r}")


@dataclass(frozen=True, slots=True)
class SchedulingInput:
    """Complete, validated problem instance passed to the solver."""

    employees: tuple[Employee, ...]
    availability: tuple[Availability, ...]
    preferences: tuple[Preference, ...]
    capacity: tuple[DayCapacity, ...]
    collaboration: tuple[CollaborationRequirement, ...]
    weights: OptimizationWeights = field(default_factory=OptimizationWeights)

    def __post_init__(self) -> None:
        if not self.employees:
            raise ValueError("employees must not be empty")
        if not self.capacity:
            raise ValueError("capacity must not be empty")


# ---------------------------------------------------------------------------
# Output Entities
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EmployeeSchedule:
    employee_id: str
    department: str
    assigned_days: dict[Weekday, bool]
    total_assigned: int
    missing_days: float


@dataclass(frozen=True, slots=True)
class DaySummary:
    day: Weekday
    used_capacity: int
    idle_capacity: float


@dataclass(frozen=True, slots=True)
class EmployeeMetrics:
    employee_id: str
    preference_satisfaction: float  # 0.0 – 1.0


@dataclass(frozen=True, slots=True)
class TeamAttendance:
    department: str
    day: Weekday
    count: int


@dataclass(frozen=True, slots=True)
class SchedulingResult:
    """Complete solver output including schedule, metrics, and diagnostics."""

    status: SolverStatus
    objective_value: float | None
    schedules: tuple[EmployeeSchedule, ...]
    day_summaries: tuple[DaySummary, ...]
    employee_metrics: tuple[EmployeeMetrics, ...]
    team_attendance: tuple[TeamAttendance, ...]
    total_missing: float
    total_preference_violations: int
    solve_time_seconds: float
    infeasibility_explanation: str | None = None
