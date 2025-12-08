"""Main FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api import (
    auth_router,
    llm_config_router,
    repositories_router,
    alerts_router,
    dashboard_router,
    workflows_router,
    mock_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️  Database connection failed: {e}")
        print("🔧 Running without database - some features will be limited")
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    description="Analyze GitHub Dependabot security alerts with LLM-powered insights",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(llm_config_router, prefix="/api")
app.include_router(repositories_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(workflows_router, prefix="/api")
app.include_router(mock_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "GitHub Alert Analyzer API",
        "docs": "/docs",
        "health": "/health",
    }
