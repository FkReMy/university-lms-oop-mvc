"""
app/controllers/quiz_controller.py
Complete FastAPI Controller for Digital + FileUpload Quizzes
Used by Harvard, MIT, Stanford-level systems
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import (
    get_db, get_current_active_user,
    get_teacher_user, get_student_user
)
from app.services.quiz_service import QuizService
from app.schemas.quiz import (
    QuizCreate, QuizUpdate, QuestionCreate,
    QuizAttemptCreate, QuizFileSubmit, QuizGradeCreate,
    QuizOut, QuizDetailOut, QuizStudentView,
    QuizAttemptOut, QuizFileSubmissionOut, QuizGradeOut
)
from app.schemas.common import MessageResponse, PaginatedResponse

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


# ===================================================================
# TEACHER ENDPOINTS (Professor / AssociateTeacher)
# ===================================================================

@router.post("", response_model=QuizOut, status_code=status.HTTP_201_CREATED)
def create_quiz(
    quiz_data: QuizCreate,
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    """Create new quiz (Digital or FileUpload)"""
    service = QuizService(db)
    quiz = service.create_quiz(
        quiz_data=quiz_data,
        creator_id=teacher["user_id"],
        creator_role=teacher["role"]
    )
    return quiz


@router.get("/{quiz_id}", response_model=QuizDetailOut)
def get_quiz_detail(
    quiz_id: str = Path(...),
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    """Get full quiz with questions (teacher view)"""
    service = QuizService(db)
    quiz = service.quiz_repo.get_quiz_with_details(quiz_id)
    if not quiz or quiz.created_by_id != teacher["user_id"]:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return QuizDetailOut.from_orm(quiz)


@router.put("/{quiz_id}", response_model=QuizOut)
def update_quiz(
    quiz_id: str,
    update_data: QuizUpdate,
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    service = QuizService(db)
    quiz = service.update_quiz(quiz_id, update_data, teacher["user_id"], teacher["role"])
    return quiz


@router.post("/{quiz_id}/publish", response_model=MessageResponse)
def publish_quiz(
    quiz_id: str,
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    service = QuizService(db)
    service.publish_quiz(quiz_id, teacher["user_id"])
    return MessageResponse(success=True, message="Quiz published successfully")


@router.post("/{quiz_id}/questions", response_model=MessageResponse)
def add_question(
    quiz_id: str,
    question_data: QuestionCreate,
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    service = QuizService(db)
    result = service.add_question(quiz_id, question_data, teacher["user_id"])
    return MessageResponse(
        success=True,
        message="Question added",
        **result
    )


# ===================================================================
# STUDENT ENDPOINTS
# ===================================================================

@router.get("/offering/{offering_id}", response_model=List[QuizStudentView])
def get_quizzes_for_offering(
    offering_id: str,
    student: dict = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    """Get all quizzes for a course offering (student view)"""
    service = QuizService(db)
    quizzes = service.quiz_repo.list_quizzes_for_offering(offering_id, include_unpublished=False)
    
    result = []
    for quiz in quizzes:
        view = service.get_student_quiz_view(quiz.quiz_id, student["user_id"])
        result.append(view)
    
    return result


@router.get("/student/{quiz_id}", response_model=QuizStudentView)
def get_student_quiz_view(
    quiz_id: str,
    student: dict = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    service = QuizService(db)
    return service.get_student_quiz_view(quiz_id, student["user_id"])


@router.post("/{quiz_id}/start", response_model=MessageResponse)
def start_attempt(
    quiz_id: str,
    student: dict = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    service = QuizService(db)
    result = service.start_quiz_attempt(quiz_id, student["user_id"])
    return MessageResponse(success=True, **result)


@router.post("/attempt/{attempt_id}/submit", response_model=QuizAttemptOut)
def submit_digital_quiz(
    attempt_id: str,
    answers: QuizAttemptCreate,
    student: dict = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    service = QuizService(db)
    result = service.submit_digital_quiz(attempt_id, answers, student["user_id"])
    return result


@router.post("/{quiz_id}/submit-file", response_model=MessageResponse)
def submit_file_quiz(
    quiz_id: str,
    submission: QuizFileSubmit,
    student: dict = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    service = QuizService(db)
    result = service.submit_file_quiz(quiz_id, submission, student["user_id"])
    return MessageResponse(success=True, **result)


# ===================================================================
# GRADING (Teacher)
# ===================================================================

@router.post("/grade/digital/{attempt_id}", response_model=MessageResponse)
def grade_digital_quiz(
    attempt_id: str,
    grade_data: QuizGradeCreate,
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    service = QuizService(db)
    service.grade_quiz(
        grade_data=grade_data,
        target_id=attempt_id,
        target_type="digital",
        grader_id=teacher["user_id"],
        grader_role=teacher["role"]
    )
    return MessageResponse(success=True, message="Quiz graded successfully")


@router.post("/grade/file/{submission_id}", response_model=MessageResponse)
def grade_file_quiz(
    submission_id: str,
    grade_data: QuizGradeCreate,
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    service = QuizService(db)
    service.grade_quiz(
        grade_data=grade_data,
        target_id=submission_id,
        target_type="file",
        grader_id=teacher["user_id"],
        grader_role=teacher["role"]
    )
    return MessageResponse(success=True, message="File quiz graded successfully")


# ===================================================================
# STUDENT: VIEW RESULTS
# ===================================================================

@router.get("/my-attempts/{quiz_id}", response_model=List[QuizAttemptOut])
def get_my_attempts(
    quiz_id: str,
    student: dict = Depends(get_student_user),
    db: Session = Depends(get_db)
):
    service = QuizService(db)
    attempts = service.quiz_repo.get_student_attempts_for_quiz(quiz_id, student["user_id"])
    return [QuizAttemptOut.from_orm(a) for a in attempts]