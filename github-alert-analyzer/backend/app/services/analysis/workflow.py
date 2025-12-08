"""
Workflow runner that integrates with database tracking.
This is a bridge between the existing agentic analysis code and the web app.
"""
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session

# Add the parent directory to path to import existing analysis code
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from src.orchestrator.workflow import DependabotAnalyzer
from src.orchestrator.state import AnalysisState
from app.models import Alert, AgentExecution


async def run_alert_analysis(
    alert: Alert,
    workflow_id: str,
    github_token: str,
    llm_provider: str,
    llm_model: str,
    db: Session
) -> Dict[str, Any]:
    """
    Run analysis on an alert and track execution in database.
    
    Args:
        alert: The Alert model instance
        workflow_id: ID of the AnalysisWorkflow being tracked
        github_token: GitHub API token
        llm_provider: LLM provider (google, anthropic, openai)
        llm_model: LLM model name
        db: Database session
        
    Returns:
        Dict with analysis results
    """
    
    # Get repository info
    repository = alert.repository
    repo_full_name = repository.full_name
    
    # Create the analyzer
    analyzer = DependabotAnalyzer(
        repo=repo_full_name,
        github_token=github_token,
        llm_model=llm_model,
        llm_provider=llm_provider,
        verbose=True
    )
    
    # We need to convert the DB alert to a DependabotAlert
    # For now, let's fetch it fresh from GitHub
    alerts = analyzer.alert_fetcher.fetch_alerts()
    
    # Find the matching alert by number
    target_alert = None
    for a in alerts:
        if a.alert_number == alert.github_alert_number:
            target_alert = a
            break
    
    if not target_alert:
        raise ValueError(f"Alert #{alert.github_alert_number} not found in GitHub")
    
    # Create initial state
    state = AnalysisState(alert=target_alert)
    
    # Create a tracking wrapper that logs to database
    class DatabaseTracker:
        def __init__(self, workflow_id: str, db: Session):
            self.workflow_id = workflow_id
            self.db = db
            self.execution_order = 0
        
        def log_execution(
            self,
            agent_name: str,
            phase: str,
            status: str,
            success: bool = False,
            output_summary: str = None,
            output_data: Dict[str, Any] = None,
            error_message: str = None,
            duration_seconds: float = None,
            attempt_number: int = 1
        ):
            """Log an agent execution to database."""
            self.execution_order += 1
            
            execution = AgentExecution(
                analysis_workflow_id=self.workflow_id,
                agent_name=agent_name,
                execution_order=self.execution_order,
                phase=phase,
                status=status,
                success=success,
                output_summary=output_summary,
                output_data=output_data,
                error_message=error_message,
                duration_seconds=duration_seconds,
                attempt_number=attempt_number,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc) if status == "completed" else None
            )
            
            self.db.add(execution)
            self.db.commit()
            return execution
    
    tracker = DatabaseTracker(workflow_id, db)
    
    # Run the analysis with tracking
    # This is a simplified version - you'll want to integrate more deeply
    # with the existing workflow to track each step
    
    try:
        # Process the alert (this calls the existing workflow)
        result_state = await analyzer._process_alert_with_state(state)
        
        # Log executions from the state
        for execution in result_state.execution_history:
            tracker.log_execution(
                agent_name=execution.agent_name,
                phase=state.current_phase,
                status="completed" if execution.success else "failed",
                success=execution.success,
                error_message=execution.error_message,
                output_data=execution.metadata,
                attempt_number=1
            )
        
        # Extract final results
        final_report = result_state.final_report
        final_fp_check = result_state.final_fp_check
        
        result = {
            "confidence_score": final_report.confidence if final_report else None,
            "verdict": "false_positive" if (final_fp_check and final_fp_check.is_false_positive) else "true_positive",
            "code_matches": len(result_state.code_matches),
            "analysis_complete": result_state.current_phase in ["completed", "failed"]
        }
        
        # Update workflow counters
        from app.models import AnalysisWorkflow
        workflow = db.query(AnalysisWorkflow).filter(
            AnalysisWorkflow.id == workflow_id
        ).first()
        
        if workflow:
            workflow.total_agents_executed = len(result_state.execution_history)
            workflow.successful_executions = sum(1 for e in result_state.execution_history if e.success)
            workflow.failed_executions = sum(1 for e in result_state.execution_history if not e.success)
            workflow.code_matches_found = len(result_state.code_matches)
            workflow.current_phase = result_state.current_phase
            db.commit()
        
        return result
        
    except Exception as e:
        # Log failure
        tracker.log_execution(
            agent_name="workflow",
            phase="failed",
            status="failed",
            success=False,
            error_message=str(e)
        )
        raise
