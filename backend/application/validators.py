"""
Business-rule validation that goes beyond field-level Pydantic checks.

Catches referential integrity violations, duplicate entries, and
mathematical infeasibility that only emerge when cross-referencing
multiple input collections.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from enum import Enum

from .dtos import SchedulingRequestDTO

DAY_LABELS: dict[str, str] = {
    "monday": "Monday",
    "tuesday": "Tuesday",
    "wednesday": "Wednesday",
    "thursday": "Thursday",
    "friday": "Friday",
}


def _day_label(day_value: str) -> str:
    return DAY_LABELS.get(day_value, day_value)


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class ValidationIssue:
    """A single validation finding with severity."""

    __slots__ = ("field", "message", "severity", "code")

    def __init__(
        self,
        field: str,
        message: str,
        severity: Severity = Severity.ERROR,
        *,
        code: str = "validation_error",
    ) -> None:
        self.field = field
        self.message = message
        self.severity = severity
        self.code = code

    def __repr__(self) -> str:
        return (
            f"ValidationIssue({self.severity.value}: "
            f"field={self.field!r}, code={self.code!r}, message={self.message!r})"
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity.value,
            "code": self.code,
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

    def summary_message(self) -> str:
        """Single-line summary for API responses."""
        if not self.errors:
            return "Input validation passed."
        if len(self.errors) == 1:
            return self.errors[0].message
        return (
            f"Cannot create a schedule: {len(self.errors)} rule violation(s) detected. "
            f"First issue: {self.errors[0].message}"
        )


class InputValidator:
    """
    Cross-collection business-rule validation for ``SchedulingRequestDTO``.

    Field-level constraints (types, ranges) are already enforced by Pydantic.
    This class checks referential integrity, duplicates, and mathematical
    feasibility before the solver is invoked.
    """

    def validate(self, request: SchedulingRequestDTO) -> ValidationResult:
        issues: list[ValidationIssue] = []
        employee_ids = {e.employee_id for e in request.employees}
        employee_names = {e.employee_id: e.name for e in request.employees}
        departments = {e.department for e in request.employees}
        capacity_days = {c.day for c in request.capacity}
        capacity_by_day = {c.day: c.capacity for c in request.capacity}

        self._check_duplicate_employees(request, issues)
        self._check_availability_refs(request, employee_ids, issues)
        self._check_duplicate_availability(request, issues)
        self._check_availability_coverage(request, employee_ids, employee_names, capacity_days, issues)
        self._check_min_max_vs_availability(request, employee_names, capacity_days, issues)
        self._check_preference_refs(request, employee_ids, issues)
        self._check_duplicate_preferences(request, issues)
        self._check_duplicate_capacity(request, issues)
        self._check_collaboration_refs(request, departments, issues)
        self._check_duplicate_collaboration(request, issues)
        self._check_collaboration_feasibility(request, issues)
        self._check_collaboration_vs_capacity(request, capacity_by_day, issues)
        self._check_collaboration_availability(request, issues)
        self._check_collaboration_day_coverage(request, capacity_days, issues)
        self._check_capacity_vs_demand(request, capacity_by_day, issues)

        return ValidationResult(issues)

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    @staticmethod
    def _availability_map(request: SchedulingRequestDTO) -> dict[tuple[str, str], bool]:
        return {
            (a.employee_id, a.day.value): bool(a.available)
            for a in request.availability
        }

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
                    f"Duplicate employee_id: '{emp.employee_id}'. "
                    "Each employee must have a unique identifier.",
                    code="duplicate_employee",
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
                    f"Unknown employee_id in availability: '{avail.employee_id}'. "
                    "Add the employee to the employee list first.",
                    code="unknown_employee_availability",
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
                    f"Conflicting availability entries for employee '{eid}' on "
                    f"{_day_label(day.value)} ({count} entries). "
                    "Each employee-day pair must be defined only once.",
                    code="duplicate_availability",
                ))

    @staticmethod
    def _check_availability_coverage(
        request: SchedulingRequestDTO,
        employee_ids: set[str],
        employee_names: dict[str, str],
        capacity_days: set,
        issues: list[ValidationIssue],
    ) -> None:
        avail_keys = {(a.employee_id, a.day) for a in request.availability}
        for eid in employee_ids:
            name = employee_names.get(eid, eid)
            for day in capacity_days:
                if (eid, day) not in avail_keys:
                    issues.append(ValidationIssue(
                        "availability",
                        f"Missing availability for {name} ({eid}) on {_day_label(day.value)}. "
                        "Availability must be provided for every day with office capacity.",
                        code="missing_availability",
                    ))

    @staticmethod
    def _check_min_max_vs_availability(
        request: SchedulingRequestDTO,
        employee_names: dict[str, str],
        capacity_days: set,
        issues: list[ValidationIssue],
    ) -> None:
        avail = InputValidator._availability_map(request)
        for emp in request.employees:
            available_count = sum(
                1 for day in capacity_days
                if avail.get((emp.employee_id, day.value), False)
            )
            name = employee_names[emp.employee_id]

            if emp.min_days > available_count:
                issues.append(ValidationIssue(
                    "employees",
                    f"{name}: minimum office days ({emp.min_days}) exceeds "
                    f"the number of available days ({available_count}). "
                    "Update availability or lower the minimum day requirement.",
                    code="min_days_exceeds_availability",
                ))

            if emp.max_days > available_count:
                issues.append(ValidationIssue(
                    "employees",
                    f"{name}: maximum office days ({emp.max_days}) exceeds "
                    f"the number of available days ({available_count}). "
                    "Update availability or lower the maximum day limit.",
                    code="max_days_exceeds_availability",
                ))

            if available_count == 0 and emp.max_days > 0:
                issues.append(ValidationIssue(
                    "availability",
                    f"{name} is unavailable on every day; no office assignment is possible.",
                    code="no_available_days",
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
                    f"Unknown employee_id in preferences: '{pref.employee_id}'.",
                    code="unknown_employee_preference",
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
                    f"Conflicting preference entries for employee '{eid}' on "
                    f"{_day_label(day.value)} ({count} entries). "
                    "Each employee-day pair must be defined only once.",
                    code="duplicate_preference",
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
                    f"Conflicting capacity entries for {_day_label(day.value)} "
                    f"({count} entries). Each day must have only one capacity value.",
                    code="duplicate_capacity",
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
                    f"Unknown department in collaboration rule: '{collab.department}'. "
                    "Define the department in the employee list first.",
                    code="unknown_department",
                ))

    @staticmethod
    def _check_duplicate_collaboration(
        request: SchedulingRequestDTO,
        issues: list[ValidationIssue],
    ) -> None:
        counts = Counter((c.department, c.day) for c in request.collaboration)
        for (dept, day), count in counts.items():
            if count > 1:
                issues.append(ValidationIssue(
                    "collaboration",
                    f"Conflicting collaboration rules for department '{dept}' on "
                    f"{_day_label(day.value)} ({count} entries). "
                    "Each department-day pair must be defined only once.",
                    code="duplicate_collaboration",
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
                    f"Department '{collab.department}' has {dept_size} employee(s) but "
                    f"requires at least {collab.min_required} onsite on "
                    f"{_day_label(collab.day.value)}. "
                    "Reduce the requirement or add more employees to the department.",
                    code="collaboration_exceeds_department_size",
                ))

    @staticmethod
    def _check_collaboration_vs_capacity(
        request: SchedulingRequestDTO,
        capacity_by_day: dict,
        issues: list[ValidationIssue],
    ) -> None:
        collab_by_day: dict = defaultdict(int)
        for collab in request.collaboration:
            day_cap = capacity_by_day.get(collab.day)
            if day_cap is not None and collab.min_required > day_cap:
                issues.append(ValidationIssue(
                    "collaboration",
                    f"Department '{collab.department}' requires at least "
                    f"{collab.min_required} employees onsite on {_day_label(collab.day.value)}, "
                    f"but office capacity is only {day_cap}. "
                    "Increase capacity or relax the collaboration rule.",
                    code="collaboration_exceeds_capacity",
                ))
            collab_by_day[collab.day] += collab.min_required

        for day, total_required in collab_by_day.items():
            day_cap = capacity_by_day.get(day)
            if day_cap is not None and total_required > day_cap:
                issues.append(ValidationIssue(
                    "capacity",
                    f"On {_day_label(day.value)}, the sum of department minimum "
                    f"onsite requirements ({total_required}) exceeds office capacity "
                    f"({day_cap}). Rules conflict on this day — relax at least one rule.",
                    code="collaboration_sum_exceeds_capacity",
                ))

    @staticmethod
    def _check_collaboration_availability(
        request: SchedulingRequestDTO,
        issues: list[ValidationIssue],
    ) -> None:
        avail = InputValidator._availability_map(request)
        dept_members: dict[str, list[str]] = defaultdict(list)
        for emp in request.employees:
            dept_members[emp.department].append(emp.employee_id)

        for collab in request.collaboration:
            members = dept_members.get(collab.department, [])
            available_count = sum(
                1 for eid in members
                if avail.get((eid, collab.day.value), False)
            )
            if collab.min_required > available_count:
                issues.append(ValidationIssue(
                    "collaboration",
                    f"Department '{collab.department}' has only {available_count} "
                    f"available employee(s) on {_day_label(collab.day.value)}, "
                    f"but requires at least {collab.min_required}. "
                    "Update availability or relax the collaboration rule.",
                    code="collaboration_exceeds_available_members",
                ))

    @staticmethod
    def _check_collaboration_day_coverage(
        request: SchedulingRequestDTO,
        capacity_days: set,
        issues: list[ValidationIssue],
    ) -> None:
        """Warn when a collaboration requirement targets a day with no capacity defined."""
        for collab in request.collaboration:
            if collab.day not in capacity_days:
                issues.append(ValidationIssue(
                    "collaboration",
                    f"Collaboration rule for department '{collab.department}' on "
                    f"{_day_label(collab.day.value)} references a day with no "
                    "office capacity defined.",
                    Severity.WARNING,
                    code="collaboration_without_capacity",
                ))

    @staticmethod
    def _check_capacity_vs_demand(
        request: SchedulingRequestDTO,
        capacity_by_day: dict,
        issues: list[ValidationIssue],
    ) -> None:
        """Detect when total max onsite demand cannot fit into weekly capacity."""
        total_max_demand = sum(emp.max_days for emp in request.employees)
        total_capacity = sum(capacity_by_day.values())
        if total_max_demand > total_capacity:
            issues.append(ValidationIssue(
                "capacity",
                f"Total maximum office days across all employees ({total_max_demand}) "
                f"exceeds total weekly office capacity ({total_capacity}). "
                "Increase capacity or reduce employee maximum day limits.",
                Severity.WARNING,
                code="total_demand_exceeds_capacity",
            ))
