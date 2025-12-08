"""Dashboard API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.core.database import get_db
from app.models import Alert, Repository, AlertAnalysis
from app.api.schemas import DashboardStats, AlertResponse
from app.api.deps import CurrentUser


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Get dashboard statistics for current user."""
    # Get user's repository IDs as a proper select subquery
    repo_ids = select(Repository.id).filter(
        Repository.user_id == current_user.id
    ).scalar_subquery()
    
    # Total alerts
    total_alerts = db.query(func.count(Alert.id)).filter(
        Alert.repository_id.in_(repo_ids)
    ).scalar() or 0
    
    # Alerts by severity
    severity_counts = db.query(
        Alert.severity,
        func.count(Alert.id)
    ).filter(
        Alert.repository_id.in_(repo_ids)
    ).group_by(Alert.severity).all()
    
    # Alerts by state
    state_counts = db.query(
        Alert.state,
        func.count(Alert.id)
    ).filter(
        Alert.repository_id.in_(repo_ids)
    ).group_by(Alert.state).all()
    
    # Alerts by ecosystem
    ecosystem_counts = db.query(
        Alert.package_ecosystem,
        func.count(Alert.id)
    ).filter(
        Alert.repository_id.in_(repo_ids)
    ).group_by(Alert.package_ecosystem).all()
    
    # Recent alerts
    recent_alerts = db.query(Alert).join(Repository).filter(
        Alert.repository_id.in_(repo_ids)
    ).order_by(Alert.created_at.desc()).limit(5).all()
    
    # Add repository full_name to each alert
    for alert in recent_alerts:
        alert.repository_full_name = alert.repository.full_name
    
    # Monitored repositories
    repos_monitored = db.query(func.count(Repository.id)).filter(
        Repository.user_id == current_user.id,
        Repository.is_monitored == True
    ).scalar() or 0
    
    # Total analyses
    total_analyses = db.query(func.count(AlertAnalysis.id)).join(Alert).filter(
        Alert.repository_id.in_(repo_ids),
        AlertAnalysis.status == "completed"
    ).scalar() or 0
    
    return DashboardStats(
        total_alerts=total_alerts,
        alerts_by_severity=dict(severity_counts),
        alerts_by_state=dict(state_counts),
        alerts_by_ecosystem=dict(ecosystem_counts),
        recent_alerts=[AlertResponse.model_validate(a) for a in recent_alerts],
        repositories_monitored=repos_monitored,
        total_analyses=total_analyses,
    )


@router.get("/trends")
async def get_trends(
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Get alert trends over time."""
    # TODO: Implement trend analysis
    return {
        "message": "Trends endpoint - implement with time-series data"
    }


@router.get("/recent-activity")
async def get_recent_activity(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    limit: int = 10
):
    """Get recent activity for current user."""
    # Get user's repository IDs
    repo_ids = db.query(Repository.id).filter(
        Repository.user_id == current_user.id
    ).subquery()
    
    # Recent analyses
    recent_analyses = db.query(AlertAnalysis).join(Alert).filter(
        Alert.repository_id.in_(repo_ids)
    ).order_by(AlertAnalysis.created_at.desc()).limit(limit).all()
    
    activity = []
    for analysis in recent_analyses:
        activity.append({
            "type": "analysis",
            "id": analysis.id,
            "alert_id": analysis.alert_id,
            "status": analysis.status,
            "provider": analysis.llm_provider,
            "model": analysis.llm_model,
            "created_at": analysis.created_at.isoformat(),
        })
    
    return {"activity": activity}
