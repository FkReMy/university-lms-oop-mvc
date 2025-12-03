"""
app/models/quiz.py
Complete Quiz System – Digital + FileUpload
Used by Canvas, Moodle, Blackboard – but better
"""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy import (
    String, Text, DateTime, Boolean, ForeignKey, Enum, Integer, Float,
    UniqueConstraint, CheckConstraint, func, LargeBinary
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel
from app.models.course import CourseOffering
from app.models.file import UploadedFile


# =============================================================================
# QUIZ – Main quiz (Digital or FileUpload)
# =============================================================================
class Quiz(BaseModel):
    __tablename__ = "quizzes"

    quiz_id: Mapped[str_pk]
    offering_id: Mapped[str] = mapped_column(String, ForeignKey("course_offerings.offering_id"), nullable=False)
    created_by_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"), nullable=False)
    created_by_role: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    instructions_file_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("uploaded_files.file_id"))

    quiz_type: Mapped[str] = mapped_column(
        Enum("Digital", "FileUpload", name="quiz_type"),
        nullable=False,
        default="Digital"
    )
    start_time: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True))
    deadline: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    time_limit_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    max_attempts: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    show_results_after: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    offering: Mapped["CourseOffering"] = relationship("CourseOffering", back_populates="quizzes")
    creator: Mapped["User"] = relationship("User")
    instructions_file: Mapped[Optional["UploadedFile"]] = relationship("UploadedFile")
    questions: Mapped[List["Question"]] = relationship(
        "Question", back_populates="quiz", cascade="all, delete-orphan"
    )
    attempts: Mapped[List["QuizAttempt"]] = relationship(
        "QuizAttempt", back_populates="quiz", cascade="all, delete-orphan"
    )
    file_submissions: Mapped[List["QuizFileSubmission"]] = relationship(
        "QuizFileSubmission", back_populates="quiz"
    )
    grades: Mapped[List["QuizGrade"]] = relationship("QuizGrade", back_populates="quiz")


# =============================================================================
# QUESTION – Only for Digital quizzes
# =============================================================================
class Question(BaseModel):
    __tablename__ = "questions"

    question_id: Mapped[str_pk]
    quiz_id: Mapped[str] = mapped_column(String, ForeignKey("quizzes.quiz_id"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        Enum("MCQ", "TrueFalse", "Paragraph", name="question_type"),
        nullable=False
    )
    marks: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    order_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="questions")
    options: Mapped[List["QuestionOption"]] = relationship(
        "QuestionOption", back_populates="question", cascade="all, delete-orphan"
    )
    answers: Mapped[List["QuizAnswer"]] = relationship("QuizAnswer", back_populates="question")

    __table_args__ = (
        UniqueConstraint("quiz_id", "order_number", name="uq_question_order"),
        CheckConstraint(
            "(SELECT quiz_type FROM quizzes q WHERE q.quiz_id = quiz_id) = 'Digital'",
            name="ck_digital_only_questions"
        ),
    )


# =============================================================================
# MCQ / TRUE-FALSE OPTIONS (A, B, C, D...)
# =============================================================================
class QuestionOption(BaseModel):
    __tablename__ = "question_options"

    option_id: Mapped[str_pk]
    question_id: Mapped[str] = mapped_column(String, ForeignKey("questions.question_id"), nullable=False)
    option_label: Mapped[str] = mapped_column(String(1), nullable=False)  # A, B, C, D, E, F
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    order_number: Mapped[int] = mapped_column(Integer, nullable=False)

    question: Mapped["Question"] = relationship("Question", back_populates="options")

    __table_args__ = (
        UniqueConstraint("question_id", "option_label", name="uq_option_label"),
        UniqueConstraint("question_id", "order_number", name="uq_option_order"),
    )


