"""
File-based data loader — infrastructure layer.

Implements ``DataLoaderInterface`` by reading JSON files from a directory
on disk and assembling them into a ``SchedulingInput``.

Expected directory layout:
    <source>/
        employees.json
        availability.json
        preferences.json       (optional — defaults to empty)
        capacity.json
        collaboration.json     (optional — defaults to empty)
        weights.json           (optional — uses default weights)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.domain.enums import Weekday
from backend.domain.interfaces import DataLoaderInterface
from backend.domain.models import (
    Availability,
    CollaborationRequirement,
    DayCapacity,
    Employee,
    OptimizationWeights,
    Preference,
    SchedulingInput,
)

logger = logging.getLogger(__name__)

_REQUIRED_FILES = ("employees.json", "capacity.json", "availability.json")
_OPTIONAL_FILES = ("preferences.json", "collaboration.json", "weights.json")


class FileLoader(DataLoaderInterface):
    """Loads scheduling data from a directory of JSON files."""

    def load(self, source: str) -> SchedulingInput:
        """Read JSON files from *source* directory and return a SchedulingInput.

        Raises:
            FileNotFoundError: Directory or a required file is missing.
            ValueError: JSON is malformed or data doesn't match expected schema.
        """
        directory = Path(source)
        if not directory.is_dir():
            raise FileNotFoundError(f"Data directory not found: {directory}")

        self._check_required_files(directory)

        employees = self._load_employees(directory / "employees.json")
        availability = self._load_availability(directory / "availability.json")
        preferences = self._load_preferences(directory / "preferences.json")
        capacity = self._load_capacity(directory / "capacity.json")
        collaboration = self._load_collaboration(directory / "collaboration.json")
        weights = self._load_weights(directory / "weights.json")

        logger.info(
            "Loaded scheduling data: %d employees, %d availability records, "
            "%d preferences, %d capacity days, %d collaboration requirements",
            len(employees),
            len(availability),
            len(preferences),
            len(capacity),
            len(collaboration),
        )

        return SchedulingInput(
            employees=tuple(employees),
            availability=tuple(availability),
            preferences=tuple(preferences),
            capacity=tuple(capacity),
            collaboration=tuple(collaboration),
            weights=weights,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_required_files(self, directory: Path) -> None:
        missing = [f for f in _REQUIRED_FILES if not (directory / f).is_file()]
        if missing:
            raise FileNotFoundError(
                f"Missing required file(s) in {directory}: {', '.join(missing)}"
            )

    def _read_json(self, path: Path) -> Any:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise FileNotFoundError(f"Cannot read {path}: {exc}") from exc
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {path.name}: {exc}") from exc

    def _read_optional_json(self, path: Path) -> list[dict[str, Any]] | None:
        if not path.is_file():
            return None
        return self._read_json(path)

    def _parse_weekday(self, value: str, context: str) -> Weekday:
        """Convert a raw string to a Weekday enum, case-insensitive."""
        try:
            return Weekday(value.lower().strip())
        except (ValueError, AttributeError) as exc:
            valid = ", ".join(d.value for d in Weekday)
            raise ValueError(
                f"Invalid day '{value}' in {context}. Valid days: {valid}"
            ) from exc

    # ------------------------------------------------------------------
    # Entity loaders
    # ------------------------------------------------------------------

    def _load_employees(self, path: Path) -> list[Employee]:
        raw = self._read_json(path)
        if not isinstance(raw, list):
            raise ValueError(f"{path.name} must contain a JSON array")

        employees: list[Employee] = []
        for i, item in enumerate(raw):
            try:
                employees.append(
                    Employee(
                        employee_id=str(item["employee_id"]),
                        name=str(item["name"]),
                        department=str(item["department"]),
                        min_days=int(item["min_days"]),
                        max_days=int(item["max_days"]),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"{path.name}[{i}]: {exc}"
                ) from exc
        return employees

    def _load_availability(self, path: Path) -> list[Availability]:
        raw = self._read_json(path)
        if not isinstance(raw, list):
            raise ValueError(f"{path.name} must contain a JSON array")

        records: list[Availability] = []
        for i, item in enumerate(raw):
            try:
                records.append(
                    Availability(
                        employee_id=str(item["employee_id"]),
                        day=self._parse_weekday(item["day"], f"{path.name}[{i}]"),
                        available=bool(int(item["available"])),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"{path.name}[{i}]: {exc}"
                ) from exc
        return records

    def _load_preferences(self, path: Path) -> list[Preference]:
        raw = self._read_optional_json(path)
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise ValueError(f"{path.name} must contain a JSON array")

        records: list[Preference] = []
        for i, item in enumerate(raw):
            try:
                records.append(
                    Preference(
                        employee_id=str(item["employee_id"]),
                        day=self._parse_weekday(item["day"], f"{path.name}[{i}]"),
                        preferred=bool(int(item["preferred"])),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"{path.name}[{i}]: {exc}"
                ) from exc
        return records

    def _load_capacity(self, path: Path) -> list[DayCapacity]:
        raw = self._read_json(path)
        if not isinstance(raw, list):
            raise ValueError(f"{path.name} must contain a JSON array")

        records: list[DayCapacity] = []
        for i, item in enumerate(raw):
            try:
                records.append(
                    DayCapacity(
                        day=self._parse_weekday(item["day"], f"{path.name}[{i}]"),
                        capacity=int(item["capacity"]),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"{path.name}[{i}]: {exc}"
                ) from exc
        return records

    def _load_collaboration(self, path: Path) -> list[CollaborationRequirement]:
        raw = self._read_optional_json(path)
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise ValueError(f"{path.name} must contain a JSON array")

        records: list[CollaborationRequirement] = []
        for i, item in enumerate(raw):
            try:
                records.append(
                    CollaborationRequirement(
                        department=str(item["department"]),
                        day=self._parse_weekday(item["day"], f"{path.name}[{i}]"),
                        min_required=int(item["min_required"]),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"{path.name}[{i}]: {exc}"
                ) from exc
        return records

    def _load_weights(self, path: Path) -> OptimizationWeights:
        raw = self._read_optional_json(path)
        if raw is None:
            return OptimizationWeights()
        if not isinstance(raw, dict):
            raise ValueError(f"{path.name} must contain a JSON object")
        try:
            return OptimizationWeights(
                w_miss=float(raw.get("w_miss", 10.0)),
                w_idle=float(raw.get("w_idle", 1.0)),
                w_pref=float(raw.get("w_pref", 2.0)),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{path.name}: {exc}") from exc
