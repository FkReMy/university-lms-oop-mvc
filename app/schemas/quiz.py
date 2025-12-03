"""
app/schemas/quiz.py
Full Pydantic schemas for Digital + FileUpload Quizzes
Perfect OpenAPI docs, validation, and frontend integration
"""

from __future__ import annotations

from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator
from uuid import UUID


# =============================================================================
# BASE & COMMON
# =============================================================================

class QuizBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    quiz_type: Literal["Digital", "FileUpload"] = "Digital"
    deadline: datetime
    start_time: Optional[datetime] = None
    time_limit_minutes: Optional[int] = Field(None, ge=5, le=300)
    max_attempts: Optional[int] = Field(1, ge=1, le=10)
    is_published: bool = False
    show_results_after: bool = True


class QuizCreate(QuizBase):
    offering_id: str
    instructions_file_id: Optional[str] = None


class QuizUpdate(QuizBase):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    is_published: Optional[bool] = None


# =============================================================================
# QUESTION & OPTIONS
# =============================================================================

class QuestionOptionBase(BaseModel):
    option_label: str = Field(..., regex="^[A-F]$")  # A, B, C, D, E, F
    option_text: str = Field(..., min_length=1, max_length=1000)
    is_correct: bool = False


class QuestionOptionCreate(QuestionOptionBase):
    pass


class QuestionOptionOut(QuestionOptionBase):
    option_id: str

    class Config:
        from_attributes = True


class QuestionBase(BaseModel):
    question_text: str = Field(..., min_length=5, max_length=2000)
    question_type: Literal["MCQ", "TrueFalse", "Paragraph"]
    marks: float = Field(1.0, ge=0.5, le=100.0)
    order_number: int = Field(..., ge=1)


class QuestionCreate(QuestionBase):
    options: List[QuestionOptionCreate] = Field(
        ..., min_items=2, max_items=6,
        description="Required for MCQ/TrueFalse. Must have exactly 1 correct."
    )

    @validator("options")
    def validate_options(cls, v, values):
        qtype = values.get("question_type")
        if qtype in ["MCQ", "TrueFalse"] and len(v) < 2:
            raise ValueError("MCQ/TrueFalse must have at least 2 options")
        if qtype == "TrueFalse" and len(v) != 2:
            raise ValueError("True/False questions must have exactly 2 options")
        correct_count = sum(1 for opt in v if opt.is_correct)
        if qtype in ["MCQ", "TrueFalse"] and correct_count != 1:
            raise ValueError("Exactly one option must be correct for MCQ/TrueFalse")
        if qtype == "Paragraph" and v:
            raise ValueError("Paragraph questions cannot have options")
        return v


class QuestionUpdate(QuestionBase):
    question_text: Optional[str] = None
    marks: Optional[float] = None
    order_number: Optional[int] = None
    options: Optional[List[QuestionOptionCreate]] = None


class QuestionOut(QuestionBase):
    question_id: str
    options: List[QuestionOptionOut] = []

    class Config:
        from_attributes = True


# =============================================================================
# QUIZ RESPONSE
# =============================================================================

class QuizOut(QuizBase):
    quiz_id: str
    offering_id: str
    created_by_id: str
    created_by_role: str
    created_at: datetime
    updated_at: datetime
    instructions_file_url: Optional[str] = None
    total_marks: Optional[float] = None
    question_count: int = 0

    class Config:
        from_attributes = True


class QuizDetailOut(QuizOut):
    questions: List[QuestionOut] = []

    class Config:
        from_attributes = True


# =============================================================================
# STUDENT QUIZ ATTEMPT
# =============================================================================

class StudentAnswer(BaseModel):
    question_id: str
    selected_option_id: Optional[str] = None
    answer_text: Optional[str] = None


class QuizAttemptCreate(BaseModel):
    answers: List[StudentAnswer]


class QuizAttemptOut(BaseModel):
    attempt_id: str
    quiz_id: str
    attempt_number: int
    started_at: datetime
    submitted_at: Optional[datetime]
    score: Optional[float]
    total_marks: Optional[float]
    is_completed: bool

    class Config:
        from_attributes = True


# =============================================================================
# FILE SUBMISSION
# =============================================================================

class QuizFileSubmit(BaseModel):
    file_id: str  # file_id from upload


class QuizFileSubmissionOut(BaseModel):
    submission_id: str
    quiz_id: str
    student_id: str
    file_url: str
    filename: str
    submitted_at: datetime
    is_late: bool

    class Config:
        from_attributes = True


# =============================================================================
# GRADING
# =============================================================================

class QuizGradeCreate(BaseModel):
    final_score: float = Field(..., ge=0)
    feedback_text: Optional[str] = None
    feedback_file_id: Optional[str] = None


class QuizGradeOut(BaseModel):
    grade_id: str
    final_score: float
    feedback_text: Optional[str]
    feedback_file_url: Optional[str]
    graded_at: datetime
    graded_by_name: str

    class Config:
        from_attributes = True


# =============================================================================
# STUDENT VIEW OF QUIZ (no answers shown)
# =============================================================================

class QuizStudentView(QuizBase):
    quiz_id: str
    has_attempted: bool = False
    best_score: Optional[float] = None
    attempts_used: int = 0
    can_attempt: bool = True
    time_remaining: Optional[int] = None  # minutes

    class Config:
        from_attributes = True