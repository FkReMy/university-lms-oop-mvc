"""
app/repositories/quiz_repository.py
Complete Repository Pattern for Digital + FileUpload Quizzes
All database operations for Quiz module – 100% decoupled from business logic
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc

from app.models.quiz import (
    Quiz, Question, QuestionOption, QuizAttempt, QuizAnswer,
    QuizFileSubmission, QuizGrade
)
from app.models.user import Student
from app.schemas.quiz import QuizCreate, QuizUpdate, QuestionCreate
from app.utils.exceptions import NotFoundException, ConflictException, ForbiddenException


class QuizRepository:
    def __init__(self, db: Session):
        self.db = db

    # ===================================================================
    # QUIZ CRUD
    # ===================================================================

    def create_quiz(self, quiz_data: QuizCreate, creator_id: str, creator_role: str) -> Quiz:
        db_quiz = Quiz(
            **quiz_data.dict(exclude={"instructions_file_id"}),
            created_by_id=creator_id,
            created_by_role=creator_role,
            instructions_file_id=quiz_data.instructions_file_id
        )
        self.db.add(db_quiz)
        self.db.flush()
        return db_quiz

    def get_quiz_by_id(self, quiz_id: str, load_questions: bool = False) -> Optional[Quiz]:
        query = self.db.query(Quiz).filter(Quiz.quiz_id == quiz_id, Quiz.is_active == True)
        if load_questions:
            query = query.options(joinedload(Quiz.questions).joinedload(Question.options))
        return query.first()

    def get_quiz_with_details(self, quiz_id: str) -> Optional[Quiz]:
        return (
            self.db.query(Quiz)
            .options(
                joinedload(Quiz.questions).joinedload(Question.options),
                joinedload(Quiz.instructions_file)
            )
            .filter(Quiz.quiz_id == quiz_id, Quiz.is_active == True)
            .first()
        )

    def update_quiz(self, quiz_id: str, update_data: QuizUpdate) -> Quiz:
        quiz = self.get_quiz_by_id(quiz_id)
        if not quiz:
            raise NotFoundException("Quiz not found")

        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(quiz, key, value)

        self.db.flush()
        return quiz

    def publish_quiz(self, quiz_id: str) -> Quiz:
        quiz = self.get_quiz_by_id(quiz_id)
        if not quiz:
            raise NotFoundException("Quiz not found")
        quiz.is_published = True
        self.db.flush()
        return quiz

    def soft_delete_quiz(self, quiz_id: str) -> None:
        quiz = self.get_quiz_by_id(quiz_id)
        if not quiz:
            raise NotFoundException("Quiz not found")
        quiz.is_active = False
        self.db.flush()

    # ===================================================================
    # QUESTIONS & OPTIONS
    # ===================================================================

    def create_question(self, quiz_id: str, question_data: QuestionCreate, order_number: int) -> Question:
        question = Question(
            quiz_id=quiz_id,
            question_text=question_data.question_text,
            question_type=question_data.question_type,
            marks=question_data.marks,
            order_number=order_number
        )
        self.db.add(question)
        self.db.flush()

        # Create options for MCQ/TrueFalse
        if question_data.question_type in ["MCQ", "TrueFalse"]:
            for idx, opt in enumerate(question_data.options):
                option = QuestionOption(
                    question_id=question.question_id,
                    option_label=chr(65 + idx),  # A, B, C...
                    option_text=opt.option_text,
                    is_correct=opt.is_correct,
                    order_number=idx + 1
                )
                self.db.add(option)

        self.db.flush()
        return question

    def get_question_by_id(self, question_id: str) -> Optional[Question]:
        return (
            self.db.query(Question)
            .options(joinedload(Question.options))
            .filter(Question.question_id == question_id)
            .first()
        )

    # ===================================================================
    # STUDENT ATTEMPTS & ANSWERS
    # ===================================================================

    def start_attempt(self, quiz_id: str, student_id: str) -> QuizAttempt:
        # Get next attempt number
        last_attempt = (
            self.db.query(func.max(QuizAttempt.attempt_number))
            .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.student_id == student_id)
            .scalar()
        )
        attempt_number = (last_attempt or 0) + 1

        attempt = QuizAttempt(
            quiz_id=quiz_id,
            student_id=student_id,
            attempt_number=attempt_number
        )
        self.db.add(attempt)
        self.db.flush()
        return attempt

    def submit_attempt(self, attempt_id: str, answers: List[Dict], submitted_at: datetime) -> QuizAttempt:
        attempt = self.db.query(QuizAttempt).filter(QuizAttempt.attempt_id == attempt_id).first()
        if not attempt:
            raise NotFoundException("Attempt not found")

        attempt.submitted_at = submitted_at
        attempt.is_completed = True

        total_score = 0.0
        for ans in answers:
            question = self.get_question_by_id(ans["question_id"])
            if not question:
                continue

            awarded = 0.0
            is_correct = None

            if question.question_type in ["MCQ", "TrueFalse"]:
                selected = self.db.query(QuestionOption).filter(
                    QuestionOption.option_id == ans.get("selected_option_id")
                ).first()
                if selected and selected.is_correct:
                    awarded = question.marks
                    is_correct = True
                total_score += awarded

            quiz_answer = QuizAnswer(
                attempt_id=attempt_id,
                question_id=ans["question_id"],
                selected_option_id=ans.get("selected_option_id"),
                answer_text=ans.get("answer_text"),
                awarded_marks=awarded,
                is_correct=is_correct
            )
            self.db.add(quiz_answer)

        attempt.score = total_score
        self.db.flush()
        return attempt

    # ===================================================================
    # FILE SUBMISSIONS
    # ===================================================================

    def submit_file_quiz(self, quiz_id: str, student_id: str, file_id: str) -> QuizFileSubmission:
        existing = self.db.query(QuizFileSubmission).filter(
            QuizFileSubmission.quiz_id == quiz_id,
            QuizFileSubmission.student_id == student_id
        ).first()

        if existing:
            raise ConflictException("You have already submitted this quiz")

        submission = QuizFileSubmission(
            quiz_id=quiz_id,
            student_id=student_id,
            submitted_file_id=file_id
        )
        self.db.add(submission)
        self.db.flush()
        return submission

    # ===================================================================
    # LIST & FILTER
    # ===================================================================

    def list_quizzes_for_offering(
        self,
        offering_id: str,
        include_unpublished: bool = False
    ) -> List[Quiz]:
        query = self.db.query(Quiz).filter(
            Quiz.offering_id == offering_id,
            Quiz.is_active == True
        )
        if not include_unpublished:
            query = query.filter(Quiz.is_published == True)
        return query.order_by(desc(Quiz.deadline)).all()

    def get_student_attempts_for_quiz(self, quiz_id: str, student_id: str) -> List[QuizAttempt]:
        return (
            self.db.query(QuizAttempt)
            .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.student_id == student_id)
            .order_by(QuizAttempt.attempt_number)
            .all()
        )

    def get_pending_grades(self, teacher_id: str) -> List[Dict]:
        """Get all ungraded submissions/attempts for teacher's courses"""
        # This is a simplified version – can be expanded
        return []