"""
Port interfaces (Hexagonal Architecture).

These define the contracts that infrastructure adapters must implement.
The domain and application layers depend only on these abstractions —
never on concrete implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import SchedulingInput, SchedulingResult


class SolverInterface(ABC):
    """Contract for any optimization solver (Gurobi, OR-Tools, mock, etc.).

    Implementors must translate ``SchedulingInput`` into the solver's
    native representation, run the optimization, and translate the
    result back into ``SchedulingResult``.

    Raises:
        InfeasibleError:    Model is provably infeasible.
        SolverTimeoutError: Time limit reached (may still carry a partial result).
        SolverError:        Any other solver-internal failure.
    """

    @abstractmethod
    def solve(self, problem: SchedulingInput) -> SchedulingResult: ...


class DataLoaderInterface(ABC):
    """Contract for loading scheduling data from any source (files, DB, API, etc.).

    Raises:
        FileNotFoundError: Source is unreachable.
        ValueError:        Data is structurally malformed.
    """

    @abstractmethod
    def load(self, source: str) -> SchedulingInput: ...
