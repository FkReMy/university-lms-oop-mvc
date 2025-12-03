"""
app/repositories/user_repository.py
Clean Repository Pattern – separates data access from business logic
All user-related DB operations go here
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.models.user import User, UserRole, Professor, Student, AssociateTeacher, Admin
from app.models.role import Role
from app.core.security import SecurityManager
from app.schemas.user import UserCreate, UserUpdate, ChangePassword
from app.utils.exceptions import NotFoundException, ConflictException, UnauthorizedException


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    # ===================================================================
    # CORE USER OPERATIONS
    # ===================================================================

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(
            User.user_id == user_id,
            User.is_active == True
        ).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(
            func.lower(User.email) == email.lower(),
            User.is_active == True
        ).first()

    def create_user(self, user_data: UserCreate, role: str = "Student") -> User:
        # Check email conflict
        if self.get_by_email(user_data.email):
            raise ConflictException("Email already registered")

        # Hash password
        hashed_password = SecurityManager.hash_password(user_data.password)

        # Create user
        db_user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=hashed_password
        )
        self.db.add(db_user)
        self.db.flush()  # Get user_id

        # Assign role
        user_role = UserRole(user_id=db_user.user_id, role=role)
        self.db.add(user_role)

        # Create role-specific profile
        if role == "Professor":
            self.db.add(Professor(user_id=db_user.user_id))
        elif role == "AssociateTeacher":
            self.db.add(AssociateTeacher(user_id=db_user.user_id))
        elif role == "Student":
            self.db.add(Student(user_id=db_user.user_id, student_code=self._generate_student_code()))
        elif role == "Admin":
            self.db.add(Admin(user_id=db_user.user_id))

        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update_user(self, user_id: str, update_data: UserUpdate) -> User:
        user = self.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        if update_data.email and update_data.email != user.email:
            if self.get_by_email(update_data.email):
                raise ConflictException("Email already in use")
            user.email = update_data.email

        if update_data.full_name:
            user.full_name = update_data.full_name

        self.db.commit()
        self.db.refresh(user)
        return user

    def change_password(self, user_id: str, password_data: ChangePassword) -> None:
        user = self.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        if not SecurityManager.verify_password(password_data.current_password, user.password_hash):
            raise UnauthorizedException("Current password is incorrect")

        user.password_hash = SecurityManager.hash_password(password_data.new_password)
        self.db.commit()

    def soft_delete(self, user_id: str) -> None:
        user = self.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        user.is_active = False
        self.db.commit()

    # ===================================================================
    # ROLE & PERMISSIONS
    # ===================================================================

    def get_user_with_role(self, user_id: str) -> Optional[Dict[str, Any]]:
        result = self.db.query(User, UserRole.role).join(
            UserRole, User.user_id == UserRole.user_id
        ).filter(
            User.user_id == user_id,
            User.is_active == True
        ).first()

        if not result:
            return None

        user, role = result
        return {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "role": role,
            "created_at": user.created_at
        }

    def get_user_role(self, user_id: str) -> Optional[str]:
        role = self.db.query(UserRole.role).filter(
            UserRole.user_id == user_id
        ).scalar()
        return role

    # ===================================================================
    # LIST & SEARCH
    # ===================================================================

    def list_users(
        self,
        role: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> List[Dict[str, Any]]:
        query = self.db.query(User).join(UserRole).filter(User.is_active == True)

        if role:
            query = query.filter(UserRole.role == role)

        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(User.email).like(search_term),
                    func.lower(User.full_name).like(search_term)
                )
            )

        query = query.order_by(User.created_at.desc())

        total = query.count()
        users = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "data": [
                {
                    "user_id": u.user_id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": self.get_user_role(u.user_id),
                    "created_at": u.created_at
                }
                for u in users
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page
            }
        }

    # ===================================================================
    # UTILITIES
    # ===================================================================

    def _generate_student_code(self) -> str:
        """Generate unique student code like S2025001"""
        import random
        year = "2025"
        while True:
            code = f"S{year}{random.randint(1, 9999):04d}"
            if not self.db.query(Student).filter(Student.student_code == code).first():
                return code

    def count_by_role(self, role: str) -> int:
        return self.db.query(UserRole).filter(UserRole.role == role).count()