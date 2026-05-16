"""Employee and planning persistence API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.application.dtos import EmployeeDTO, SchedulingRequestDTO
from backend.application.employee_service import EmployeeService
from backend.infrastructure.db.session import get_db

router = APIRouter(prefix="/employees", tags=["employees"])


def _service(db: Session = Depends(get_db)) -> EmployeeService:
    return EmployeeService(db)


@router.get("", response_model=list[EmployeeDTO], summary="List active employees")
def list_employees(service: EmployeeService = Depends(_service)) -> list[EmployeeDTO]:
    return service.list_employees()


@router.get(
    "/planning",
    response_model=SchedulingRequestDTO,
    summary="Load full planning input from database",
)
def get_planning(service: EmployeeService = Depends(_service)) -> SchedulingRequestDTO:
    try:
        return service.build_planning_request()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/sync",
    summary="Save UI planning input to database (matched by employee_id)",
)
def sync_planning(
    request: SchedulingRequestDTO,
    service: EmployeeService = Depends(_service),
) -> dict:
    stats = service.sync_from_request(request)
    return {"status": "ok", **stats}


@router.post(
    "/weekly-refresh",
    summary="Trigger weekly background refresh manually",
)
def weekly_refresh(service: EmployeeService = Depends(_service)) -> dict:
    return service.run_weekly_refresh()
