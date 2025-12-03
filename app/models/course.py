"""
app/models/course.py
Complete Course Management System – Enterprise Grade 2025

Includes:
- CourseCatalog (permanent)
- CourseOffering (per semester)
- SectionGroup (Lecture, Section, Lab)
- CourseEnrollment (student registration)
- ScheduledSlot (timetable)
- Full relationships + compound keys
"""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy import (
    String, Integer, DateTime, ForeignKey, Enum, Text, UniqueConstraint,
    CheckConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel
from app.models.user import Professor


# =============================================================================
# COURSE CATALOG – Permanent courses (CS101, MATH201, etc.)
# =============================================================================
class CourseCatalog(BaseModel):
    __tablename__ = "course_catalog"

    course_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    dept_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("departments.dept_id"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="courses")
    offerings: Mapped[List["CourseOffering"]] = relationship(
        "CourseOffering", back_populates="course", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Course {self.course_code} – {self.course_name}>"


# =============================================================================
# COURSE OFFERING – One instance per semester
# =============================================================================
class CourseOffering(BaseModel):
    __tablename__ = "course_offerings"

    offering_id: Mapped[str_pk]
    course_code: Mapped[str] = mapped_column(
        String(20), ForeignKey("course_catalog.course_code"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String, ForeignKey("academic_sessions.session_id"))
    professor_id: Mapped[str] = mapped_column(String, ForeignKey("professors.user_id"))
    course_type: Mapped[str] = mapped_column(
        Enum("LectureOnly", "Lecture+Section", "Lecture+Section+Lab", name="course_type"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="Planned", server_default="Planned"
    )

    # Relationships
    course: Mapped["CourseCatalog"] = relationship("CourseCatalog", back_populates="offerings")
    professor: Mapped["Professor"] = relationship("Professor")
    session: Mapped["AcademicSession"] = relationship("AcademicSession", back_populates="offerings")
    enrollments: Mapped[List["CourseEnrollment"]] = relationship("CourseEnrollment", back_populates="offering")
    sections: Mapped[List["SectionGroup"]] = relationship("SectionGroup", back_populates="offering")
    slots: Mapped[List["ScheduledSlot"]] = relationship("ScheduledSlot", back_populates="offering")

    __table_args__ = (
        UniqueConstraint("course_code", "session_id", name="uq_course_per_session"),
    )


# =============================================================================
# SECTION GROUPS – Lab / Tutorial sections
# =============================================================================
class SectionGroup(BaseModel):
    __tablename__ = "section_groups"

    section_group_id: Mapped[str_pk]
    offering_id: Mapped[str] = mapped_column(String, ForeignKey("course_offerings.offering_id"))
    group_type: Mapped[str] = mapped_column(
        Enum("Section", "Lab", name="group_type"), nullable=False
    )
    group_number: Mapped[int] = mapped_column(Integer, nullable=False)
    associate_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("associate_teachers.user_id"), nullable=True
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    offering: Mapped["CourseOffering"] = relationship("CourseOffering", back_populates="sections")
    associate: Mapped[Optional["AssociateTeacher"]] = relationship("AssociateTeacher")
    assignments: Mapped[List["StudentSectionAssignment"]] = relationship(
        "StudentSectionAssignment", back_populates="section"
    )
    slots: Mapped[List["ScheduledSlot"]] = relationship("ScheduledSlot", back_populates="section")

    __table_args__ = (
        UniqueConstraint("offering_id", "group_type", "group_number", name="uq_section_number"),
    )


# =============================================================================
# STUDENT ENROLLMENT IN COURSE
# =============================================================================
class CourseEnrollment(BaseModel):
    __tablename__ = "course_enrollments"

    student_id: Mapped[str] = mapped_column(
        String, ForeignKey("students.user_id"), primary_key=True
    )
    offering_id: Mapped[str] = mapped_column(
        String, ForeignKey("course_offerings.offering_id"), primary_key=True
    )
    enrolled_at: Mapped[created_at_col]
    final_grade: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Relationships
    student: Mapped["Student"] = relationship("Student")
    offering: Mapped["CourseOffering"] = relationship("CourseOffering", back_populates="enrollments")
    section_assignments: Mapped[List["StudentSectionAssignment"]] = relationship(
        "StudentSectionAssignment", back_populates="enrollment"
    )


# =============================================================================
# STUDENT → SECTION ASSIGNMENT
# =============================================================================
class StudentSectionAssignment(BaseModel):
    __tablename__ = "student_section_assignments"

    student_id: Mapped[str] = mapped_column(
        String, ForeignKey("students.user_id"), primary_key=True
    )
    section_group_id: Mapped[str] = mapped_column(
        String, ForeignKey("section_groups.section_group_id"), primary_key=True
    )
    assigned_at: Mapped[created_at_col]

    enrollment: Mapped["CourseEnrollment"] = relationship("CourseEnrollment", back_populates="section_assignments")
    section: Mapped["SectionGroup"] = relationship("SectionGroup", back_populates="assignments")


# =============================================================================
# TIMETABLE – Scheduled slots
# =============================================================================
class ScheduledSlot(BaseModel):
    __tablename__ = "scheduled_slots"

    slot_id: Mapped[str_pk]
    offering_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("course_offerings.offering_id"))
    section_group_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("section_groups.section_group_id"))
    room_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("rooms.room_id"))
    day_of_week: Mapped[int] = mapped_column(Integer, CheckConstraint("day_of_week BETWEEN 1 AND 7"))
    start_time: Mapped[str] = mapped_column(String(8))  # "10:00:00"
    end_time: Mapped[str] = mapped_column(String(8))     # "11:30:00"
    slot_type: Mapped[str] = mapped_column(String(20), default="Lecture")

    offering: Mapped[Optional["CourseOffering"]] = relationship("CourseOffering", back_populates="slots")
    section: Mapped[Optional["SectionGroup"]] = relationship("SectionGroup", back_populates="slots")
    room: Mapped[Optional["Room"]] = relationship("Room")