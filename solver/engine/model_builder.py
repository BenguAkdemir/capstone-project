"""
Gurobi model construction — the mathematical core.

Builds the full MIP formulation:
    Sets:        E, D, T, E_t
    Parameters:  avail, pref, cap, min_days, max_days, collab
    Variables:   x[e,d] binary, miss[e] continuous, idle[d] continuous
    Constraints: availability, capacity, min/max days, collaboration, idle
    Objective:   minimize weighted sum of miss + idle + preference violations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import gurobipy as gp
from gurobipy import GRB

from solver.domain.models import SolveRequest, Weekday


@dataclass
class ModelComponents:
    """Container for the built Gurobi model and its decision variables."""

    model: Any  # gp.Model
    x: dict[tuple[str, Weekday], Any] = field(default_factory=dict)
    miss: dict[str, Any] = field(default_factory=dict)
    idle: dict[Weekday, Any] = field(default_factory=dict)
    employees: set[str] = field(default_factory=set)
    days: set[Weekday] = field(default_factory=set)
    departments: set[str] = field(default_factory=set)
    dept_employees: dict[str, set[str]] = field(default_factory=dict)
    avail: dict[tuple[str, Weekday], bool] = field(default_factory=dict)
    pref: dict[tuple[str, Weekday], bool] = field(default_factory=dict)
    avoid: dict[tuple[str, Weekday], bool] = field(default_factory=dict)


def build_model(request: SolveRequest) -> ModelComponents:
    """Construct the Gurobi MIP from a SolveRequest."""

    model = gp.Model("hybrid_scheduling")

    # ------------------------------------------------------------------
    # Sets
    # ------------------------------------------------------------------
    employees: set[str] = {e.employee_id for e in request.employees}
    days: set[Weekday] = {c.day for c in request.capacity}
    departments: set[str] = {e.department for e in request.employees}
    dept_employees: dict[str, set[str]] = {t: set() for t in departments}
    for e in request.employees:
        dept_employees[e.department].add(e.employee_id)

    # ------------------------------------------------------------------
    # Parameters (sparse dict lookups)
    # ------------------------------------------------------------------
    avail: dict[tuple[str, Weekday], bool] = {}
    for a in request.availability:
        avail[(a.employee_id, a.day)] = a.available

    pref: dict[tuple[str, Weekday], bool] = {}
    avoid: dict[tuple[str, Weekday], bool] = {}
    for p in request.preferences:
        if p.preferred:
            pref[(p.employee_id, p.day)] = True
        if p.avoid:
            avoid[(p.employee_id, p.day)] = True

    cap: dict[Weekday, int] = {c.day: c.capacity for c in request.capacity}
    min_days_param: dict[str, int] = {e.employee_id: e.min_days for e in request.employees}
    max_days_param: dict[str, int] = {e.employee_id: e.max_days for e in request.employees}

    collab: dict[tuple[str, Weekday], int] = {}
    for c in request.collaboration:
        collab[(c.department, c.day)] = c.min_required

    weights = request.weights

    # ------------------------------------------------------------------
    # Decision Variables
    # ------------------------------------------------------------------
    x: dict[tuple[str, Weekday], Any] = {}
    for e in employees:
        for d in days:
            x[(e, d)] = model.addVar(vtype=GRB.BINARY, name=f"x_{e}_{d.value}")

    miss: dict[str, Any] = {}
    for e in employees:
        miss[e] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"miss_{e}")

    idle: dict[Weekday, Any] = {}
    for d in days:
        idle[d] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"idle_{d.value}")

    model.update()

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    # 1. Availability: x[e,d] <= avail[e,d]
    for e in employees:
        for d in days:
            if not avail.get((e, d), False):
                model.addConstr(x[(e, d)] == 0, name=f"avail_{e}_{d.value}")

    # 2. Capacity: Σ_e x[e,d] <= cap[d]
    for d in days:
        model.addConstr(
            gp.quicksum(x[(e, d)] for e in employees) <= cap[d],
            name=f"cap_{d.value}",
        )

    # 3. Minimum days: Σ_d x[e,d] + miss[e] >= min_days[e]
    for e in employees:
        model.addConstr(
            gp.quicksum(x[(e, d)] for d in days) + miss[e] >= min_days_param[e],
            name=f"min_days_{e}",
        )

    # 4. Maximum days: Σ_d x[e,d] <= max_days[e]
    for e in employees:
        model.addConstr(
            gp.quicksum(x[(e, d)] for d in days) <= max_days_param[e],
            name=f"max_days_{e}",
        )

    # 5. Collaboration: Σ_{e ∈ E_t} x[e,d] >= collab[t,d]
    for (dept, d), min_req in collab.items():
        if dept in dept_employees and d in days:
            members = dept_employees[dept]
            model.addConstr(
                gp.quicksum(x[(e, d)] for e in members if (e, d) in x) >= min_req,
                name=f"collab_{dept}_{d.value}",
            )

    # 6. Idle definition: idle[d] = cap[d] - Σ_e x[e,d]
    for d in days:
        model.addConstr(
            idle[d] == cap[d] - gp.quicksum(x[(e, d)] for e in employees),
            name=f"idle_def_{d.value}",
        )

    # ------------------------------------------------------------------
    # Objective Function
    # ------------------------------------------------------------------
    # min Z = w_miss * Σ miss_e + w_idle * Σ idle_d + w_pref * (preference violations)
    obj_miss = weights.w_miss * gp.quicksum(miss[e] for e in employees)
    obj_idle = weights.w_idle * gp.quicksum(idle[d] for d in days)

    pref_terms = []
    # Unmet preferred onsite days: (1 - x[e,d]) when preferred and available
    for (e, d), is_pref in pref.items():
        if is_pref and avail.get((e, d), False) and (e, d) in x:
            pref_terms.append(1.0 - x[(e, d)])
    # Avoid-day violations: x[e,d] when employee prefers to avoid onsite
    for (e, d), is_avoid in avoid.items():
        if is_avoid and (e, d) in x:
            pref_terms.append(x[(e, d)])
    obj_pref = weights.w_pref * gp.quicksum(pref_terms) if pref_terms else 0

    model.setObjective(obj_miss + obj_idle + obj_pref, GRB.MINIMIZE)

    return ModelComponents(
        model=model,
        x=x,
        miss=miss,
        idle=idle,
        employees=employees,
        days=days,
        departments=departments,
        dept_employees=dept_employees,
        avail=avail,
        pref=pref,
        avoid=avoid,
    )
