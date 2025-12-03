"""
app/schemas/user.py
Pydantic DTOs for User, Role, Registration, Login, Profile
Used in FastAPI responses & request validation
"""

from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
import re

# =============================================================================
# BASE SCHEMAS
# =============================================================================

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    
    class Config:
        from_attributes = True  # Allows .dict(model) and response_model


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    confirm_password: str
    
    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v
    
    @validator("password")
    def strong_password(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain a number")
        if not re.search(r"[!@#$%^&*]", v):
            raise ValueError("Password must contain special character")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 60 * 60 * 24 * 7  # 7 days


class TokenData(BaseModel):
    user_id: str
    role: str
    exp: datetime


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class RoleInfo(BaseModel):
    role: str
    assigned_at: datetime
    
    class Config:
        from_attributes = True


class UserProfile(UserBase):
    user_id: str
    created_at: datetime
    is_active: bool
    role: RoleInfo


class UserInDB(UserProfile):
    """For internal use – includes password hash (never returned in API)"""
    password_hash: str


class UserResponse(BaseModel):
    success: bool = True
    message: str
    data: UserProfile


class LoginResponse(BaseModel):
    success: bool = True
    message: str = "Login successful"
    token: Token
    user: UserProfile


# =============================================================================
# UPDATE SCHEMAS
# =============================================================================

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    
    @validator("email")
    def email_not_empty(cls, v):
        if v == "":
            raise ValueError("Email cannot be empty")
        return v


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v


# =============================================================================
# ADMIN SCHEMAS
# =============================================================================

class UserAdminResponse(UserProfile):
    last_login: Optional[datetime] = None


class UserListResponse(BaseModel):
    success: bool = True
    total: int
    users: List[UserAdminResponse]