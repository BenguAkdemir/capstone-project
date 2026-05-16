"""
Business-rule validation that goes beyond field-level Pydantic checks.

Catches referential integrity violations, duplicate entries, and
logical inconsistencies that only emerge when cross-referencing
multiple input collections.
"""

from __future__ import annotations

from collections import Counter
from enum import Enum

from .dtos import SchedulingRequestDTO


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class ValidationIssue:
    """A single validation finding with severity."""

    __slots__ = ("field", "message", "severity")

    def __init__(
        self,
        field: str,
        message: str,
        severity: Severity = Severity.ERROR,
    ) -> None:
        self.field = field
        self.message = message
        self.severity = severity

    def __repr__(self) -> str:
        return (
            f"ValidationIssue({self.severity.value}: "
            f"field={self.field!r}, message={self.message!r})"
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity.value,
        }


class ValidationResult:
    """Aggregated validation outcome."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues

    @property
    def is_valid(self) -> bool:
        """True when there are zero ERROR-level issues (warnings are acceptable)."""
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    def to_dicts(self) -> list[dict[str, str]]:
        return [i.to_dict() for i in self.issues]


class InputValidator:
    """
    Cross-collection business-rule validation for ``SchedulingRequestDTO``.

    Field-level constraints (types, ranges) are already enforced by Pydantic.
    This class checks referential integrity, duplicates, and feasibility.
    """

    def validate(self, request: SchedulingRequestDTO) -> ValidationResult:
        issues: list[ValidationIssue] = []
        employee_ids = {e.employee_id for e in request.employees}
        departments = {e.department for e in request.employees}

        self._check_duplicate_employees(request, issues)
        self._check_availability_refs(request, employee_ids, issues)
        self._check_duplicate_availability(request, issues)
        self._check_preference_refs(request, employee_ids, issues)
        self._check_duplicate_preferences(request, issues)
        self._check_duplicate_capacity(request, issues)
        self._check_collaboration_refs(request, departments, issues)
        self._check_collaboration_feasibility(request, issues)
        self._check_collaboration_day_coverage(request, issues)

        return ValidationResult(issues)

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_duplicate_employees(
        request: SchedulingRequestDTO,
        issues: list[ValidationIssue],
    ) -> None:
        seen: set[str] = set()
        for emp in request.employees:
            if emp.employee_id in seen:
                issues.append(ValidationIssue(
                    "employees",
                    f"Duplicate employee_id: '{emp.employee_id}'",
                ))
            seen.add(emp.employee_id)

    @staticmethod
    def _check_availability_refs(
        request: SchedulingRequestDTO,
        employee_ids: set[str],
        issues: list[ValidationIssue],
    ) -> None:
        for avail in request.availability:
            if avail.employee_id not in employee_ids:
                issues.append(ValidationIssue(
                    "availability",
                    f"Unknown employee_id: '{avail.employee_id}'",
                ))

    @staticmethod
    def _check_duplicate_availability(
        request: SchedulingRequestDTO,
        issues: list[ValidationIssue],
    ) -> None:
        counts = Counter((a.employee_id, a.day) for a in request.availability)
        for (eid, day), count in counts.items():
            if count > 1:
                issues.append(ValidationIssue(
                    "availability",
                    f"Duplicate entry for employee '{eid}' on {day.value} ({count} entries)",
                ))

    @staticmethod
    def _check_preference_refs(
        request: SchedulingRequestDTO,
        employee_ids: set[str],
        issues: list[ValidationIssue],
    ) -> None:
        for pref in request.preferences:
            if pref.employee_id not in employee_ids:
                issues.append(ValidationIssue(
                    "preferences",
                    f"Unknown employee_id: '{pref.employee_id}'",
                ))

    @staticmethod
    def _check_duplicate_preferences(
        request: SchedulingRequestDTO,
        issues: list[ValidationIssue],
    ) -> None:
        counts = Counter((p.employee_id, p.day) for p in request.preferences)
        for (eid, day), count in counts.items():
            if count > 1:
                issues.append(ValidationIssue(
                    "preferences",
                    f"Duplicate entry for employee '{eid}' on {day.value} ({count} entries)",
                ))

    @staticmethod
    def _check_duplicate_capacity(
        request: SchedulingRequestDTO,
        issues: list[ValidationIssue],
    ) -> None:
        day_counts = Counter(c.day for c in request.capacity)
        for day, count in day_counts.items():
            if count > 1:
                issues.append(ValidationIssue(
                    "capacity",
                    f"Duplicate capacity entry for '{day.value}' ({count} entries)",
                ))

    @staticmethod
    def _check_collaboration_refs(
        request: SchedulingRequestDTO,
        departments: set[str],
        issues: list[ValidationIssue],
    ) -> None:
        for collab in request.collaboration:
            if collab.department not in departments:
                issues.append(ValidationIssue(
                    "collaboration",
                    f"Unknown department: '{collab.department}'",
                ))

    @staticmethod
    def _check_collaboration_feasibility(
        request: SchedulingRequestDTO,
        issues: list[ValidationIssue],
    ) -> None:
        dept_sizes: dict[str, int] = Counter(
            e.department for e in request.employees
        )
        for collab in request.collaboration:
            dept_size = dept_sizes.get(collab.department, 0)
            if collab.min_required > dept_size:
                issues.append(ValidationIssue(
                    "collaboration",
                    f"Department '{collab.department}' has {dept_size} employee(s) "
                    f"but requires {collab.min_required} on {collab.day.value}",
                    Severity.WARNING,
                ))

    @staticmethod
    def _check_collaboration_day_coverage(
        request: SchedulingRequestDTO,
        issues: list[ValidationIssue],
    ) -> None:
        """Warn when a collaboration requirement targets a day with no capacity defined."""
        capacity_days = {c.day for c in request.capacity}
        for collab in request.collaboration:
            if collab.day not in capacity_days:
                issues.append(ValidationIssue(
                    "collaboration",
                    f"Collaboration for '{collab.department}' on {collab.day.value} "
                    f"references a day with no capacity defined",
                    Severity.WARNING,
                ))
