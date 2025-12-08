"""API routes."""
from app.api.routes.auth import router as auth_router
from app.api.routes.llm_config import router as llm_config_router
from app.api.routes.repositories import router as repositories_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.workflows import router as workflows_router
from app.api.routes.analysis import router as analysis_router

__all__ = [
    "auth_router",
    "llm_config_router",
    "repositories_router",
    "alerts_router",
    "dashboard_router",
    "workflows_router",
    "analysis_router",
]
