"""
app/models/role.py
Dedicated Role reference table – for future RBAC, permissions, and admin UI

Currently used as a reference/lookup table.
Your core role enforcement still happens via compound key in user_roles.
This is the GOLD standard for scalable systems.
"""

from __future__ import annotations

from typing import List
from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class Role(BaseModel):
    __tablename__ = "roles"

    # We keep name as PK for simplicity & performance.
    # NOTE: Since BaseModel also has an 'id' PK, this table effectively has 
    # a Composite Primary Key (id, name). This is valid in SQLAlchemy.
    name: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        nullable=False,
        comment="Admin, Professor, AssociateTeacher, Student"
    )
    
    display_name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    
    description: Mapped[str] = mapped_column(
        Text, nullable=True
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default="true"
    )
    
    can_create_quizzes: Mapped[bool] = mapped_column(default=False)
    can_grade_assignments: Mapped[bool] = mapped_column(default=False)
    can_manage_users: Mapped[bool] = mapped_column(default=False)
    can_view_all_courses: Mapped[bool] = mapped_column(default=False)

    # Optional: back-populate from UserRole if needed
    # users: Mapped[List["UserRole"]] = relationship(back_populates="role_ref")

    def __repr__(self) -> str:
        return f"<Role {self.display_name}>"

    class Permissions:
        """Helper to check permissions"""
        def __init__(self, role: Role):
            self.role = role
        
        def can_create_quizzes(self) -> bool:
            return self.role.can_create_quizzes

# === SEED DATA (run once on startup or via migration) ===
ROLES_SEED = [
    {
        "name": "Admin",
        "display_name": "System Administrator",
        "description": "Full access to the entire system",
        "can_create_quizzes": True,
        "can_grade_assignments": True,
        "can_manage_users": True,
        "can_view_all_courses": True,
    },
    {
        "name": "Professor",
        "display_name": "Professor",
        "description": "Full teaching rights",
        "can_create_quizzes": True,
        "can_grade_assignments": True,
        "can_manage_users": False,
        "can_view_all_courses": True,
    },
    {
        "name": "AssociateTeacher",
        "display_name": "Associate Teacher / TA",
        "description": "Can assist in teaching and grading",
        "can_create_quizzes": True,
        "can_grade_assignments": True,
        "can_manage_users": False,
        "can_view_all_courses": False,
    },
    {
        "name": "Student",
        "display_name": "Student",
        "description": "Standard student access",
        "can_create_quizzes": False,
        "can_grade_assignments": False,
        "can_manage_users": False,
        "can_view_all_courses": False,
    },
]
