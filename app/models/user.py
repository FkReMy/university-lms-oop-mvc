"""
app/models/user.py
Full User authentication system with compound foreign keys (user_id, role)
Supports:
- One user → exactly one role (enforced at DB level)
- Multi-valued departments/specializations via association tables
- Full audit trail
- Soft delete ready
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, Table, CheckConstraint,
    UniqueConstraint, func, ForeignKeyConstraint  # <--- FIXED: Added ForeignKeyConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base_model import BaseModel
from app.database.base import str_pk, created_at_col, updated_at_col, is_active_col

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.specialization import Specialization

# =============================================================================
# ASSOCIATION TABLES – Multi-valued attributes (many-to-many)
# =============================================================================

professor_departments = Table(
    "professor_departments",
    BaseModel.metadata,
    Column("user_id", String, ForeignKey("professors.user_id", ondelete="CASCADE"), primary_key=True),
    Column("dept_id", String, ForeignKey("departments.dept_id"), primary_key=True),
    UniqueConstraint("user_id", "dept_id", name="uq_prof_dept")
)

professor_specializations = Table(
    "professor_specializations",
    BaseModel.metadata,
    Column("user_id", String, ForeignKey("professors.user_id", ondelete="CASCADE"), primary_key=True),
    Column("spec_id", String, ForeignKey("specializations.spec_id"), primary_key=True),
    UniqueConstraint("user_id", "spec_id", name="uq_prof_spec")
)

associate_departments = Table(
    "associate_departments",
    BaseModel.metadata,
    Column("user_id", String, ForeignKey("associate_teachers.user_id", ondelete="CASCADE"), primary_key=True),
    Column("dept_id", String, ForeignKey("departments.dept_id"), primary_key=True)
)

associate_specializations = Table(
    "associate_specializations",
    BaseModel.metadata,
    Column("user_id", String, ForeignKey("associate_teachers.user_id", ondelete="CASCADE"), primary_key=True),
    Column("spec_id", String, ForeignKey("specializations.spec_id"), primary_key=True)
)

# =============================================================================
# CORE USER & ROLE SYSTEM
# =============================================================================

class User(BaseModel):
    __tablename__ = "users"

    user_id: Mapped[str_pk]
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]
    is_active: Mapped[is_active_col]

    # Relationship to role (one-to-one)
    role_assignment: Mapped["UserRole"] = relationship(
        "UserRole", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role_assignment.role if self.role_assignment else 'No Role'})>"


class UserRole(BaseModel):
    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True
    )
    role: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        nullable=False
    )
    assigned_at: Mapped[created_at_col]

    # Enforce valid roles
    __table_args__ = (
        CheckConstraint(
            role.in_(["Admin", "Professor", "AssociateTeacher", "Student"]),
            name="ck_valid_role"
        ),
        UniqueConstraint("user_id", name="uq_one_role_per_user"),  # Critical: one role only
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="role_assignment")


# =============================================================================
# ROLE-SPECIFIC PROFILE TABLES (Table-per-Type Inheritance Pattern)
# =============================================================================

class Admin(BaseModel):
    __tablename__ = "admins"

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("user_roles.user_id", ondelete="CASCADE"),
        primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="Admin")

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "role"],
            ["user_roles.user_id", "user_roles.role"],
            ondelete="CASCADE"
        ),
        CheckConstraint("role = 'Admin'", name="ck_admin_role")
    )


class Student(BaseModel):
    __tablename__ = "students"

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("user_roles.user_id", ondelete="CASCADE"),
        primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), server_default="Student", nullable=False)
    student_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(9), server_default="2025-2026")

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "role"],
            ["user_roles.user_id", "user_roles.role"]
        ),
        CheckConstraint("role = 'Student'", name="ck_student_role")
    )


class Professor(BaseModel):
    __tablename__ = "professors"

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("user_roles.user_id", ondelete="CASCADE"),
        primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), server_default="Professor", nullable=False)
    office: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    hire_date: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Many-to-many relationships
    departments: Mapped[List["Department"]] = relationship(
        "Department",
        secondary=professor_departments,
        back_populates="professors"
    )
    specializations: Mapped[List["Specialization"]] = relationship(
        "Specialization",
        secondary=professor_specializations,
        back_populates="professors"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "role"],
            ["user_roles.user_id", "user_roles.role"]
        ),
        CheckConstraint("role = 'Professor'", name="ck_professor_role")
    )


class AssociateTeacher(BaseModel):
    __tablename__ = "associate_teachers"

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("user_roles.user_id", ondelete="CASCADE"),
        primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), server_default="AssociateTeacher", nullable=False)
    max_weekly_hours: Mapped[int] = mapped_column(default=20, nullable=False)

    # Many-to-many
    departments: Mapped[List["Department"]] = relationship(
        "Department",
        secondary=associate_departments,
        back_populates="associate_teachers"
    )
    specializations: Mapped[List["Specialization"]] = relationship(
        "Specialization",
        secondary=associate_specializations,
        back_populates="associate_teachers"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "role"],
            ["user_roles.user_id", "user_roles.role"]
        ),
        CheckConstraint("role = 'AssociateTeacher'", name="ck_associate_role")
    )
