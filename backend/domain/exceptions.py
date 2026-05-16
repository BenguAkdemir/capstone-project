"""
Domain-specific exception hierarchy.

Every exception the scheduling domain can raise is rooted here,
making it easy for upper layers to catch broad or narrow error
categories without leaking implementation details.
"""

from __future__ import annotations


class SchedulingError(Exception):
    """Root exception for the scheduling domain."""


class InvalidInputError(SchedulingError):
    """Input data failed business-rule validation.

    Attributes:
        issues: Machine-readable list of validation issue dicts
                (each has ``field``, ``message``, ``severity``).
    """

    def __init__(
        self,
        issues: list[dict[str, str]],
        message: str = "Input validation failed",
    ) -> None:
        self.issues = issues
        super().__init__(message)


class SolverError(SchedulingError):
    """The optimization solver encountered an internal error.

    Attributes:
        user_message: Plain-language message safe to show in the UI.
    """

    def __init__(self, message: str, *, user_message: str | None = None) -> None:
        self.user_message = user_message or message
        super().__init__(message)


class InfeasibleError(SchedulingError):
    """The model is provably infeasible (no feasible relaxation found).

    Attributes:
        explanation: Human-readable description of why the model is infeasible.
    """

    def __init__(self, explanation: str) -> None:
        self.explanation = explanation
        super().__init__(explanation)


class SolverTimeoutError(SchedulingError):
    """The solver exceeded its time limit without finding a proven-optimal solution.

    Attributes:
        best_objective: Objective value of the best incumbent (if any).
        elapsed_seconds: Wall-clock time before the timeout fired.
    """

    def __init__(
        self,
        elapsed_seconds: float,
        best_objective: float | None = None,
    ) -> None:
        self.elapsed_seconds = elapsed_seconds
        self.best_objective = best_objective
        super().__init__(
            f"Solver timed out after {elapsed_seconds:.1f}s"
            + (f" (best objective: {best_objective:.4f})" if best_objective is not None else "")
        )
