"""API module."""
from app.api.routes import (
    auth_router,
    llm_config_router,
    repositories_router,
    alerts_router,
    dashboard_router,
)
from app.api.routes.mock import router as mock_router

__all__ = [
    "auth_router",
    "llm_config_router",
    "repositories_router",
    "alerts_router",
    "dashboard_router",
    "mock_router",
]
