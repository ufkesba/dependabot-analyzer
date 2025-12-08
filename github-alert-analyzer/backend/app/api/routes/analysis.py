"""Analysis API routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Alert, Repository, User, AnalysisWorkflow
from app.models.user import OAuthConnection
from app.api.deps import CurrentUser
from app.services.analysis_service import analysis_service


router = APIRouter(prefix="/analysis", tags=["Analysis"])


class StartAnalysisRequest(BaseModel):
    """Request to start analysis."""
    llm_provider: Optional[str] = "anthropic"
    llm_model: Optional[str] = "claude-haiku-4-5-20251001"


class StartAnalysisResponse(BaseModel):
    """Response with workflow ID."""
    workflow_id: str
    status: str
    message: str


class AnalysisStatusResponse(BaseModel):
    """Response with analysis status."""
    workflow_id: str
    status: str
    is_running: bool
    error_message: Optional[str] = None
    completed_agents: Optional[int] = None
    total_agents: Optional[int] = None
    error_message: Optional[str] = None
    completed_agents: Optional[int] = None
    total_agents: Optional[int] = None


@router.post("/alerts/{alert_id}/analyze", response_model=StartAnalysisResponse)
async def start_alert_analysis(
    alert_id: str,
    request: StartAnalysisRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Start an analysis workflow for an alert.
    This runs asynchronously in the background.
    """
    # Verify alert exists and belongs to user (with eager loading)
    from sqlalchemy.orm import joinedload
    alert = (
        db.query(Alert)
        .options(joinedload(Alert.repository))
        .join(Repository)
        .filter(
            Alert.id == alert_id,
            Repository.user_id == current_user.id
        )
        .first()
    )
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Get user's GitHub token
    user = db.query(User).filter(User.id == current_user.id).first()
    github_token = None
    
    # Try to get OAuth connection
    if user.oauth_connections:
        github_oauth = next(
            (conn for conn in user.oauth_connections if conn.provider == "github"),
            None
        )
        if github_oauth:
            github_token = github_oauth.access_token
    
    if not github_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub OAuth connection required. Please connect your GitHub account."
        )
    
    try:
        # Start the analysis
        workflow_id = await analysis_service.start_analysis(
            alert_id=alert_id,
            github_token=github_token,
            llm_provider=request.llm_provider,
            llm_model=request.llm_model,
            user_id=current_user.id
        )
        
        return StartAnalysisResponse(
            workflow_id=workflow_id,
            status="started",
            message="Analysis started successfully. This may take several minutes."
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start analysis: {str(e)}"
        )


@router.get("/workflows/{workflow_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    workflow_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Get the status of a running or completed analysis."""
    # Verify workflow belongs to user
    workflow = (
        db.query(AnalysisWorkflow)
        .join(Alert)
        .join(Repository)
        .filter(
            AnalysisWorkflow.id == workflow_id,
            Repository.user_id == current_user.id
        )
        .first()
    )
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    
    is_running = analysis_service.is_running(workflow_id)
    
    return AnalysisStatusResponse(
        workflow_id=workflow_id,
        status=workflow.status,
        is_running=is_running,
        error_message=workflow.error_message if hasattr(workflow, 'error_message') else None,
        completed_agents=workflow.successful_executions + workflow.failed_executions,
        total_agents=workflow.total_agents_executed
    )


@router.post("/alerts/{alert_id}/cancel")
async def cancel_analysis(
    alert_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Cancel a running analysis (not implemented yet)."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Analysis cancellation not yet implemented"
    )
