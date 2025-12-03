"""
app/repositories/file_repository.py
Complete Repository Pattern for File Management
Handles:
- Secure file metadata storage
- Virus scan status tracking
- Soft delete & expiration
- Search, filter, pagination
- Used by quizzes, assignments, feedback
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc

from app.models.file import UploadedFile
from app.models.user import User
from app.schemas.common import PaginationParams
from app.utils.exceptions import NotFoundException, ForbiddenException


class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    # ===================================================================
    # CORE FILE OPERATIONS
    # ===================================================================

    def create_file(
        self,
        uploaded_by: str,
        uploaded_by_role: str,
        filename: str,
        original_filename: str,
        file_size: int,
        mime_type: str,
        storage_path: str,
        url: str,
        is_public: bool = False,
        expires_at: Optional[datetime] = None
    ) -> UploadedFile:
        """Create file record after successful upload"""
        file_record = UploadedFile(
            uploaded_by=uploaded_by,
            uploaded_by_role=uploaded_by_role,
            filename=filename,
            original_filename=original_filename,
            file_size=file_size,
            mime_type=mime_type,
            storage_path=storage_path,
            url=url,
            is_public=is_public,
            expires_at=expires_at,
            virus_scan_status="pending"
        )
        self.db.add(file_record)
        self.db.flush()
        return file_record

    def get_file_by_id(self, file_id: str, include_uploader: bool = True) -> Optional[UploadedFile]:
        query = self.db.query(UploadedFile).filter(
            UploadedFile.file_id == file_id,
            UploadedFile.is_active == True
        )
        if include_uploader:
            query = query.options(joinedload(UploadedFile.uploader))
        return query.first()

    def get_file_by_path(self, storage_path: str) -> Optional[UploadedFile]:
        return self.db.query(UploadedFile).filter(
            UploadedFile.storage_path == storage_path,
            UploadedFile.is_active == True
        ).first()

    def mark_virus_clean(self, file_id: str) -> None:
        file = self.get_file_by_id(file_id)
        if not file:
            raise NotFoundException("File not found")
        file.virus_scan_status = "clean"
        self.db.flush()

    def mark_virus_infected(self, file_id: str) -> None:
        file = self.get_file_by_id(file_id)
        if not file:
            raise NotFoundException("File not found")
        file.virus_scan_status = "infected"
        file.is_active = False  # Auto-quarantine
        self.db.flush()

    def update_file_status(self, file_id: str, status: str) -> None:
        valid_statuses = ["pending", "clean", "infected", "failed"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")
        
        file = self.get_file_by_id(file_id)
        if not file:
            raise NotFoundException("File not found")
        file.virus_scan_status = status
        self.db.flush()

    def soft_delete_file(self, file_id: str, deleter_id: str) -> None:
        file = self.get_file_by_id(file_id)
        if not file:
            raise NotFoundException("File not found")
        
        # Optional: check ownership or admin
        if file.uploaded_by != deleter_id:
            # You can add admin check here
            pass
        
        file.is_active = False
        self.db.flush()

    # ===================================================================
    # SEARCH & FILTER
    # ===================================================================

    def list_files(
        self,
        uploaded_by: Optional[str] = None,
        mime_type: Optional[str] = None,
        virus_status: Optional[str] = None,
        is_public: Optional[bool] = None,
        search: Optional[str] = None,
        pagination: Optional[PaginationParams] = None
    ) -> Dict[str, Any]:
        query = self.db.query(UploadedFile).filter(UploadedFile.is_active == True)

        if uploaded_by:
            query = query.filter(UploadedFile.uploaded_by == uploaded_by)
        if mime_type:
            query = query.filter(UploadedFile.mime_type.startswith(mime_type.split("/")[0]))
        if virus_status:
            query = query.filter(UploadedFile.virus_scan_status == virus_status)
        if is_public is not None:
            query = query.filter(UploadedFile.is_public == is_public)
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(UploadedFile.filename).like(search_term),
                    func.lower(UploadedFile.original_filename).like(search_term)
                )
            )

        # Default sort
        query = query.order_by(desc(UploadedFile.uploaded_at))

        total = query.count()

        if pagination:
            query = query.offset((pagination.page - 1) * pagination.per_page).limit(pagination.per_page)

        files = query.all()

        return {
            "data": [f.to_dict() for f in files],
            "pagination": {
                "page": pagination.page if pagination else 1,
                "per_page": pagination.per_page if pagination else 20,
                "total": total,
                "total_pages": (total + (pagination.per_page if pagination else 20) - 1) // (pagination.per_page if pagination else 20)
            }
        }

    def get_user_files(
        self,
        user_id: str,
        file_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        return self.list_files(
            uploaded_by=user_id,
            mime_type=file_type,
            pagination=PaginationParams(page=page, per_page=per_page)
        )

    def get_expired_files(self, days_old: int = 90) -> List[UploadedFile]:
        """Find files with expiration date passed"""
        expiry_date = datetime.utcnow() - timedelta(days=days_old)
        return self.db.query(UploadedFile).filter(
            UploadedFile.expires_at < datetime.utcnow(),
            UploadedFile.is_active == True
        ).all()

    def get_files_needing_scan(self) -> List[UploadedFile]:
        return self.db.query(UploadedFile).filter(
            UploadedFile.virus_scan_status == "pending",
            UploadedFile.is_active == True
        ).all()

    # ===================================================================
    # STATISTICS
    # ===================================================================

    def get_storage_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        query = self.db.query(
            func.count(UploadedFile.file_id).label("total_files"),
            func.coalesce(func.sum(UploadedFile.file_size), 0).label("total_size"),
            func.count(case((UploadedFile.virus_scan_status == "clean", 1))).label("clean"),
            func.count(case((UploadedFile.virus_scan_status == "infected", 1))).label("infected")
        ).filter(UploadedFile.is_active == True)

        if user_id:
            query = query.filter(UploadedFile.uploaded_by == user_id)

        result = query.first()

        return {
            "total_files": result.total_files or 0,
            "total_size_bytes": result.total_size or 0,
            "total_size_mb": round((result.total_size or 0) / (1024 * 1024), 2),
            "clean_files": result.clean or 0,
            "infected_files": result.infected or 0,
            "pending_scan": (result.total_files or 0) - (result.clean or 0) - (result.infected or 0)
        }