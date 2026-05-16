"""FastAPI route definitions."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_optimization_service
from backend.application.dtos import SchedulingRequestDTO, SchedulingResponseDTO
from backend.application.optimization_service import OptimizationService

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


@router.get("/health", summary="Health check")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "backend"}
