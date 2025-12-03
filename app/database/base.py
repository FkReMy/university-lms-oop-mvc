"""
app/database/base.py
SQLAlchemy declarative base + shared configuration

All models inherit from Base
Handles:
- UUID primary keys (as string)
- Automatic timestamps
- Table naming conventions
- Future-proof metadata
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, func
from typing import Annotated
import uuid

# Create the base class that all models will inherit from
Base = declarative_base()

# === Reusable column types (OOP style) ===

# UUID as string (recommended for PostgreSQL + FastAPI)
str_uuid = Annotated[
    str,
    mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        unique=True,
        nullable=False,
    )
]

# Timestamps (created_at, updated_at)
created_at = Annotated[
    DateTime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
]

updated_at = Annotated[
    DateTime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
]

# Soft delete flag (optional future use)
is_active = Annotated[
    bool,
    mapped_column(default=True, nullable=False)
]

# Role column (used in compound keys)
role_str = Annotated[
    str,
    mapped_column(String(50), nullable=False)
]

# Example of how to use in models:
# class User(Base):
#     __tablename__ = "users"
#     user_id: Mapped[str_uuid]
#     email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
#     created_at: Mapped[created_at]

# Metadata configuration (optional but recommended)
Base.metadata.naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# Optional: For future reflection or migrations (Alembic)
# Base.registry.configure()