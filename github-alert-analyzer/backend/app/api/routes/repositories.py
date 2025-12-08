"""Repository API routes."""
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models import Repository, Alert, OAuthConnection
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


@router.get("/available", status_code=status.HTTP_200_OK)
async def get_available_repositories(
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Fetch available repositories from GitHub without syncing."""
    # Get the user's GitHub OAuth connection
    oauth_conn = db.query(OAuthConnection).filter(
        OAuthConnection.user_id == current_user.id,
        OAuthConnection.provider == "github"
    ).first()
    
    if not oauth_conn or not oauth_conn.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub account not connected. Please connect your GitHub account first."
        )
    
    try:
        # Fetch repositories from GitHub API
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {oauth_conn.access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            
            response = await client.get(
                "https://api.github.com/user/repos",
                headers=headers,
                params={
                    "type": "all",
                    "sort": "updated",
                    "per_page": 100
                }
            )
            response.raise_for_status()
            github_repos = response.json()
        
        # Get already synced repository IDs
        synced_repo_ids = set(
            db.query(Repository.github_repo_id)
            .filter(Repository.user_id == current_user.id)
            .all()
        )
        synced_repo_ids = {str(id[0]) for id in synced_repo_ids}
        
        # Format repository data
        available_repos = []
        for repo_data in github_repos:
            repo_id = str(repo_data["id"])
            available_repos.append({
                "github_repo_id": repo_id,
                "full_name": repo_data["full_name"],
                "name": repo_data["name"],
                "description": repo_data.get("description"),
                "is_private": repo_data["private"],
                "primary_language": repo_data.get("language"),
                "html_url": repo_data["html_url"],
                "is_synced": repo_id in synced_repo_ids
            })
        
        return {
            "repositories": available_repos,
            "total": len(available_repos)
        }
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API error: {e.response.status_code}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch repositories: {str(e)}"
        )


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_repositories(
    repo_ids: list[int],
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Sync selected repositories from GitHub."""
    if not repo_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No repositories selected"
        )
    
    # Get the user's GitHub OAuth connection
    oauth_conn = db.query(OAuthConnection).filter(
        OAuthConnection.user_id == current_user.id,
        OAuthConnection.provider == "github"
    ).first()
    
    if not oauth_conn or not oauth_conn.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub account not connected. Please connect your GitHub account first."
        )
    
    try:
        # Fetch repositories from GitHub API
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {oauth_conn.access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            
            response = await client.get(
                "https://api.github.com/user/repos",
                headers=headers,
                params={
                    "type": "all",
                    "sort": "updated",
                    "per_page": 100
                }
            )
            response.raise_for_status()
            github_repos = response.json()
        
        # Filter to only selected repositories
        selected_repos = [r for r in github_repos if r["id"] in repo_ids]
        
        if not selected_repos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected repositories not found in your GitHub account"
            )
        
        # Create or update repositories in database
        synced_count = 0
        for repo_data in selected_repos:
            repo = db.query(Repository).filter(
                Repository.github_repo_id == repo_data["id"],
                Repository.user_id == current_user.id
            ).first()
            
            if repo:
                # Update existing repository
                repo.full_name = repo_data["full_name"]
                repo.is_private = repo_data["private"]
                repo.description = repo_data.get("description")
                repo.primary_language = repo_data.get("language")
                repo.is_monitored = True
            else:
                # Create new repository
                repo = Repository(
                    user_id=current_user.id,
                    github_repo_id=repo_data["id"],
                    full_name=repo_data["full_name"],
                    is_private=repo_data["private"],
                    description=repo_data.get("description"),
                    primary_language=repo_data.get("language"),
                    is_monitored=True,
                    sync_status="pending"
                )
                db.add(repo)
            
            synced_count += 1
        
        db.commit()
        
        return {
            "status": "accepted",
            "message": f"Successfully synced {synced_count} repositories from GitHub."
        }
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API error: {e.response.status_code}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync repositories: {str(e)}"
        )



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


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repo_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Unlink (delete) a repository from monitoring."""
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    db.delete(repo)
    db.commit()
    
    return None


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
