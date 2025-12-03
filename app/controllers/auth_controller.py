"""
app/controllers/auth_controller.py
FastAPI Authentication Routes – Login, Register, Profile, Password Management
100% Secure, Clean, and Beautiful
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_active_user
from app.services.auth_service import AuthService
from app.schemas.user import (
    UserCreate, UserLogin, Token, UserProfile,
    ChangePassword, UserResponse, LoginResponse
)
from app.schemas.common import MessageResponse

router = APIRouter()


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register new user (Student by default)
    Admin can override role via internal endpoint
    """
    auth_service = AuthService(db)
    result = auth_service.register(user_data, role="Student")
    
    return LoginResponse(
        success=True,
        message="Registration successful",
        token=result["token"],
        user=result["user"]
    )


@router.post("/login", response_model=LoginResponse)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with email + password → returns JWT + user profile
    """
    auth_service = AuthService(db)
    result = auth_service.login(credentials)
    
    return LoginResponse(
        success=True,
        message=result["message"],
        token=result["token"],
        user=result["user"]
    )


@router.post("/login/form", response_model=LoginResponse)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible login (for Swagger UI)
    """
    credentials = UserLogin(email=form_data.username, password=form_data.password)
    auth_service = AuthService(db)
    result = auth_service.login(credentials)
    
    return LoginResponse(
        success=True,
        message=result["message"],
        token=result["token"],
        user=result["user"]
    )


@router.get("/me", response_model=UserResponse)
def get_profile(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user profile
    """
    auth_service = AuthService(db)
    profile = auth_service.get_current_user_profile(current_user["user_id"])
    
    return UserResponse(
        success=True,
        message="Profile retrieved",
        data=profile
    )


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    password_data: ChangePassword,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password
    """
    auth_service = AuthService(db)
    auth_service.change_password(current_user["user_id"], password_data)
    
    return MessageResponse(success=True, message="Password changed successfully")


@router.post("/refresh", response_model=Token)
def refresh_token(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate new access token
    """
    auth_service = AuthService(db)
    token = auth_service.refresh_token(current_user["user_id"], current_user["role"])
    return token


@router.post("/logout", response_model=MessageResponse)
def logout(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Logout (token blacklist in production)
    """
    auth_service = AuthService(db)
    auth_service.logout(current_user["user_id"])
    return MessageResponse(success=True, message="Logged out successfully")


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Request password reset link
    """
    auth_service = AuthService(db)
    result = auth_service.request_password_reset(email)
    return MessageResponse(success=True, message=result["message"])


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """
    Reset password using token
    """
    auth_service = AuthService(db)
    result = auth_service.reset_password(token, new_password)
    return MessageResponse(success=True, message=result["message"])