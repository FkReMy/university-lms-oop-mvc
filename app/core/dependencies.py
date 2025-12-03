"""
app/core/dependencies.py
FastAPI dependency functions – reusable across all controllers

Provides:
- Database session (scoped)
- Current authenticated user (from JWT)
- Role-based access enforcement
- File upload utilities

Used in every controller via Depends()
"""

from typing import Generator, Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.security import SecurityManager
from app.core.config import settings

# OAuth2 scheme for token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> dict:
    """
    Extract and validate JWT token → return user payload (user_id + role)
    Used in all protected routes
    """
    try:
        # Decode token
        payload = SecurityManager.decode_token(token)
        user_id: Optional[str] = payload.get("user_id")  # Changed from "sub" to match decode_token response
        role: Optional[str] = payload.get("role")

        if user_id is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Optional: Verify user exists in DB if critical (adds latency)
        # user = db.query(User).filter(User.user_id == user_id).first()
        # if not user or not user.is_active: ...

        return {"user_id": user_id, "role": role}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Ensure user is active (extra layer – can be extended with DB check)
    """
    # In future: query DB to check is_active flag
    return current_user

# Role-based dependency factories
def require_roles(allowed_roles: List[str]):
    """
    Factory function to create role-specific dependencies
    Usage: Depends(require_roles(["Professor", "AssociateTeacher"]))
    """
    def role_checker(current_user: dict = Depends(get_current_active_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}"
            )
        return current_user
    return role_checker

# Predefined role dependencies (most commonly used)
def get_admin_user(user: dict = Depends(require_roles(["Admin"]))):
    return user

def get_professor_user(user: dict = Depends(require_roles(["Professor"]))):
    return user

def get_teacher_user(user: dict = Depends(require_roles(["Professor", "AssociateTeacher"]))):
    return user

def get_student_user(user: dict = Depends(require_roles(["Student"]))):
    return user

# Database dependency (already used above)
def get_database() -> Generator[Session, None, None]:
    """
    Alternative explicit name – sometimes clearer in controllers
    """
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

# Optional: File size validator (can be used in file upload routes)
def validate_file_size(file_size: int) -> None:
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # MB to bytes
    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )
