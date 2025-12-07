"""Pydantic schemas for repository-related data."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class RepositoryBase(BaseModel):
    """Base repository schema."""
    full_name: str
    description: Optional[str] = None
    is_private: bool = False
    primary_language: Optional[str] = None


class RepositoryResponse(RepositoryBase):
    """Schema for repository response."""
    id: str
    github_repo_id: int
    is_monitored: bool
    sync_status: str
    last_synced_at: Optional[datetime]
    alert_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class RepositoryUpdate(BaseModel):
    """Schema for updating repository."""
    is_monitored: Optional[bool] = None


class RepositoryListResponse(BaseModel):
    """Schema for paginated repository list."""
    items: List[RepositoryResponse]
    total: int
    page: int
    per_page: int
    pages: int


class SyncJobResponse(BaseModel):
    """Schema for sync job response."""
    id: str
    repository_id: str
    status: str
    job_type: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    alerts_processed: int
    created_at: datetime
    
    class Config:
        from_attributes = True
