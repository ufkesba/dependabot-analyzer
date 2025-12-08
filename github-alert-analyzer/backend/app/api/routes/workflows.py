"""Workflow analysis API routes."""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from collections import defaultdict
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Alert, Repository, AnalysisWorkflow, AgentExecution
from app.api.schemas import (
    AnalysisWorkflowResponse,
    AnalysisWorkflowDetailResponse,
    AgentExecutionResponse,
    WorkflowPhaseStats,
    WorkflowSummary,
)
from app.api.deps import CurrentUser


router = APIRouter(prefix="/workflows", tags=["Workflows"])


class UpdateWorkflowStatusRequest(BaseModel):
    """Request to update workflow status."""
    status: str  # completed, failed, cancelled
    error_message: Optional[str] = None


@router.get("/{workflow_id}", response_model=AnalysisWorkflowDetailResponse)
async def get_workflow(
    workflow_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Get detailed workflow information including all agent executions."""
    workflow = (
        db.query(AnalysisWorkflow)
        .join(Alert)
        .join(Repository)
        .filter(
            AnalysisWorkflow.id == workflow_id,
            Repository.user_id == current_user.id
        )
        .options(
            joinedload(AnalysisWorkflow.agent_executions)
        )
        .first()
    )
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    
    return workflow


@router.get("/{workflow_id}/summary", response_model=WorkflowSummary)
async def get_workflow_summary(
    workflow_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Get high-level workflow summary with phase statistics."""
    workflow = (
        db.query(AnalysisWorkflow)
        .join(Alert)
        .join(Repository)
        .filter(
            AnalysisWorkflow.id == workflow_id,
            Repository.user_id == current_user.id
        )
        .options(
            joinedload(AnalysisWorkflow.agent_executions)
        )
        .first()
    )
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    
    # Calculate phase statistics
    phase_data = defaultdict(lambda: {
        "executions": [],
        "agents": set()
    })
    
    for execution in workflow.agent_executions:
        phase_data[execution.phase]["executions"].append(execution)
        phase_data[execution.phase]["agents"].add(execution.agent_name)
    
    phase_stats = []
    for phase, data in phase_data.items():
        executions = data["executions"]
        successful = sum(1 for e in executions if e.success)
        failed = sum(1 for e in executions if not e.success)
        total_duration = sum(e.duration_seconds or 0 for e in executions)
        
        phase_stats.append(WorkflowPhaseStats(
            phase=phase,
            total_executions=len(executions),
            successful_executions=successful,
            failed_executions=failed,
            total_duration_seconds=total_duration,
            agents=sorted(list(data["agents"]))
        ))
    
    # Get completed phases
    phases_completed = list(set(e.phase for e in workflow.agent_executions if e.success))
    
    # Calculate success rate
    total_executions = len(workflow.agent_executions)
    success_rate = (
        workflow.successful_executions / total_executions 
        if total_executions > 0 
        else 0.0
    )
    
    return WorkflowSummary(
        workflow_id=workflow.id,
        alert_id=workflow.alert_id,
        status=workflow.status,
        phases_completed=sorted(phases_completed),
        total_agents=total_executions,
        success_rate=success_rate,
        total_duration=workflow.total_duration_seconds,
        phase_stats=phase_stats
    )


@router.get("/alert/{alert_id}", response_model=List[AnalysisWorkflowResponse])
async def get_alert_workflows(
    alert_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Get all workflows for a specific alert."""
    workflows = (
        db.query(AnalysisWorkflow)
        .join(Alert)
        .join(Repository)
        .filter(
            AnalysisWorkflow.alert_id == alert_id,
            Repository.user_id == current_user.id
        )
        .order_by(AnalysisWorkflow.created_at.desc())
        .all()
    )
    
    return workflows


@router.get("/{workflow_id}/executions", response_model=List[AgentExecutionResponse])
async def get_workflow_executions(
    workflow_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    phase: Optional[str] = None,
):
    """Get all agent executions for a workflow, optionally filtered by phase."""
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
    
    # Get executions
    query = db.query(AgentExecution).filter(
        AgentExecution.analysis_workflow_id == workflow_id
    )
    
    if phase:
        query = query.filter(AgentExecution.phase == phase)
    
    executions = query.order_by(AgentExecution.execution_order).all()
    
    return executions


@router.get("/{workflow_id}/phases", response_model=List[str])
async def get_workflow_phases(
    workflow_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Get list of all phases in a workflow."""
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
    
    # Get unique phases
    phases = (
        db.query(AgentExecution.phase)
        .filter(AgentExecution.analysis_workflow_id == workflow_id)
        .distinct()
        .order_by(AgentExecution.execution_order)
        .all()
    )
    
    return [p[0] for p in phases]


@router.put("/{workflow_id}/status", response_model=AnalysisWorkflowDetailResponse)
async def update_workflow_status(
    workflow_id: str,
    request: UpdateWorkflowStatusRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Manually update workflow status (for stuck/hanging workflows)."""
    # Verify workflow belongs to user
    workflow = (
        db.query(AnalysisWorkflow)
        .join(Alert)
        .join(Repository)
        .filter(
            AnalysisWorkflow.id == workflow_id,
            Repository.user_id == current_user.id
        )
        .options(
            joinedload(AnalysisWorkflow.agent_executions)
        )
        .first()
    )
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    
    # Validate status
    valid_statuses = ["completed", "failed", "cancelled"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Update workflow
    workflow.status = request.status
    if not workflow.completed_at:
        workflow.completed_at = datetime.now(timezone.utc)
    
    # Calculate duration if started
    if workflow.started_at and workflow.completed_at:
        workflow.total_duration_seconds = (
            workflow.completed_at - workflow.started_at
        ).total_seconds()
    
    # Update error message if provided
    if request.error_message:
        workflow.error_message = request.error_message
    
    # Mark any running agent executions as failed
    for execution in workflow.agent_executions:
        if execution.status in ["pending", "running"]:
            execution.status = "failed"
            execution.completed_at = datetime.now(timezone.utc)
            if execution.started_at:
                execution.duration_seconds = (
                    execution.completed_at - execution.started_at
                ).total_seconds()
            execution.error_message = "Workflow manually terminated"
    
    db.commit()
    db.refresh(workflow)
    
    return workflow
