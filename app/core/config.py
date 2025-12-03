"""
app/core/config.py
Configuration management using Pydantic Settings (v2)
Supports .env file, environment variables, and type safety
"""

import os
from functools import lru_cache
from typing import Literal, List, Set, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # =================================================================
    # Database
    # =================================================================
    DATABASE_URL: str = "postgresql+psycopg2://postgres:secret@localhost:5432/lms"
    
    # =================================================================
    # JWT & Security
    # =================================================================
    SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production-2025"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # =================================================================
    # File Upload
    # =================================================================
    UPLOAD_DIR: str = "static/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: Set[str] = {
        ".pdf", ".docx", ".doc", ".txt", ".jpg", ".jpeg", ".png", ".zip"
    }

    # =================================================================
    # App Environment
    # =================================================================
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True

    # =================================================================
    # CORS
    # =================================================================
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # =================================================================
    # Email
    # =================================================================
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "no-reply@university.edu"

    # =================================================================
    # Validators (Fix for .env comma-separated lists)
    # =================================================================
    @field_validator("ALLOWED_ORIGINS", "ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_comma_separated_list(cls, v: Union[str, List[str], Set[str]]) -> Union[List[str], Set[str]]:
        """
        Parses comma-separated strings from .env into lists/sets.
        Example: "http://a.com,http://b.com" -> ["http://a.com", "http://b.com"]
        """
        if isinstance(v, str) and not v.strip().startswith("["):
            return [item.strip() for item in v.split(",")]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance – safe for multiple imports
    """
    return Settings()

# Create singleton instance
settings = get_settings()

# Auto-create upload directory
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
