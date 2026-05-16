"""Persist and load employee planning data from PostgreSQL."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from backend.application.dtos import (
    AvailabilityDTO,
    CapacityDTO,
    CollaborationDTO,
    EmployeeDTO,
    PreferenceDTO,
    SchedulingRequestDTO,
    WeightsDTO,
)
from backend.domain.enums import Weekday
from backend.infrastructure.db.models import (
    CollaborationRule,
    Employee,
    EmployeeAvailability,
    EmployeePreference,
    OfficeCapacity,
    PlanningWeights,
    SystemMetadata,
)

ALL_DAYS: tuple[Weekday, ...] = tuple(Weekday)


class EmployeeService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_employees(self) -> list[EmployeeDTO]:
        rows = (
            self._session.query(Employee)
            .filter(Employee.active.is_(True))
            .order_by(Employee.employee_id)
            .all()
        )
        return [
            EmployeeDTO(
                employee_id=e.employee_id,
                name=e.name,
                department=e.department,
                min_days=e.min_days,
                max_days=e.max_days,
            )
            for e in rows
        ]

    def build_planning_request(self) -> SchedulingRequestDTO:
        employees = self.list_employees()
        if not employees:
            raise ValueError("No employees in database. Run seed or add employees first.")

        eids = [e.employee_id for e in employees]
        availability = self._load_availability(eids)
        preferences = self._load_preferences(eids)
        capacity = self._load_capacity()
        collaboration = self._load_collaboration()
        weights = self._load_weights()
        return SchedulingRequestDTO(
            employees=employees,
            availability=availability,
            preferences=preferences,
            capacity=capacity,
            collaboration=collaboration,
            weights=weights,
        )

    def sync_from_request(self, request: SchedulingRequestDTO) -> dict[str, int]:
        """Upsert UI/API payload into DB, matched by employee_id."""
        now = datetime.utcnow()
        incoming_ids = {e.employee_id for e in request.employees}

        for dto in request.employees:
            row = self._session.get(Employee, dto.employee_id)
            if row is None:
                row = Employee(
                    employee_id=dto.employee_id,
                    created_at=now,
                )
                self._session.add(row)
            row.name = dto.name
            row.department = dto.department
            row.min_days = dto.min_days
            row.max_days = dto.max_days
            row.active = True
            row.updated_at = now

        if incoming_ids:
            inactive = (
                self._session.query(Employee)
                .filter(Employee.employee_id.notin_(incoming_ids))
                .all()
            )
            for row in inactive:
                row.active = False
                row.updated_at = now

        for dto in request.employees:
            self._session.query(EmployeeAvailability).filter(
                EmployeeAvailability.employee_id == dto.employee_id
            ).delete()
            for day in ALL_DAYS:
                avail = next(
                    (a for a in request.availability if a.employee_id == dto.employee_id and a.day == day),
                    None,
                )
                available = bool(avail.available) if avail else True
                self._session.add(
                    EmployeeAvailability(
                        employee_id=dto.employee_id,
                        day=day.value,
                        available=available,
                        updated_at=now,
                    )
                )

            self._session.query(EmployeePreference).filter(
                EmployeePreference.employee_id == dto.employee_id
            ).delete()
            for pref in request.preferences:
                if pref.employee_id != dto.employee_id:
                    continue
                if pref.preferred or pref.avoid:
                    self._session.add(
                        EmployeePreference(
                            employee_id=dto.employee_id,
                            day=pref.day.value,
                            preferred=bool(pref.preferred),
                            avoid=bool(pref.avoid),
                            updated_at=now,
                        )
                    )

        self._session.query(OfficeCapacity).delete()
        for cap in request.capacity:
            self._session.add(
                OfficeCapacity(day=cap.day.value, capacity=cap.capacity, updated_at=now)
            )

        self._session.query(CollaborationRule).delete()
        for collab in request.collaboration:
            self._session.add(
                CollaborationRule(
                    department=collab.department,
                    day=collab.day.value,
                    min_required=collab.min_required,
                    updated_at=now,
                )
            )

        weights = self._session.get(PlanningWeights, 1)
        if weights is None:
            weights = PlanningWeights(id=1)
            self._session.add(weights)
        weights.w_miss = request.weights.w_miss
        weights.w_idle = request.weights.w_idle
        weights.w_pref = request.weights.w_pref
        weights.updated_at = now

        self._session.commit()
        return {
            "employees_upserted": len(request.employees),
            "availability_rows": len(request.availability),
            "preference_rows": len(request.preferences),
        }

    def run_weekly_refresh(self) -> dict[str, str]:
        """Normalize data each week: ensure 5-day availability rows, touch timestamps."""
        now = datetime.utcnow()
        employees = self._session.query(Employee).filter(Employee.active.is_(True)).all()
        refreshed = 0

        for emp in employees:
            existing_days = {
                a.day for a in self._session.query(EmployeeAvailability).filter_by(employee_id=emp.employee_id)
            }
            for day in ALL_DAYS:
                key = day.value
                if key not in existing_days:
                    self._session.add(
                        EmployeeAvailability(
                            employee_id=emp.employee_id,
                            day=key,
                            available=True,
                            updated_at=now,
                        )
                    )
                    refreshed += 1
            emp.updated_at = now

        meta = self._session.get(SystemMetadata, "last_weekly_refresh")
        if meta is None:
            meta = SystemMetadata(key="last_weekly_refresh", value=now.isoformat(), updated_at=now)
            self._session.add(meta)
        else:
            meta.value = now.isoformat()
            meta.updated_at = now

        self._session.commit()
        return {
            "refreshed_at": now.isoformat(),
            "availability_rows_added": str(refreshed),
            "active_employees": str(len(employees)),
        }

    def _load_availability(self, employee_ids: list[str]) -> list[AvailabilityDTO]:
        rows = (
            self._session.query(EmployeeAvailability)
            .filter(EmployeeAvailability.employee_id.in_(employee_ids))
            .all()
        )
        return [
            AvailabilityDTO(
                employee_id=r.employee_id,
                day=Weekday(r.day),
                available=int(r.available),
            )
            for r in rows
        ]

    def _load_preferences(self, employee_ids: list[str]) -> list[PreferenceDTO]:
        rows = (
            self._session.query(EmployeePreference)
            .filter(EmployeePreference.employee_id.in_(employee_ids))
            .all()
        )
        return [
            PreferenceDTO(
                employee_id=r.employee_id,
                day=Weekday(r.day),
                preferred=int(r.preferred),
                avoid=int(r.avoid),
            )
            for r in rows
        ]

    def _load_capacity(self) -> list[CapacityDTO]:
        rows = self._session.query(OfficeCapacity).all()
        if not rows:
            return [CapacityDTO(day=Weekday.MONDAY, capacity=4)]
        return [CapacityDTO(day=Weekday(r.day), capacity=r.capacity) for r in rows]

    def _load_collaboration(self) -> list[CollaborationDTO]:
        rows = self._session.query(CollaborationRule).all()
        return [
            CollaborationDTO(
                department=r.department,
                day=Weekday(r.day),
                min_required=r.min_required,
            )
            for r in rows
        ]

    def _load_weights(self) -> WeightsDTO:
        row = self._session.get(PlanningWeights, 1)
        if row is None:
            return WeightsDTO()
        return WeightsDTO(w_miss=row.w_miss, w_idle=row.w_idle, w_pref=row.w_pref)
