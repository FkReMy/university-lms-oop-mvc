"""
app/services/assignment_service.py
Complete Business Logic Layer for Assignment System
Handles:
- Assignment creation with reference file
- Student file submission (PDF/Word)
- Late detection
- Teacher grading + feedback file
- Similarity/plagiarism detection ready
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.file_repository import FileRepository
from app.repositories.user_repository import UserRepository

from app.schemas.assignment import (
    AssignmentCreate, AssignmentUpdate, AssignmentSubmit,
    AssignmentGradeCreate, AssignmentOut, AssignmentDetailOut,
    AssignmentSubmissionOut, AssignmentGradeOut
)
from app.models.assignment import Assignment, AssignmentSubmission, AssignmentGrade
from app.core.security import SecurityManager
from app.utils.exceptions import (
    NotFoundException, ForbiddenException, ConflictException, BadRequestException
)


class AssignmentService:
    def __init__(self, db: Session):
        self.assignment_repo = AssignmentRepository(db)
        self.file_repo = FileRepository(db)
        self.user_repo = UserRepository(db)
        self.db = db

    # ===================================================================
    # CREATE & UPDATE ASSIGNMENT
    # ===================================================================

    def create_assignment(
        self,
        assignment_data: AssignmentCreate,
        creator_id: str,
        creator_role: str
    ) -> AssignmentOut:
        if creator_role not in ["Professor", "AssociateTeacher"]:
            raise ForbiddenException("Only teachers can create assignments")

        if assignment_data.deadline <= datetime.now(timezone.utc):
            raise BadRequestException("Deadline must be in the future")

        # Validate reference file belongs to creator
        if assignment_data.reference_file_id:
            file = self.file_repo.get_file_by_id(assignment_data.reference_file_id)
            if not file or file.uploaded_by != creator_id:
                raise ForbiddenException("Invalid reference file")

        assignment = self.assignment_repo.create_assignment(
            assignment_data, creator_id, creator_role
        )

        self.db.commit()
        return AssignmentOut.from_orm(assignment)

    def update_assignment(
        self,
        assignment_id: str,
        update_data: AssignmentUpdate,
        user_id: str
    ) -> AssignmentOut:
        assignment = self.assignment_repo.get_assignment_by_id(assignment_id)
        if not assignment:
            raise NotFoundException("Assignment not found")

        if assignment.created_by_id != user_id:
            raise ForbiddenException("You can only edit your own assignments")

        updated = self.assignment_repo.update_assignment(assignment_id, update_data)
        self.db.commit()
        return AssignmentOut.from_orm(updated)

    # ===================================================================
    # STUDENT: SUBMIT ASSIGNMENT
    # ===================================================================

    def submit_assignment(
        self,
        assignment_id: str,
        submission: AssignmentSubmit,
        student_id: str
    ) -> AssignmentSubmissionOut:
        assignment = self.assignment_repo.get_assignment_by_id(assignment_id)
        if not assignment:
            raise NotFoundException("Assignment not found")

        if assignment.deadline < datetime.now(timezone.utc):
            raise BadRequestException("Assignment deadline has passed")

        # Check if already submitted
        existing = self.assignment_repo.get_submission(assignment_id, student_id)
        if existing:
            raise ConflictException("You have already submitted this assignment")

        # Validate file ownership
        file = self.file_repo.get_file_by_id(submission.file_id)
        if not file or file.uploaded_by != student_id:
            raise ForbiddenException("Invalid file submitted")

        # Create submission
        submission_record = self.assignment_repo.submit_assignment(
            assignment_id=assignment_id,
            student_id=student_id,
            file_id=submission.file_id
        )

        # Auto detect late
        submission_record.is_late = submission_record.submitted_at > assignment.deadline

        # Optional: trigger plagiarism check (Cel Detect)
        # plagiarism_task.delay(submission_record.submission_id)

        self.db.commit()
        return AssignmentSubmissionOut.from_orm(submission_record)

    # ===================================================================
    # TEACHER: GRADE ASSIGNMENT
    # ===================================================================

    def grade_assignment(
        self,
        submission_id: str,
        grade_data: AssignmentGradeCreate,
        grader_id: str,
        grader_role: str
    ) -> AssignmentGradeOut:
        if grader_role not in ["Professor", "AssociateTeacher"]:
            raise ForbiddenException("Only teachers can grade")

        submission = self.assignment_repo.get_submission_by_id(submission_id)
        if not submission:
            raise NotFoundException("Submission not found")

        if submission.grade:
            raise ConflictException("This assignment has already been graded")

        # Validate feedback file belongs to grader
        if grade_data.feedback_file_id:
            file = self.file_repo.get_file_by_id(grade_data.feedback_file_id)
            if not file or file.uploaded_by != grader_id:
                raise ForbiddenException("Invalid feedback file")

        grade = self.assignment_repo.create_grade(
            submission_id=submission_id,
            grade_data=grade_data,
            grader_id=grader_id,
            grader_role=grader_role
        )

        self.db.commit()
        return AssignmentGradeOut.from_orm(grade)

    # ===================================================================
    # LIST & VIEW
    # ===================================================================

    def get_assignment_detail(
        self,
        assignment_id: str,
        user_id: str,
        user_role: str
    ) -> AssignmentDetailOut:
        assignment = self.assignment_repo.get_assignment_with_details(assignment_id)
        if not assignment:
            raise NotFoundException("Assignment not found")

        # Add submission status for student
        if user_role == "Student":
            submission = self.assignment_repo.get_submission(assignment_id, user_id)
            return AssignmentDetailOut(
                **assignment.__dict__,
                my_submission=AssignmentSubmissionOut.from_orm(submission) if submission else None,
                has_submitted=bool(submission),
                is_late=submission.is_late if submission else None
            )

        return AssignmentDetailOut.from_orm(assignment)

    def list_assignments_for_offering(
        self,
        offering_id: str,
        user_id: str,
        user_role: str
    ) -> List[AssignmentOut]:
        assignments = self.assignment_repo.list_assignments_for_offering(
            offering_id=offering_id
        )

        # For students: enrich with submission status
        if user_role == "Student":
            for assignment in assignments:
                submission = self.assignment_repo.get_submission(assignment.assignment_id, user_id)
                assignment.has_submitted = bool(submission)
                assignment.is_late = submission.is_late if submission else None
                assignment.submitted_at = submission.submitted_at if submission else None

        return [AssignmentOut.from_orm(a) for a in assignments]

    def get_pending_grading(self, teacher_id: str) -> List[Dict[str, Any]]:
        """Get all ungraded submissions for teacher's courses"""
        return self.assignment_repo.get_pending_grading_for_teacher(teacher_id)