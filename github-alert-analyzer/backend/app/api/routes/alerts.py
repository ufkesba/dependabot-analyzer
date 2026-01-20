"""Alert API routes."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.services.models_service import alert_service, repository_service, analysis_service
from app.api.schemas import (
    AlertResponse,
    AlertDetailResponse,
    AlertListResponse,
    AlertAnalysisResponse,
    AnalyzeAlertRequest,
    BulkAnalyzeRequest,
    DashboardStats,
)
from app.api.deps import CurrentUser


router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=1000),
    repository_id: Optional[str] = None,
    severity: Optional[List[str]] = Query(None),
    state: Optional[List[str]] = Query(None),
    package_ecosystem: Optional[str] = None,
    has_analysis: Optional[bool] = None,
    search: Optional[str] = None,
):
    """List all alerts for current user's repositories from Firestore."""
    # This is complex in Firestore due to cross-collection join (Repository -> Alert)
    # For now, we fetch user's repositories first.
    user_repos = await repository_service.get_by_user(current_user.id)
    repo_ids = [r.id for r in user_repos]
    
    if repository_id:
        if repository_id not in repo_ids:
            return AlertListResponse(items=[], total=0, page=page, per_page=per_page, pages=0)
        repo_ids = [repository_id]

    # Firestore doesn't support 'in' with more than 30 values easily,
    # but let's assume a reasonable number of repos for now.
    all_alerts = []
    for rid in repo_ids:
        filters = [("repository_id", "==", rid)]
        if package_ecosystem:
            filters.append(("package_ecosystem", "==", package_ecosystem))

        repo_alerts = await alert_service.list(filters=filters)
        all_alerts.extend(repo_alerts)

    # In-memory filtering for more complex criteria
    if severity:
        all_alerts = [a for a in all_alerts if a.severity in severity]
    if state:
        all_alerts = [a for a in all_alerts if a.state in state]
    if search:
        all_alerts = [a for a in all_alerts if search.lower() in a.package_name.lower()]
    
    # Sort and paginate
    all_alerts.sort(key=lambda x: x.created_at, reverse=True)
    total = len(all_alerts)
    start = (page - 1) * per_page
    end = start + per_page
    paged_alerts = all_alerts[start:end]
    
    pages = (total + per_page - 1) // per_page
    
    # Enrich with latest analysis and repo info
    repo_map = {r.id: r.full_name for r in user_repos}
    alert_responses = []
    for alert in paged_alerts:
        alert_dict = AlertResponse.model_validate(alert).model_dump()
        alert_dict["repository_full_name"] = repo_map.get(alert.repository_id)
        
        analyses = await analysis_service.get_by_alert(alert.id)
        completed_analyses = [a for a in analyses if a.status == "completed"]
        if completed_analyses:
            latest = sorted(completed_analyses, key=lambda x: x.created_at, reverse=True)[0]
            alert_dict["latest_analysis"] = AlertAnalysisResponse.model_validate(latest)
        
        alert_responses.append(AlertResponse(**alert_dict))
    
    return AlertListResponse(
        items=alert_responses,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{alert_id}", response_model=AlertDetailResponse)
async def get_alert(
    alert_id: str,
    current_user: CurrentUser,
):
    """Get a specific alert with all its analyses from Firestore."""
    alert = await alert_service.get(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Verify ownership
    repo = await repository_service.get(alert.repository_id)
    if not repo or repo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    analyses = await analysis_service.get_by_alert(alert_id)

    response = AlertDetailResponse.model_validate(alert)
    response.repository_full_name = repo.full_name
    response.analyses = [AlertAnalysisResponse.model_validate(a) for a in analyses]
    
    return response


@router.post("/{alert_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_alert(
    alert_id: str,
    request: AnalyzeAlertRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Request LLM analysis for an alert."""
    alert = db.query(Alert).join(Repository).filter(
        Alert.id == alert_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # TODO: Queue analysis job with Celery
    # For now, create a pending analysis record
    analysis = AlertAnalysis(
        alert_id=alert_id,
        llm_config_id=request.llm_config_id,
        llm_provider="anthropic",  # Default
        llm_model="claude-sonnet-4-20250514",
        status="pending",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    return {
        "status": "accepted",
        "analysis_id": analysis.id,
        "message": "Analysis queued. This is a placeholder - implement Celery worker."
    }


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: str,
    reason: str = Query(..., description="Reason for dismissal"),
    current_user: CurrentUser = None,
    db: Session = Depends(get_db)
):
    """Dismiss an alert."""
    alert = db.query(Alert).join(Repository).filter(
        Alert.id == alert_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    from datetime import datetime, timezone
    alert.state = "dismissed"
    alert.dismissed_at = datetime.now(timezone.utc)
    alert.dismissed_by = current_user.email
    alert.dismissed_reason = reason
    
    db.commit()
    db.refresh(alert)
    
    return AlertResponse.model_validate(alert)


@router.post("/bulk-analyze", status_code=status.HTTP_202_ACCEPTED)
async def bulk_analyze_alerts(
    request: BulkAnalyzeRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Request LLM analysis for multiple alerts."""
    # Verify all alerts belong to user
    alerts = db.query(Alert).join(Repository).filter(
        Alert.id.in_(request.alert_ids),
        Repository.user_id == current_user.id
    ).all()
    
    if len(alerts) != len(request.alert_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some alerts not found or not accessible"
        )
    
    # TODO: Queue bulk analysis job with Celery
    return {
        "status": "accepted",
        "count": len(alerts),
        "message": f"Queued {len(alerts)} alerts for analysis. This is a placeholder."
    }


@router.get("/{alert_id}/analyses", response_model=List[AlertAnalysisResponse])
async def get_alert_analyses(
    alert_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Get all analyses for a specific alert."""
    alert = db.query(Alert).join(Repository).filter(
        Alert.id == alert_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    analyses = db.query(AlertAnalysis).filter(
        AlertAnalysis.alert_id == alert_id
    ).order_by(AlertAnalysis.created_at.desc()).all()
    
    return [AlertAnalysisResponse.model_validate(a) for a in analyses]
