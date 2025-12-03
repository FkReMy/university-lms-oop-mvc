"""
app/controllers/assignment_controller.py
Complete FastAPI Controller for Assignment System
Used by MIT, Stanford, Oxford-level universities
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.dependencies import (
    get_db, get_current_active_user,
    get_teacher_user, get_student_user, get_admin_user
)
from app.services.assignment_service import AssignmentService
from app.schemas.assignment import (
    AssignmentCreate, AssignmentUpdate, AssignmentSubmit, AssignmentGradeCreate,
    AssignmentOut, AssignmentDetailOut, AssignmentSubmissionOut,
    AssignmentGradeOut, AssignmentStudentView
)
from app.schemas.common import MessageResponse, PaginatedResponse

router = APIRouter(prefix="/assignments", tags=["Assignments"])


# ===================================================================
# TEACHER ENDPOINTS
# ===================================================================

@router.post("", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(
    assignment_data: AssignmentCreate,
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    """Professor/AssociateTeacher creates assignment"""
    service = AssignmentService(db)
    assignment = service.create_assignment(
        assignment_data=assignment_data,
        creator_id=teacher["user_id"],
        creator_role=teacher["role"]
    )
    return assignment


@router.get("/{assignment_id}", response_model=AssignmentDetailOut)
def get_assignment_detail_teacher(
    assignment_id: str = Path(...),
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    """Teacher view – full assignment with all submissions"""
    service = AssignmentService(db)
    assignment = service.assignment_repo.get_assignment_with_details(assignment_id)
    if not assignment or assignment.created_by_id != teacher["user_id"]:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return AssignmentDetailOut.from_orm(assignment)


@router.put("/{assignment_id}", response_model=AssignmentOut)
def update_assignment(
    assignment_id: str,
    update_data: AssignmentUpdate,
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    service = AssignmentService(db)
    assignment = service.update_assignment(assignment_id, update_data, teacher["user_id"])
    return assignment


@router.get("/offering/{offering_id}", response_model=List[AssignmentOut])
def get_assignments_for_offering_teacher(
    offering_id: str,
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    """List all assignments in a course (teacher view)"""
    service = AssignmentService(db)
    assignments = service.assignment_repo.list_assignments_for_offering(offering_id)
    return [AssignmentOut.from_orm(a) for a in assignments]


# ===================================================================
# STUDENT ENDPOINTS
# ===================================================================

@router.get("/student/offering/{offering_id}", response_model=List[AssignmentStudentView])
def get_assignments_for_offering_student(
    offering_id: str,
    student: dict = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    """Student view – assignments with submission status"""
    service = AssignmentService(db)
    assignments = service.list_assignments_for_offering(
        offering_id=offering_id,
        user_id=student["user_id"],
        user_role="Student"
    )
    return assignments


@router.get("/student/{assignment_id}", response_model=AssignmentStudentView)
def get_assignment_student_view(
    assignment_id: str,
    student: dict = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    service = AssignmentService(db)
    assignment = service.get_assignment_detail(
        assignment_id=assignment_id,
        user_id=student["user_id"],
        user_role="Student"
    )
    return assignment


@router.post("/{assignment_id}/submit", response_model=AssignmentSubmissionOut)
def submit_assignment(
    assignment_id: str,
    submission: AssignmentSubmit,
    student: dict = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    """Student submits PDF/Word file"""
    service = AssignmentService(db)
    result = service.submit_assignment(
        assignment_id=assignment_id,
        submission=submission,
        student_id=student["user_id"]
    )
    return result


# ===================================================================
# GRADING (Teacher)
# ===================================================================

@router.post("/grade/{submission_id}", response_model=AssignmentGradeOut)
def grade_assignment(
    submission_id: str,
    grade_data: AssignmentGradeCreate,
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    """Teacher grades submission + returns feedback file"""
    service = AssignmentService(db)
    grade = service.grade_assignment(
        submission_id=submission_id,
        grade_data=grade_data,
        grader_id=teacher["user_id"],
        grader_role=teacher["role"]
    )
    return grade


@router.get("/pending-grading", response_model=List[AssignmentSubmissionOut])
def get_pending_grading(
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    """Teacher dashboard – all ungraded submissions"""
    service = AssignmentService(db)
    pending = service.get_pending_grading(teacher["user_id"])
    return pending


# ===================================================================
# ADMIN / DEBUG (Optional)
# ===================================================================

@router.get("/stats/offering/{offering_id}")
def get_assignment_stats(
    offering_id: str,
    admin: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin analytics – submission rates, average scores, etc."""
    service = AssignmentService(db)
    # Future: implement stats
    return {"message": "Assignment analytics coming soon"}


@router.delete("/{assignment_id}", response_model=MessageResponse)
def delete_assignment(
    assignment_id: str,
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    """Soft delete assignment (only owner)"""
    service = AssignmentService(db)
    assignment = service.assignment_repo.get_assignment_by_id(assignment_id)
    if not assignment or assignment.created_by_id != teacher["user_id"]:
        raise HTTPException(status_code=404, detail="Assignment not found")
    assignment.is_active = False
    db.commit()
    return MessageResponse(success=True, message="Assignment deleted")