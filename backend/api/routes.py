"""FastAPI route definitions."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from backend.api.dependencies import get_optimization_service
from backend.application.dtos import (
    AvailabilityDTO,
    CapacityDTO,
    CollaborationDTO,
    EmployeeDTO,
    PreferenceDTO,
    ExportPayloadDTO,
    SchedulingRequestDTO,
    SchedulingResponseDTO,
    WeightsDTO,
)
from backend.application.export_service import export_results_zip
from backend.application.optimization_service import OptimizationService
from backend.infrastructure.file_loader import FileLoader

router = APIRouter()


@router.post(
    "/schedule",
    response_model=SchedulingResponseDTO,
    summary="Generate optimal hybrid work schedule",
    description="Accepts employee data, constraints, and preferences. Returns an optimized weekly schedule.",
)
def create_schedule(
    request: SchedulingRequestDTO,
    service: OptimizationService = Depends(get_optimization_service),
) -> SchedulingResponseDTO:
    return service.schedule(request)


@router.post(
    "/schedule/load",
    response_model=SchedulingRequestDTO,
    summary="Load planning data from structured JSON files (FR8)",
)
def load_from_directory(data_dir: str) -> SchedulingRequestDTO:
    """Load input from a directory containing employees.json, availability.json, etc."""
    try:
        domain_input = FileLoader().load(data_dir)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SchedulingRequestDTO(
        employees=[
            EmployeeDTO(
                employee_id=e.employee_id,
                name=e.name,
                department=e.department,
                min_days=e.min_days,
                max_days=e.max_days,
            )
            for e in domain_input.employees
        ],
        availability=[
            AvailabilityDTO(
                employee_id=a.employee_id,
                day=a.day,
                available=int(a.available),
            )
            for a in domain_input.availability
        ],
        preferences=[
            PreferenceDTO(
                employee_id=p.employee_id,
                day=p.day,
                preferred=int(p.preferred),
                avoid=int(p.avoid),
            )
            for p in domain_input.preferences
        ],
        capacity=[
            CapacityDTO(day=c.day, capacity=c.capacity) for c in domain_input.capacity
        ],
        collaboration=[
            CollaborationDTO(
                department=c.department,
                day=c.day,
                min_required=c.min_required,
            )
            for c in domain_input.collaboration
        ],
        weights=WeightsDTO(
            w_miss=domain_input.weights.w_miss,
            w_idle=domain_input.weights.w_idle,
            w_pref=domain_input.weights.w_pref,
        ),
    )


@router.post(
    "/schedule/load-sample",
    response_model=SchedulingRequestDTO,
    summary="Load bundled sample input files",
)
def load_sample() -> SchedulingRequestDTO:
    sample_dir = Path(__file__).resolve().parents[2] / "data" / "sample"
    return load_from_directory(str(sample_dir))


@router.post(
    "/schedule/export",
    summary="Export schedule and summary reports as CSV ZIP (FR9)",
)
def export_schedule(payload: ExportPayloadDTO) -> Response:
    content = export_results_zip(payload.request, payload.response)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=schedule_export.zip"},
    )


@router.get("/health", summary="Health check")
def health() -> dict[str, str]:
    from sqlalchemy import text

    from backend.infrastructure.db.session import SessionLocal

    db_status = "unknown"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "unavailable"
    return {"status": "healthy", "service": "backend", "database": db_status}
