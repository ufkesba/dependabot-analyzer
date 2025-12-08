"""Alert API routes."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.database import get_db
from app.models import Alert, Repository, AlertAnalysis, Vulnerability
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
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=1000),
    repository_id: Optional[str] = None,
    severity: Optional[List[str]] = Query(None),
    state: Optional[List[str]] = Query(None),
    package_ecosystem: Optional[str] = None,
    has_analysis: Optional[bool] = None,
    search: Optional[str] = None,
):
    """List all alerts for current user's repositories."""
    # Base query with user's repositories
    query = db.query(Alert).join(Repository).filter(
        Repository.user_id == current_user.id
    )
    
    # Apply filters
    if repository_id:
        query = query.filter(Alert.repository_id == repository_id)
    if severity:
        query = query.filter(Alert.severity.in_(severity))
    if state:
        query = query.filter(Alert.state.in_(state))
    if package_ecosystem:
        query = query.filter(Alert.package_ecosystem == package_ecosystem)
    if search:
        query = query.filter(
            Alert.package_name.ilike(f"%{search}%")
        )
    if has_analysis is not None:
        if has_analysis:
            query = query.filter(Alert.analyses.any())
        else:
            query = query.filter(~Alert.analyses.any())
    
    # Count total
    total = query.count()
    
    # Paginate
    offset = (page - 1) * per_page
    alerts = query.options(
        joinedload(Alert.vulnerability),
        joinedload(Alert.repository)
    ).order_by(
        Alert.created_at.desc()
    ).offset(offset).limit(per_page).all()
    
    pages = (total + per_page - 1) // per_page
    
    # Add latest analysis to each alert
    alert_responses = []
    for alert in alerts:
        alert_dict = AlertResponse.model_validate(alert).model_dump()
        # Add repository full name
        alert_dict["repository_full_name"] = alert.repository.full_name if alert.repository else None
        # Get latest analysis
        latest_analysis = db.query(AlertAnalysis).filter(
            AlertAnalysis.alert_id == alert.id,
            AlertAnalysis.status == "completed"
        ).order_by(AlertAnalysis.created_at.desc()).first()
        
        if latest_analysis:
            alert_dict["latest_analysis"] = AlertAnalysisResponse.model_validate(latest_analysis)
        
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
    db: Session = Depends(get_db)
):
    """Get a specific alert with all its analyses."""
    alert = db.query(Alert).options(
        joinedload(Alert.vulnerability),
        joinedload(Alert.repository),
        joinedload(Alert.analyses)
    ).join(Repository).filter(
        Alert.id == alert_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    response = AlertDetailResponse.model_validate(alert)
    response.repository_name = alert.repository.full_name
    response.analyses = [AlertAnalysisResponse.model_validate(a) for a in alert.analyses]
    
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
