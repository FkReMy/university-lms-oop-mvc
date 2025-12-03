"""
University LMS – Full OOP + MVC + Clean Architecture
FastAPI entry point
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import all controllers (API routers)
from app.controllers import (
    auth_controller,
    user_controller,
    course_controller,
    quiz_controller,
    assignment_controller,
    file_controller,
)

# Import database models to create tables on startup
from app.database.base import Base
from app.database.session import engine

# Create upload directory if not exists
os.makedirs("static/uploads", exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title="University LMS API",
    description="Enterprise-grade Learning Management System – 2025 Edition",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (uploaded PDFs, Word docs, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include all API routers
app.include_router(auth_controller.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(user_controller.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(course_controller.router, prefix="/api/v1/courses", tags=["Courses"])
app.include_router(quiz_controller.router, prefix="/api/v1/quizzes", tags=["Quizzes"])
app.include_router(assignment_controller.router, prefix="/api/v1/assignments", tags=["Assignments"])
app.include_router(file_controller.router, prefix="/api/v1/files", tags=["File Uploads"])

# Database tables creation on startup
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified successfully!")

# Health check endpoint
@app.get("/")
def read_root():
    return {
        "message": "University LMS Backend is running!",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "active"
    }

# Optional: Graceful shutdown
@app.on_event("shutdown")
def shutdown_event():
    print("University LMS API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)