"""Export scheduling results to structured CSV files (FR9)."""

from __future__ import annotations

import csv
import io
import zipfile
from typing import Any

from backend.application.dtos import SchedulingRequestDTO, SchedulingResponseDTO
from backend.domain.enums import Weekday

WEEKDAYS: tuple[Weekday, ...] = (
    Weekday.MONDAY,
    Weekday.TUESDAY,
    Weekday.WEDNESDAY,
    Weekday.THURSDAY,
    Weekday.FRIDAY,
)


def _csv_string(rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def export_results_zip(
    request: SchedulingRequestDTO,
    response: SchedulingResponseDTO,
) -> bytes:
    """Build a ZIP archive with schedule, summary, and warning CSV files."""
    emp_names = {e.employee_id: e.name for e in request.employees}

    schedule_rows: list[dict[str, Any]] = []
    for s in response.schedules:
        row: dict[str, Any] = {
            "employee_id": s.employee_id,
            "employee_name": emp_names.get(s.employee_id, ""),
            "department": s.department,
        }
        for day in WEEKDAYS:
            assigned = s.assigned_days.get(day, False)
            row[day.value] = "onsite" if assigned else "remote"
        row["total_assigned"] = s.total_assigned
        schedule_rows.append(row)

    summary_rows: list[dict[str, Any]] = []
    for s in response.schedules:
        metrics = next(
            (m for m in response.employee_metrics if m.employee_id == s.employee_id),
            None,
        )
        summary_rows.append(
            {
                "employee_id": s.employee_id,
                "employee_name": emp_names.get(s.employee_id, ""),
                "department": s.department,
                "assigned_onsite_days": s.total_assigned,
                "unmet_minimum_days": s.missing_days,
                "preference_satisfaction": metrics.preference_satisfaction if metrics else "",
            }
        )

    capacity_rows = [
        {
            "day": ds.day.value,
            "used_capacity": ds.used_capacity,
            "unused_capacity": ds.idle_capacity,
        }
        for ds in response.day_summaries
    ]

    dept_rows = [
        {
            "department": ta.department,
            "day": ta.day.value,
            "onsite_count": ta.count,
        }
        for ta in response.team_attendance
    ]

    warning_rows = [
        {"code": w.code, "message": w.message} for w in response.warnings
    ]
    if response.infeasibility_explanation:
        warning_rows.insert(
            0,
            {"code": "infeasible", "message": response.infeasibility_explanation},
        )
    for g in response.collaboration_gaps:
        warning_rows.append(
            {
                "code": "collaboration_shortfall",
                "message": (
                    f"{g.department}/{g.day.value}: required {g.required}, "
                    f"actual {g.actual}"
                ),
            }
        )

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "weekly_schedule.csv",
            _csv_string(
                schedule_rows,
                ["employee_id", "employee_name", "department"]
                + [d.value for d in WEEKDAYS]
                + ["total_assigned"],
            ),
        )
        zf.writestr(
            "summary.csv",
            _csv_string(
                summary_rows,
                [
                    "employee_id",
                    "employee_name",
                    "department",
                    "assigned_onsite_days",
                    "unmet_minimum_days",
                    "preference_satisfaction",
                ],
            ),
        )
        zf.writestr(
            "capacity_summary.csv",
            _csv_string(
                capacity_rows,
                ["day", "used_capacity", "unused_capacity"],
            ),
        )
        zf.writestr(
            "department_attendance.csv",
            _csv_string(
                dept_rows,
                ["department", "day", "onsite_count"],
            ),
        )
        zf.writestr(
            "warnings.csv",
            _csv_string(warning_rows, ["code", "message"]) if warning_rows else "code,message\n",
        )

    return zip_buf.getvalue()
