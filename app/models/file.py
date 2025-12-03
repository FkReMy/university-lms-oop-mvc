"""
app/models/file.py
Enterprise-grade file management system
Supports:
- PDF, Word, Images, ZIP
- Virus scan ready
- Presigned URLs ready (S3/MinIO)
- Full audit trail (who uploaded, when)
- Used by assignments, quizzes, feedback
"""

from __future__ import annotations

from typing import Optional
from sqlalchemy import (
    String, BigInteger, DateTime, Boolean, ForeignKey, Enum, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel
from app.models.user import User


class UploadedFile(BaseModel):
    __tablename__ = "uploaded_files"

    file_id: Mapped[str_pk]
    
    # Who uploaded
    uploaded_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.user_id"), nullable=False, index=True
    )
    uploaded_by_role: Mapped[str] = mapped_column(String(20), nullable=False)

    # File metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)  # For display
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Storage
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    
    # Security & status
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    virus_scan_status: Mapped[str] = mapped_column(
        Enum("pending", "clean", "infected", "failed", name="virus_status"),
        default="pending"
    )
    
    # Audit
    uploaded_at: Mapped[created_at_col]
    expires_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    uploader: Mapped["User"] = relationship("User", back_populates="uploaded_files")

    # Optional: reverse relationships (not mapped here to avoid circular imports)
    # Used in other models like Assignment.reference_file, Quiz.instructions_file, etc.

    def get_download_url(self) -> str:
        """Return public or presigned URL"""
        return self.url

    def is_image(self) -> bool:
        return self.mime_type.startswith("image/")

    def is_document(self) -> bool:
        return self.mime_type in {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain"
        }

    def __repr__(self) -> str:
        return f"<File {self.filename} ({self.file_size} bytes)>"

    class FileType:
        DOCUMENT = "document"
        IMAGE = "image"
        ARCHIVE = "archive"
        OTHER = "other"

    @property
    def file_type(self) -> str:
        if self.is_image():
            return self.FileType.IMAGE
        elif self.is_document():
            return self.FileType.DOCUMENT
        elif "zip" in self.mime_type or "rar" in self.mime_type:
            return self.FileType.ARCHIVE
        else:
            return self.FileType.OTHER