"""
Application service — orchestrates a single scheduling run.

Flow: validate → map DTO → solve → map result
"""

from __future__ import annotations

import logging

from backend.application.dtos import SchedulingRequestDTO, SchedulingResponseDTO
from backend.application.mappers import request_to_domain, result_to_response
from backend.application.validators import InputValidator
from backend.domain.exceptions import InvalidInputError
from backend.domain.interfaces import SolverInterface

logger = logging.getLogger(__name__)


class OptimizationService:
    """Single entry point for the API layer to request a schedule."""

    def __init__(self, solver: SolverInterface) -> None:
        self._solver = solver
        self._validator = InputValidator()

    def schedule(self, request: SchedulingRequestDTO) -> SchedulingResponseDTO:
        """Validate, solve, and return the scheduling result."""

        # 1. Business-rule validation
        validation_result = self._validator.validate(request)
        if not validation_result.is_valid:
            raise InvalidInputError(
                issues=validation_result.to_dicts(),
                message=f"Input has {len(validation_result.errors)} validation error(s)",
            )
        if validation_result.warnings:
            logger.warning(
                "Input validation warnings: %s",
                [w.message for w in validation_result.warnings],
            )

        # 2. Map DTO → domain
        domain_input = request_to_domain(request)

        # 3. Call solver
        logger.info("Calling solver with %d employees", len(domain_input.employees))
        domain_result = self._solver.solve(domain_input)

        # 4. Map result → response DTO
        return result_to_response(domain_result)
