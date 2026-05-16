"""Seed 10 mock employees and default planning data (English departments/names)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from backend.infrastructure.db.models import (
    CollaborationRule,
    Employee,
    EmployeeAvailability,
    EmployeePreference,
    OfficeCapacity,
    PlanningWeights,
    SystemMetadata,
)

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday")

MOCK_EMPLOYEES: list[dict] = [
    {"employee_id": "E001", "name": "Alice Morgan", "department": "Engineering", "min_days": 2, "max_days": 4},
    {"employee_id": "E002", "name": "Bob Chen", "department": "Engineering", "min_days": 3, "max_days": 5},
    {"employee_id": "E003", "name": "Charlie Reed", "department": "Engineering", "min_days": 2, "max_days": 3},
    {"employee_id": "E004", "name": "Diana Brooks", "department": "Design", "min_days": 2, "max_days": 4},
    {"employee_id": "E005", "name": "Emre Patel", "department": "Design", "min_days": 1, "max_days": 3},
    {"employee_id": "E006", "name": "Frank Liu", "department": "IT", "min_days": 2, "max_days": 4},
    {"employee_id": "E007", "name": "Grace Kim", "department": "IT", "min_days": 2, "max_days": 5},
    {"employee_id": "E008", "name": "Henry Walsh", "department": "HR", "min_days": 2, "max_days": 3},
    {"employee_id": "E009", "name": "Ivy Santos", "department": "HR", "min_days": 1, "max_days": 2},
    {"employee_id": "E010", "name": "Jack Turner", "department": "Product", "min_days": 2, "max_days": 4},
]

# employee_id -> day -> available
MOCK_AVAILABILITY: dict[str, dict[str, bool]] = {
    "E001": {"monday": True, "tuesday": True, "wednesday": True, "thursday": False, "friday": True},
    "E002": {d: True for d in WEEKDAYS},
    "E003": {"monday": True, "tuesday": False, "wednesday": True, "thursday": True, "friday": False},
    "E004": {"monday": True, "tuesday": True, "wednesday": False, "thursday": True, "friday": True},
    "E005": {"monday": False, "tuesday": True, "wednesday": True, "thursday": True, "friday": True},
    "E006": {d: True for d in WEEKDAYS},
    "E007": {"monday": True, "tuesday": True, "wednesday": False, "thursday": True, "friday": True},
    "E008": {"monday": True, "tuesday": False, "wednesday": True, "thursday": False, "friday": True},
    "E009": {d: True for d in WEEKDAYS},
    "E010": {"monday": True, "tuesday": True, "wednesday": True, "thursday": True, "friday": False},
}

MOCK_PREFERENCES: list[dict] = [
    {"employee_id": "E001", "day": "monday", "preferred": True, "avoid": False},
    {"employee_id": "E001", "day": "friday", "preferred": True, "avoid": False},
    {"employee_id": "E002", "day": "wednesday", "preferred": True, "avoid": False},
    {"employee_id": "E004", "day": "tuesday", "preferred": True, "avoid": False},
    {"employee_id": "E006", "day": "thursday", "preferred": False, "avoid": True},
    {"employee_id": "E008", "day": "friday", "preferred": True, "avoid": False},
]

MOCK_CAPACITY: dict[str, int] = {
    "monday": 5,
    "tuesday": 5,
    "wednesday": 4,
    "thursday": 4,
    "friday": 5,
}

MOCK_COLLABORATION: list[dict] = [
    {"department": "Engineering", "day": "wednesday", "min_required": 2},
    {"department": "Design", "day": "tuesday", "min_required": 2},
    {"department": "IT", "day": "monday", "min_required": 2},
]


def seed_database_if_empty(session: Session) -> bool:
    """Insert mock data when the employees table is empty. Returns True if seeded."""
    if session.query(Employee).count() > 0:
        return False

    now = datetime.utcnow()
    for row in MOCK_EMPLOYEES:
        session.add(Employee(**row, active=True, created_at=now, updated_at=now))

    for eid, days in MOCK_AVAILABILITY.items():
        for day, available in days.items():
            session.add(
                EmployeeAvailability(
                    employee_id=eid, day=day, available=available, updated_at=now
                )
            )

    for row in MOCK_PREFERENCES:
        session.add(EmployeePreference(**row, updated_at=now))

    for day, capacity in MOCK_CAPACITY.items():
        session.add(OfficeCapacity(day=day, capacity=capacity, updated_at=now))

    for row in MOCK_COLLABORATION:
        session.add(CollaborationRule(**row, updated_at=now))

    session.add(PlanningWeights(id=1, w_miss=10.0, w_idle=1.0, w_pref=2.0, updated_at=now))
    session.add(
        SystemMetadata(
            key="last_weekly_refresh",
            value=now.isoformat(),
            updated_at=now,
        )
    )
    session.commit()
    return True
