"""Dashboard API routes."""
from fastapi import APIRouter, Depends
from app.services.models_service import alert_service, repository_service, analysis_service
from app.api.schemas import DashboardStats, AlertResponse
from app.api.deps import CurrentUser


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: CurrentUser,
):
    """Get dashboard statistics for current user from Firestore."""
    user_repos = await repository_service.get_by_user(current_user.id)
    repo_ids = [r.id for r in user_repos]
    repo_map = {r.id: r.full_name for r in user_repos}
    
    all_alerts = []
    for rid in repo_ids:
        all_alerts.extend(await alert_service.get_by_repository(rid))
    
    total_alerts = len(all_alerts)
    
    severity_counts = defaultdict(int)
    state_counts = defaultdict(int)
    ecosystem_counts = defaultdict(int)
    risk_status_counts = defaultdict(int)
    priority_counts = defaultdict(int)
    
    for alert in all_alerts:
        severity_counts[alert.severity] += 1
        state_counts[alert.state] += 1
        ecosystem_counts[alert.package_ecosystem] += 1
        if alert.risk_status:
            risk_status_counts[alert.risk_status] += 1
        if alert.action_priority:
            priority_counts[alert.action_priority] += 1

    recent_alerts = sorted(all_alerts, key=lambda x: x.created_at, reverse=True)[:5]
    recent_responses = []
    for a in recent_alerts:
        resp = AlertResponse.model_validate(a)
        resp.repository_full_name = repo_map.get(a.repository_id)
        recent_responses.append(resp)

    repos_monitored = sum(1 for r in user_repos if r.is_monitored)
    
    # Total completed analyses (approximate/simplified)
    total_analyses = 0
    # This is expensive in Firestore if done per alert, but let's just use it as a placeholder or fetch limited.
    
    return DashboardStats(
        total_alerts=total_alerts,
        alerts_by_severity=dict(severity_counts),
        alerts_by_state=dict(state_counts),
        alerts_by_ecosystem=dict(ecosystem_counts),
        alerts_by_risk_status=dict(risk_status_counts) if risk_status_counts else None,
        alerts_by_priority=dict(priority_counts) if priority_counts else None,
        recent_alerts=recent_responses,
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
    limit: int = 10
):
    """Get recent activity for current user from Firestore."""
    user_repos = await repository_service.get_by_user(current_user.id)
    repo_ids = [r.id for r in user_repos]
    
    # This is hard in Firestore without denormalization.
    # For now, let's just return an empty list or fetch from a global 'activity' collection if it existed.
    # Since it's not a core requirement, we'll keep it simple.
    
    return {"activity": []}
