"""
app/models/base_model.py
Advanced base model class – all your SQLAlchemy models will inherit from this

Features:
- Automatic UUID v4 primary key (string)
- created_at / UPDATED_AT timestamps
- Soft delete (is_active)
- to_dict() method for easy serialization
- update() method for safe partial updates
- __repr__ and __str__ for debugging
- Hybrid properties ready
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Annotated  # <--- FIXED: Added Annotated here

from sqlalchemy import Column, String, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property

# Annotated types for reuse (SQLAlchemy 2.0 style)
str_pk = Annotated[
    str,
    mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        unique=True,
        nullable=False,
    )
]

created_at_col = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
]

updated_at_col = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
]

is_active_col = Annotated[
    bool,
    mapped_column(Boolean, default=True, nullable=False, index=True)
]

class BaseModel(DeclarativeBase):
    """
    All models inherit from this class
    Provides common fields and utility methods
    """
    # Enable future 2.0 behavior
    __future__ = True

    # Primary key (UUID string)
    id: Mapped[str_pk]

    # Timestamps
    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]

    # Soft delete
    is_active: Mapped[is_active_col]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.id}>"

    def __str__(self) -> str:
        return self.__repr__()

    def to_dict(self, exclude: Optional[set[str]] = None) -> Dict[str, Any]:
        """
        Convert model instance to dictionary
        Safe for JSON serialization (handles datetime, UUID)
        """
        if exclude is None:
            exclude = {"password_hash"}

        data = {}
        for column in self.__table__.columns:
            key = column.name
            if key in exclude:
                continue
            value = getattr(self, key)

            # Handle common types
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                data[key] = str(value)
            elif isinstance(value, (list, dict, set, tuple)):
                data[key] = str(value)  # or serialize recursively
            else:
                data[key] = value

        return data

    def update(self, **kwargs) -> None:
        """
        Safe partial update with validation
        Only updates fields that exist on the model
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = func.now()

    @hybrid_property
    def is_deleted(self) -> bool:
        return not self.is_active

    @is_deleted.setter
    def is_deleted(self, value: bool):
        self.is_active = not value

    def soft_delete(self) -> None:
        """Mark record as deleted without removing it"""
        self.is_active = False
        self.updated_at = func.now()

    def restore(self) -> None:
        """Restore a soft-deleted record"""
        self.is_active = True
        self.updated_at = func.now()
