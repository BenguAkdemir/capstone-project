"""SQLAlchemy ORM models — English table/column names aligned with API DTOs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"

    employee_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    department: Mapped[str] = mapped_column(String(64), nullable=False)
    min_days: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    max_days: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    availability: Mapped[list[EmployeeAvailability]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    preferences: Mapped[list[EmployeePreference]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class EmployeeAvailability(Base):
    __tablename__ = "employee_availability"
    __table_args__ = (UniqueConstraint("employee_id", "day", name="uq_avail_emp_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False
    )
    day: Mapped[str] = mapped_column(String(16), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    employee: Mapped[Employee] = relationship(back_populates="availability")


class EmployeePreference(Base):
    __tablename__ = "employee_preferences"
    __table_args__ = (UniqueConstraint("employee_id", "day", name="uq_pref_emp_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False
    )
    day: Mapped[str] = mapped_column(String(16), nullable=False)
    preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    avoid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    employee: Mapped[Employee] = relationship(back_populates="preferences")


class OfficeCapacity(Base):
    __tablename__ = "office_capacity"

    day: Mapped[str] = mapped_column(String(16), primary_key=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class CollaborationRule(Base):
    __tablename__ = "collaboration_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    department: Mapped[str] = mapped_column(String(64), nullable=False)
    day: Mapped[str] = mapped_column(String(16), nullable=False)
    min_required: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PlanningWeights(Base):
    """Singleton row (id=1) for optimizer penalty weights."""

    __tablename__ = "planning_weights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    w_miss: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    w_idle: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    w_pref: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class SystemMetadata(Base):
    __tablename__ = "system_metadata"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(512), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
