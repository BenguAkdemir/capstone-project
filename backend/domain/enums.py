from enum import Enum


class Weekday(str, Enum):
    """Standard working days (str mixin gives free JSON serialization)."""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"


ALL_WEEKDAYS: tuple[Weekday, ...] = tuple(Weekday)


class SolverStatus(str, Enum):
    """Outcome of a solver invocation."""

    OPTIMAL = "optimal"
    INFEASIBLE = "infeasible"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    ERROR = "error"
