"""Pydantic schemas for alert-related data."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class VulnerabilityResponse(BaseModel):
    """Schema for vulnerability response."""
    id: str
    cve_id: Optional[str]
    ghsa_id: Optional[str]
    summary: Optional[str]
    description: Optional[str]
    severity: Optional[str]
    cvss_score: Optional[float]
    cvss_vector: Optional[str]
    published_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AlertAnalysisResponse(BaseModel):
    """Schema for alert analysis response."""
    id: str
    llm_provider: str
    llm_model: str
    status: str
    analysis_result: Optional[Dict[str, Any]]
    confidence_score: Optional[float]
    tokens_used: Optional[int]
    cost_usd: Optional[float]
    processing_time_seconds: Optional[float]
    error_message: Optional[str]
    analyzed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AlertBase(BaseModel):
    """Base alert schema."""
    package_name: str
    package_ecosystem: str
    manifest_path: Optional[str] = None
    severity: str
    state: str


class AlertResponse(AlertBase):
    """Schema for alert response."""
    id: str
    repository_id: str
    repository_full_name: Optional[str] = None
    github_alert_number: int
    vulnerable_version_range: Optional[str]
    patched_version: Optional[str]
    github_created_at: Optional[datetime]
    dismissed_at: Optional[datetime]
    dismissed_by: Optional[str]
    dismissed_reason: Optional[str]
    fixed_at: Optional[datetime]
    
    # Analysis status tracking
    risk_status: Optional[str] = None
    exploitability_level: Optional[str] = None
    action_priority: Optional[str] = None
    analysis_confidence: Optional[float] = None
    last_analyzed_at: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime
    vulnerability: Optional[VulnerabilityResponse] = None
    latest_analysis: Optional[AlertAnalysisResponse] = None
    
    class Config:
        from_attributes = True


class AlertDetailResponse(AlertResponse):
    """Schema for detailed alert response with all analyses."""
    analyses: List[AlertAnalysisResponse] = []
    repository_name: Optional[str] = None


class AlertListResponse(BaseModel):
    """Schema for paginated alert list."""
    items: List[AlertResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AlertFilterParams(BaseModel):
    """Schema for alert filter parameters."""
    repository_id: Optional[str] = None
    severity: Optional[List[str]] = None
    state: Optional[List[str]] = None
    package_ecosystem: Optional[str] = None
    has_analysis: Optional[bool] = None
    search: Optional[str] = None


class AnalyzeAlertRequest(BaseModel):
    """Schema for analyze alert request."""
    llm_config_id: Optional[str] = None
    custom_prompt: Optional[str] = None


class BulkAnalyzeRequest(BaseModel):
    """Schema for bulk analyze request."""
    alert_ids: List[str]
    llm_config_id: Optional[str] = None


class DashboardStats(BaseModel):
    """Schema for dashboard statistics."""
    total_alerts: int
    alerts_by_severity: Dict[str, int]
    alerts_by_state: Dict[str, int]
    alerts_by_ecosystem: Dict[str, int]
    alerts_by_risk_status: Optional[Dict[str, int]] = None
    alerts_by_priority: Optional[Dict[str, int]] = None
    recent_alerts: List[AlertResponse]
    repositories_monitored: int
    total_analyses: int
