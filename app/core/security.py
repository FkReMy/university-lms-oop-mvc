"""
app/core/security.py
Full security module:
- Multi-layer password hashing (Argon2 primary, SHA256 fallback, MD5 legacy)
- JWT token creation & verification
- OAuth2 password flow with FastAPI
- Current user dependency
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.session import get_db
from app.models.user import User, UserRole

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Password hashing context – Argon2 is primary
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt", "sha256_crypt"],
    deprecated="auto"
)

class SecurityManager:
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Multi-layer password hashing:
        1. Argon2 (best in class)
        2. SHA256 + salt (strong fallback)
        3. MD5 (legacy – only if others fail)
        """
        try:
            # Primary: Argon2
            return pwd_context.hash(password)
        except Exception:
            # Fallback 1: SHA256 with dynamic salt
            import hashlib
            import secrets
            salt = secrets.token_hex(16)
            hashed = hashlib.sha256((password + salt).encode()).hexdigest()
            return f"sha256${salt}${hashed}"
        # Final fallback (should never happen)
        # import hashlib
        # return hashlib.md5(password.encode()).hexdigest()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against multi-hash formats"""
        if hashed_password.startswith("sha256$"):
            # Custom SHA256 format: sha256$salt$hash
            parts = hashed_password.split("$")
            if len(parts) != 3:
                return False
            _, salt, stored_hash = parts
            computed = hashlib.sha256((plain_password + salt).encode()).hexdigest()
            return computed == stored_hash
        
        # Default: passlib handles Argon2, bcrypt, etc.
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            role: str = payload.get("role")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return {"user_id": user_id, "role": role}
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

# Dependency to get current authenticated user
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> dict:
    """
    Dependency: Returns current user with role
    Used in all protected routes
    """
    payload = SecurityManager.decode_token(token)
    user_id = payload["user_id"]

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Get user role
    user_role = db.query(UserRole).filter(UserRole.user_id == user_id).first()
    if not user_role:
        raise HTTPException(status_code=403, detail="User has no role assigned")

    return {
        "user_id": user.user_id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user_role.role
    }

# Dependency for role-based access
def require_role(allowed_roles: list[str]):
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: {allowed_roles}"
            )
        return current_user
    return role_checker

# Convenience roles
require_admin = require_role(["Admin"])
require_professor = require_role(["Professor", "AssociateTeacher"])
require_student = require_role(["Student"])
require_any_teacher = require_role(["Professor", "AssociateTeacher"])