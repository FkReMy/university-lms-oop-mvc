"""
app/schemas/common.py
Shared response models, pagination, errors, and utilities
Used across all modules for consistent API design
"""

from __future__ import annotations

from typing import Generic, TypeVar, Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

# Generic type for pagination
T = TypeVar("T")


# =============================================================================
# STANDARD SUCCESS / ERROR RESPONSES
# =============================================================================

class APIResponse(BaseModel):
    success: bool = True
    message: str = "Operation completed successfully"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: Optional[str] = None


class ErrorDetail(BaseModel):
    code: str
    detail: str
    field: Optional[str] = None


class ErrorResponse(APIResponse):
    success: bool = False
    error: ErrorDetail


# =============================================================================
# PAGINATION (used everywhere)
# =============================================================================

class PaginatedResponse(GenericModel, Generic[T]):
    success: bool = True
    message: str = "Data retrieved successfully"
    data: List[T]
    pagination: dict = Field(
        ...,
        example={
            "page": 1,
            "per_page": 20,
            "total": 157,
            "total_pages": 8,
            "has_next": True,
            "has_prev": False
        }
    )


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")


# =============================================================================
# FILE RESPONSES
# =============================================================================

class FileUploadResponse(BaseModel):
    success: bool = True
    message: str = "File uploaded successfully"
    file_id: str
    filename: str
    file_url: str
    file_size: int
    mime_type: str  # document, image, archive
    uploaded_at: datetime


class FileInfo(BaseModel):
    file_id: str
    filename: str
    file_url: str
    file_size: int
    mime_type: str
    uploaded_by_name: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# COMMON ENUM-LIKE RESPONSES
# =============================================================================

class HealthCheck(BaseModel):
    status: str = "healthy"
    service: str = "University LMS API"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MessageResponse(BaseModel):
    success: bool = True
    message: str


# =============================================================================
# SORTING & FILTERING
# =============================================================================

class SortOrder(str):
    ASC = "asc"
    DESC = "desc"


class SortableField(BaseModel):
    field: str = Field(..., description="Database column name")
    order: SortOrder = SortOrder.ASC


# =============================================================================
# NOTIFICATION / ACTIVITY
# =============================================================================

class Notification(BaseModel):
    id: str
    title: str
    message: str
    type: str  # info, warning, success, error
    read: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# STATISTICS
# =============================================================================

class StatsSummary(BaseModel):
    total_students: int
    total_courses: int
    active_quizzes: int
    pending_grades: int


# =============================================================================
# EXPORT / IMPORT
# =============================================================================

class ExportResponse(BaseModel):
    success: bool = True
    message: str = "Export generated"
    download_url: str
    filename: str
    expires_at: datetime


# =============================================================================
# REUSABLE FIELDS
# =============================================================================

class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime


class OwnedMixin(BaseModel):
    created_by_id: str
    created_by_name: str
    created_by_role: str


class SoftDeleteMixin(BaseModel):
    is_active: bool
    deleted_at: Optional[datetime] = None