"""Repository API routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models import Repository, Alert
from app.api.schemas import (
    RepositoryResponse,
    RepositoryUpdate,
    RepositoryListResponse,
    SyncJobResponse,
)
from app.api.deps import CurrentUser


router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_monitored: Optional[bool] = None,
):
    """List all repositories for current user."""
    query = db.query(Repository).filter(Repository.user_id == current_user.id)
    
    # Apply filters
    if search:
        query = query.filter(Repository.full_name.ilike(f"%{search}%"))
    if is_monitored is not None:
        query = query.filter(Repository.is_monitored == is_monitored)
    
    # Count total
    total = query.count()
    
    # Paginate
    offset = (page - 1) * per_page
    repositories = query.order_by(Repository.full_name).offset(offset).limit(per_page).all()
    
    pages = (total + per_page - 1) // per_page
    
    return RepositoryListResponse(
        items=[RepositoryResponse.model_validate(r) for r in repositories],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_repositories(
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Sync repositories from GitHub."""
    # TODO: Implement GitHub API call to fetch repositories
    # This would require GitHub OAuth connection
    return {
        "status": "accepted",
        "message": "Repository sync started. This is a placeholder - implement GitHub OAuth first."
    }


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Get a specific repository."""
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    return RepositoryResponse.model_validate(repo)


@router.put("/{repo_id}", response_model=RepositoryResponse)
async def update_repository(
    repo_id: str,
    repo_data: RepositoryUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Update repository settings."""
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    # Update fields
    update_data = repo_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(repo, field, value)
    
    db.commit()
    db.refresh(repo)
    
    return RepositoryResponse.model_validate(repo)


@router.post("/{repo_id}/sync-alerts", status_code=status.HTTP_202_ACCEPTED)
async def sync_repository_alerts(
    repo_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Sync Dependabot alerts for a specific repository."""
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    # TODO: Implement GitHub API call to fetch alerts
    return {
        "status": "accepted",
        "message": f"Alert sync started for {repo.full_name}. This is a placeholder."
    }


@router.get("/{repo_id}/stats")
async def get_repository_stats(
    repo_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Get statistics for a specific repository."""
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    # Get alert counts by severity
    severity_counts = db.query(
        Alert.severity,
        func.count(Alert.id)
    ).filter(
        Alert.repository_id == repo_id
    ).group_by(Alert.severity).all()
    
    # Get alert counts by state
    state_counts = db.query(
        Alert.state,
        func.count(Alert.id)
    ).filter(
        Alert.repository_id == repo_id
    ).group_by(Alert.state).all()
    
    return {
        "repository_id": repo_id,
        "full_name": repo.full_name,
        "total_alerts": repo.alert_count,
        "alerts_by_severity": dict(severity_counts),
        "alerts_by_state": dict(state_counts),
        "last_synced_at": repo.last_synced_at,
        "sync_status": repo.sync_status,
    }
