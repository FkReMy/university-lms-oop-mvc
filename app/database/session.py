"""
app/database/session.py
Database engine, session factory and scoped session management
Clean, production-ready, fully compatible with FastAPI Depends()
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app.core.config import settings
import logging

# Configure logging for connection issues
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Create the SQLAlchemy engine
# ------------------------------------------------------------------
engine = create_engine(
    url=settings.DATABASE_URL,
    pool_pre_ping=True,           # Detects broken connections
    pool_size=20,                 # Max concurrent connections
    max_overflow=40,              # Allow temporary overflow
    pool_timeout=30,              # Wait up to 30s for a connection
    echo=False,                   # Set to True only in deep debugging
    future=True,                  # Enables SQLAlchemy 2.0 behavior
    connect_args={
        "connect_timeout": 10,
        # PostgreSQL-specific options (optional but recommended)
        "application_name": "university-lms-api"
    }
)

# ------------------------------------------------------------------
# Session factory
# ------------------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,       # Prevents attribute expiration after commit
    class_=scoped_session         # Thread-local sessions (safe in async/uvicorn)
)

# ------------------------------------------------------------------
# Dependency for FastAPI – yields a session and always closes it
# ------------------------------------------------------------------
def get_db():
    """
    FastAPI dependency: provides a database session per request
    Usage in routers:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        # Optional: test connection on first use
        db.execute("SELECT 1")
        yield db
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# ------------------------------------------------------------------
# Optional: Direct session for scripts, tests, or background tasks
# ------------------------------------------------------------------
def get_session() -> SessionLocal:
    """
    Returns a new session (use in Celery, scripts, migrations, etc.)
    Remember to close it manually!
    """
    return SessionLocal()