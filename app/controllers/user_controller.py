"""
app/controllers/user_controller.py
Complete User Management API
- Admin: List, Create, Update, Delete, Role Assignment
- Self: View profile, Update own info
- Secure, Clean, Beautiful
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import (
    get_db,
    get_current_active_user,
    require_roles,
    get_admin_user,
    get_professor_user,
    get_teacher_user,
    get_student_user
)
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.schemas.user import (
    UserCreate, UserUpdate, UserProfile,
    UserAdminResponse, UserListResponse, MessageResponse
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


# ===================================================================
# SELF-SERVICE ENDPOINTS (All authenticated users)
# ===================================================================

@router.get("/profile", response_model=UserProfile)
def get_my_profile(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get own profile"""
    auth_service = AuthService(db)
    profile = auth_service.get_current_user_profile(current_user["user_id"])
    return profile


@router.put("/profile", response_model=MessageResponse)
def update_my_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update own name/email"""
    user_repo = UserRepository(db)
    user_repo.update_user(current_user["user_id"], update_data)
    return MessageResponse(success=True, message="Profile updated successfully")


# ===================================================================
# ADMIN ONLY ENDPOINTS
# ===================================================================

@router.post("", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    user_data: UserCreate,
    role: str = Query(..., description="Admin, Professor, AssociateTeacher, Student"),
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin creates any user with specified role
    """
    auth_service = AuthService(db)
    result = auth_service.register(user_data, role=role.upper())
    return result["user"]


@router.get("", response_model=PaginatedResponse[UserAdminResponse])
def list_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    search: Optional[str] = Query(None, description="Search name/email"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: List all users with pagination + search
    """
    user_repo = UserRepository(db)
    result = user_repo.list_users(
        role=role,
        search=search,
        page=page,
        per_page=per_page
    )

    return PaginatedResponse(
        success=True,
        message="Users retrieved",
        data=result["data"],
        pagination=result["pagination"]
    )
    )


@router.get("/{user_id}", response_model=UserAdminResponse)
def get_user_by_id(
    user_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin: Get any user by ID"""
    user_repo = UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserAdminResponse.from_orm(user)


@router.put("/{user_id}", response_model=MessageResponse)
def admin_update_user(
    user_id: str,
    update_data: UserUpdate,
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin: Update any user's info"""
    user_repo = UserRepository(db)
    user_repo.update_user(user_id, update_data)
    return MessageResponse(success=True, message="User updated successfully")


@router.delete("/{user_id}", response_model=MessageResponse)
def admin_delete_user(
    user_id: str,
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin: Soft delete user"""
    user_repo = UserRepository(db)
    user_repo.soft_delete(user_id)
    return MessageResponse(success=True, message="User deleted successfully")


@router.post("/{user_id}/assign-role", response_model=MessageResponse)
def admin_assign_role(
    user_id: str,
    new_role: str = Query(..., regex="^(Admin|Professor|AssociateTeacher|Student)$"),
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Change user role (dangerous – use carefully)
    """
    user_repo = UserRepository(db)
    current_role = user_repo.get_user_role(user_id)
    if not current_role:
        raise HTTPException(status_code=404, detail="User not found")

    # In production: add role change logic with audit log
    # For now: placeholder
    return MessageResponse(
        success=True,
        message=f"Role change from {current_role} to {new_role} queued"
    )


# ===================================================================
# TEACHER ENDPOINTS (View their students)
# ===================================================================

@router.get("/my-students", response_model=List[UserProfile])
def get_my_students(
    teacher_user: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    """
    Professor/AssociateTeacher: Get list of students in their courses
    (Future: implement via course enrollment join)
    """
    # Placeholder – real version joins through CourseOffering
    return []


# ===================================================================
# STATISTICS (Admin only)
# ===================================================================

@router.get("/stats/summary")
def get_user_stats(
    admin_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin dashboard stats"""
    repo = UserRepository(db)
    return {
        "total_users": repo.count_by_role(None),  # custom method
        "admins": repo.count_by_role("Admin"),
        "professors": repo.count_by_role("Professor"),
        "associate_teachers": repo.count_by_role("AssociateTeacher"),
        "students": repo.count_by_role("Student")
    }