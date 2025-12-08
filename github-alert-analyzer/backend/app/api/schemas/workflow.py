"""Schemas for agent execution and workflow tracking."""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AgentExecutionBase(BaseModel):
    """Base agent execution data."""
    agent_name: str
    execution_order: int
    phase: str
    status: str = "pending"
    attempt_number: int = 1


class AgentExecutionResponse(AgentExecutionBase):
    """Agent execution response with all details."""
    id: str
    analysis_workflow_id: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    success: bool
    output_summary: Optional[str] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AnalysisWorkflowBase(BaseModel):
    """Base workflow data."""
    status: str = "pending"
    current_phase: Optional[str] = None


class AnalysisWorkflowResponse(AnalysisWorkflowBase):
    """Analysis workflow response with summary."""
    id: str
    alert_id: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_seconds: Optional[float] = None
    total_agents_executed: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_retries: int = 0
    total_refinements: int = 0
    final_confidence_score: Optional[float] = None
    final_verdict: Optional[str] = None
    code_matches_found: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AnalysisWorkflowDetailResponse(AnalysisWorkflowResponse):
    """Detailed workflow response with all agent executions."""
    agent_executions: List[AgentExecutionResponse] = Field(default_factory=list)
    accumulated_context: Optional[str] = None
    code_context: Optional[str] = None


class WorkflowPhaseStats(BaseModel):
    """Statistics for a specific phase in the workflow."""
    phase: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    total_duration_seconds: float
    agents: List[str]


class WorkflowSummary(BaseModel):
    """High-level summary of workflow execution."""
    workflow_id: str
    alert_id: str
    status: str
    phases_completed: List[str]
    total_agents: int
    success_rate: float
    total_duration: Optional[float]
    phase_stats: List[WorkflowPhaseStats]