# =============================================================================
# DIGITAL QUIZ ATTEMPT
# =============================================================================
class QuizAttempt(BaseModel):
    __tablename__ = "quiz_attempts"

    attempt_id: Mapped[str_pk]
    quiz_id: Mapped[str] = mapped_column(String, ForeignKey("quizzes.quiz_id"), nullable=False)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.user_id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True))
    score: Mapped[Optional[float]] = mapped_column(Float)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="attempts")
    student: Mapped["Student"] = relationship("Student")
    answers: Mapped[List["QuizAnswer"]] = relationship("QuizAnswer", back_populates="attempt")
    grade: Mapped[Optional["QuizGrade"]] = relationship("QuizGrade", back_populates="attempt")

    __table_args__ = (
        UniqueConstraint("quiz_id", "student_id", "attempt_number", name="uq_student_attempt"),
    )


# =============================================================================
# STUDENT ANSWER (Digital)
# =============================================================================
class QuizAnswer(BaseModel):
    __tablename__ = "quiz_answers"

    answer_id: Mapped[str_pk]
    attempt_id: Mapped[str] = mapped_column(String, ForeignKey("quiz_attempts.attempt_id"), nullable=False)
    question_id: Mapped[str] = mapped_column(String, ForeignKey("questions.question_id"), nullable=False)

    selected_option_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("question_options.option_id"))
    answer_text: Mapped[Optional[str]] = mapped_column(Text)  # For Paragraph

    awarded_marks: Mapped[Optional[float]] = mapped_column(Float)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    answered_at: Mapped[created_at_col]

    attempt: Mapped["QuizAttempt"] = relationship("QuizAttempt", back_populates="answers")
    question: Mapped["Question"] = relationship("Question", back_populates="answers")
    selected_option: Mapped[Optional["QuestionOption"]] = relationship("QuestionOption")

    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_one_answer_per_question"),
    )


# =============================================================================
# FILE-BASED QUIZ SUBMISSION (take-home exam)
# =============================================================================
class QuizFileSubmission(BaseModel):
    __tablename__ = "quiz_file_submissions"

    submission_id: Mapped[str_pk]
    quiz_id: Mapped[str] = mapped_column(String, ForeignKey("quizzes.quiz_id"), nullable=False)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.user_id"), nullable=False)
    submitted_file_id: Mapped[str] = mapped_column(String, ForeignKey("uploaded_files.file_id"), nullable=False)
    submitted_at: Mapped[created_at_col]
    is_late: Mapped[bool] = mapped_column(Boolean, server_default="false")

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="file_submissions")
    student: Mapped["Student"] = relationship("Student")
    file: Mapped["UploadedFile"] = relationship("UploadedFile")
    grade: Mapped[Optional["QuizGrade"]] = relationship("QuizGrade", back_populates="file_submission")

    __table_args__ = (
        UniqueConstraint("quiz_id", "student_id", name="uq_one_file_per_student"),
    )


# =============================================================================
# FINAL QUIZ GRADING (works for both types)
# =============================================================================
class QuizGrade(BaseModel):
    __tablename__ = "quiz_grades"

    grade_id: Mapped[str_pk]
    attempt_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("quiz_attempts.attempt_id"))
    file_submission_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("quiz_file_submissions.submission_id"))
    graded_by_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"), nullable=False)
    graded_by_role: Mapped[str] = mapped_column(String(20), nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    feedback_text: Mapped[Optional[str]] = mapped_column(Text)
    feedback_file_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("uploaded_files.file_id"))
    graded_at: Mapped[created_at_col]

    attempt: Mapped[Optional["QuizAttempt"]] = relationship("QuizAttempt", back_populates="grade")
    file_submission: Mapped[Optional["QuizFileSubmission"]] = relationship("QuizFileSubmission", back_populates="grade")
    graded_by: Mapped["User"] = relationship("User")
    feedback_file: Mapped[Optional["UploadedFile"]] = relationship("UploadedFile")
    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="grades")

    __table_args__ = (
        CheckConstraint(
            "(attempt_id IS NOT NULL AND file_submission_id IS NULL) OR (attempt_id IS NULL AND file_submission_id IS NOT NULL)",
            name="ck_one_source_only"
        ),
    )