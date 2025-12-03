"""
University LMS – Full OOP + MVC + Clean Architecture
FastAPI entry point
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import settings to ensure config is loaded
from app.core.config import settings

# Import database models to create tables on startup
from app.database.base import Base
from app.database.session import engine

# Import all controllers (API routers)
from app.controllers import (
    auth_controller,
    user_controller,
    quiz_controller,
    assignment_controller,
    # course_controller,  # TODO: Create this file (Missing in upload)
    # file_controller,    # TODO: Create this file (Missing in upload)
)

# =============================================================================
# LIFESPAN MANAGER (Modern Startup/Shutdown)
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events.
    Replaces deprecated @app.on_event("startup")
    """
    # --- Startup ---
    print("University LMS API starting up...")
    
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Create DB tables (In production, use Alembic migrations instead)
    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified successfully!")
    
    yield
    
    # --- Shutdown ---
    print("University LMS API shutting down...")

# =============================================================================
# APP INITIALIZATION
# =============================================================================
app = FastAPI(
    title=settings.APP_NAME if hasattr(settings, 'APP_NAME') else "University LMS API",
    description="Enterprise-grade Learning Management System – 2025 Edition",
    version=settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# =============================================================================
# MIDDLEWARE
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# STATIC FILES
# =============================================================================
# Ensure directory exists before mounting to prevent crash
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# =============================================================================
# ROUTERS
# =============================================================================
app.include_router(auth_controller.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(user_controller.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(quiz_controller.router, prefix="/api/v1/quizzes", tags=["Quizzes"])
app.include_router(assignment_controller.router, prefix="/api/v1/assignments", tags=["Assignments"])

# TODO: Uncomment these once the files are created
# app.include_router(course_controller.router, prefix="/api/v1/courses", tags=["Courses"])
# app.include_router(file_controller.router, prefix="/api/v1/files", tags=["File Uploads"])

# =============================================================================
# HEALTH CHECK
# =============================================================================
@app.get("/", tags=["Health"])
def read_root():
    return {
        "message": "University LMS Backend is running!",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "active"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
