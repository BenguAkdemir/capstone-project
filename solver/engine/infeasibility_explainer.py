"""
Translate Gurobi IIS constraint names into manager-friendly explanations.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from solver.domain.models import SolveRequest

DAY_LABELS: dict[str, str] = {
    "monday": "Monday",
    "tuesday": "Tuesday",
    "wednesday": "Wednesday",
    "thursday": "Thursday",
    "friday": "Friday",
}


def _day_label(day_value: str) -> str:
    return DAY_LABELS.get(day_value.lower(), day_value)


def explain_constraint(name: str, request: SolveRequest | None = None) -> str:
    """Map a single Gurobi constraint name to a human-readable rule description."""
    employee_names = (
        {e.employee_id: e.name for e in request.employees}
        if request is not None
        else {}
    )

    if name.startswith("avail_"):
        rest = name[len("avail_"):]
        for day in DAY_LABELS:
            suffix = f"_{day}"
            if rest.endswith(suffix):
                eid = rest[: -len(suffix)]
                name_label = employee_names.get(eid, eid)
                return (
                    f"Availability rule: {name_label} cannot be assigned onsite on "
                    f"{_day_label(day)}."
                )
        return f"Availability rule violation: {name}"

    if name.startswith("cap_"):
        day = name[len("cap_"):]
        cap = None
        if request is not None:
            for c in request.capacity:
                if c.day.value == day:
                    cap = c.capacity
                    break
        cap_text = f" (capacity: {cap})" if cap is not None else ""
        return (
            f"Office capacity rule: {_day_label(day)} exceeds the maximum "
            f"assignable headcount{cap_text}."
        )

    if name.startswith("max_days_"):
        eid = name[len("max_days_"):]
        name_label = employee_names.get(eid, eid)
        max_days = None
        if request is not None:
            for e in request.employees:
                if e.employee_id == eid:
                    max_days = e.max_days
                    break
        limit = f" (max {max_days} days/week)" if max_days is not None else ""
        return (
            f"Maximum office days rule: {name_label}'s weekly limit{limit} "
            "conflicts with other constraints."
        )

    if name.startswith("collab_"):
        rest = name[len("collab_"):]
        for day in DAY_LABELS:
            suffix = f"_{day}"
            if rest.endswith(suffix):
                dept = rest[: -len(suffix)]
                required = None
                if request is not None:
                    for c in request.collaboration:
                        if c.department == dept and c.day.value == day:
                            required = c.min_required
                            break
                req_text = f" (at least {required} required)" if required is not None else ""
                return (
                    f"Collaboration rule: department '{dept}' must have "
                    f"{req_text} onsite on {_day_label(day)}, but availability "
                    "or capacity cannot satisfy this requirement."
                )
        return f"Collaboration rule violation: {name}"

    if name.startswith("min_days_"):
        eid = name[len("min_days_"):]
        name_label = employee_names.get(eid, eid)
        return (
            f"Minimum office days rule: {name_label}'s required minimum "
            "conflicts with other hard constraints."
        )

    if name.startswith("idle_def_"):
        day = name[len("idle_def_"):]
        return (
            f"Capacity balance on {_day_label(day)}: assignments are "
            "inconsistent with office capacity."
        )

    return f"Conflicting constraint: {name}"


def explain_infeasibility(
    constraint_names: list[str],
    request: SolveRequest | None = None,
) -> tuple[str, list[str]]:
    """
    Build a summary explanation and per-rule messages from IIS constraint names.

    Returns:
        (summary, rule_messages)
    """
    if not constraint_names:
        return (
            "The submitted rules conflict; no mathematically feasible schedule exists.",
            [],
        )

    priority_prefixes = ("avail_", "cap_", "collab_", "max_days_", "min_days_")
    ranked = sorted(
        constraint_names,
        key=lambda n: (
            0 if n.startswith(priority_prefixes) else 1,
            n,
        ),
    )

    seen: set[str] = set()
    rule_messages: list[str] = []
    for name in ranked:
        if name.startswith("idle_def_"):
            continue
        msg = explain_constraint(name, request)
        if msg not in seen:
            seen.add(msg)
            rule_messages.append(msg)

    if not rule_messages:
        rule_messages = [
            explain_constraint(name, request) for name in ranked[:5]
        ]

    limited = rule_messages[:5]
    if len(rule_messages) == 1:
        summary = (
            "No feasible schedule exists because this rule conflicts with "
            "other constraints: " + limited[0]
        )
    else:
        summary = (
            "No feasible schedule exists; the following rules conflict "
            f"({len(rule_messages)} rule(s) identified)."
        )

    return summary, limited


def parse_iis_names(raw_message: str) -> list[str]:
    """Extract constraint names from a legacy explanation string."""
    if "IIS" not in raw_message and "constraints:" not in raw_message:
        return []
    tail = raw_message.split("constraints:", 1)[-1]
    names = re.split(r",\s*|\.\.\.", tail)
    return [n.strip() for n in names if n.strip() and not n.strip().startswith("and ")]
