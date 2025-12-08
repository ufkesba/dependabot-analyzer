"""Agent execution tracking models for agentic workflow visualization."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Integer, Float, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Dict, Any

from app.core.database import Base


class AgentExecution(Base):
    """Individual agent execution within an analysis workflow."""
    
    __tablename__ = "agent_executions"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    analysis_workflow_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_workflows.id", ondelete="CASCADE"),
        nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)  # code_analyzer, deep_analyzer, etc.
    execution_order: Mapped[int] = mapped_column(Integer, nullable=False)  # Order in workflow
    phase: Mapped[str] = mapped_column(String(50), nullable=False)  # code_analysis, deep_analysis, reflection, etc.
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Results
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # Human-readable summary
    output_data: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # Structured output
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Metadata
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    extra_data: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # Additional agent-specific data
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    workflow = relationship("AnalysisWorkflow", back_populates="agent_executions")
    
    def __repr__(self) -> str:
        return f"<AgentExecution {self.agent_name} ({self.status})>"


class AnalysisWorkflow(Base):
    """Complete analysis workflow for an alert, tracking all agent executions."""
    
    __tablename__ = "analysis_workflows"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    alert_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Workflow status
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed
    current_phase: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Summary results
    total_agents_executed: Mapped[int] = mapped_column(Integer, default=0)
    successful_executions: Mapped[int] = mapped_column(Integer, default=0)
    failed_executions: Mapped[int] = mapped_column(Integer, default=0)
    total_retries: Mapped[int] = mapped_column(Integer, default=0)
    total_refinements: Mapped[int] = mapped_column(Integer, default=0)  # Number of reflection iterations
    
    # Final results
    final_confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_verdict: Mapped[str | None] = mapped_column(String(100), nullable=True)  # false_positive, true_positive, needs_review
    accumulated_context: Mapped[str | None] = mapped_column(Text, nullable=True)  # Context from retries
    
    # Error tracking
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Code analysis results
    code_matches_found: Mapped[int] = mapped_column(Integer, default=0)
    code_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    alert = relationship("Alert", back_populates="workflows")
    agent_executions = relationship(
        "AgentExecution",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="AgentExecution.execution_order"
    )
    
    def __repr__(self) -> str:
        return f"<AnalysisWorkflow {self.id} ({self.status})>"
