"""Alert analysis service with workflow tracking integration."""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models import Alert, AnalysisWorkflow, AgentExecution
from app.core.database import SessionLocal

# Add project root to path for importing orchestrator
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class AnalysisService:
    """
    Service for running alert analysis with workflow tracking.
    Integrates the agentic analysis workflow with database tracking.
    """
    
    def __init__(self):
        self.running_analyses: Dict[str, asyncio.Task] = {}
    
    async def start_analysis(
        self,
        alert_id: str,
        github_token: str,
        llm_provider: str = "google",
        llm_model: str = "gemini-flash-latest",
        user_id: str = None
    ) -> str:
        """
        Start an analysis workflow for an alert.
        Returns the workflow_id.
        """
        db = SessionLocal()
        try:
            # Get the alert with eager loading to prevent detached instance errors
            from sqlalchemy.orm import joinedload
            alert = db.query(Alert).options(joinedload(Alert.repository)).filter(Alert.id == alert_id).first()
            if not alert:
                raise ValueError(f"Alert {alert_id} not found")
            
            # Create workflow record
            workflow = AnalysisWorkflow(
                alert_id=alert_id,
                status="pending",
                current_phase="initial",
                started_at=datetime.now(timezone.utc),
                llm_provider=llm_provider,
                llm_model=llm_model
            )
            db.add(workflow)
            db.commit()
            db.refresh(workflow)
            
            workflow_id = workflow.id
            
            # Start background task (pass alert_id instead of alert object to avoid detached instance)
            task = asyncio.create_task(
                self._run_analysis(
                    workflow_id=workflow_id,
                    alert_id=alert_id,
                    github_token=github_token,
                    llm_provider=llm_provider,
                    llm_model=llm_model
                )
            )
            self.running_analyses[workflow_id] = task
            
            return workflow_id
            
        finally:
            db.close()
    
    async def _run_analysis(
        self,
        workflow_id: str,
        alert_id: str,
        github_token: str,
        llm_provider: str,
        llm_model: str
    ):
        """
        Run the actual analysis workflow with database tracking.
        This runs in the background.
        """
        db = SessionLocal()
        try:
            workflow = db.query(AnalysisWorkflow).filter(
                AnalysisWorkflow.id == workflow_id
            ).first()
            
            if not workflow:
                return
            
            workflow.status = "running"
            db.commit()
            
            # Reload alert with eager loading to prevent detached instance errors
            from sqlalchemy.orm import joinedload
            alert = db.query(Alert).options(joinedload(Alert.repository)).filter(Alert.id == alert_id).first()
            if not alert:
                raise ValueError(f"Alert {alert_id} not found")
            
            # Import the analysis components
            # These will be imported from the relocated modules
            from app.services.analysis.workflow import run_alert_analysis
            
            # Run the analysis
            result = await run_alert_analysis(
                alert=alert,
                workflow_id=workflow_id,
                github_token=github_token,
                llm_provider=llm_provider,
                llm_model=llm_model,
                db=db
            )
            
            # Update workflow with final results
            workflow.status = "completed"
            workflow.completed_at = datetime.now(timezone.utc)
            workflow.total_duration_seconds = (
                workflow.completed_at - workflow.started_at
            ).total_seconds()
            
            # Convert confidence string to numeric score
            confidence_str = result.get("confidence_score")
            if confidence_str:
                confidence_map = {"high": 0.9, "medium": 0.6, "low": 0.3}
                workflow.final_confidence_score = confidence_map.get(confidence_str.lower(), 0.5)
            else:
                workflow.final_confidence_score = None
            
            workflow.final_verdict = result.get("verdict")
            db.commit()
            
        except Exception as e:
            # Handle errors
            import traceback
            error_msg = str(e)
            error_trace = traceback.format_exc()
            print(f"Analysis failed for workflow {workflow_id}: {error_msg}")
            print(error_trace)
            
            workflow = db.query(AnalysisWorkflow).filter(
                AnalysisWorkflow.id == workflow_id
            ).first()
            if workflow:
                workflow.status = "failed"
                workflow.completed_at = datetime.now(timezone.utc)
                workflow.error_message = error_msg
                workflow.error_details = error_trace
                if workflow.started_at:
                    workflow.total_duration_seconds = (
                        workflow.completed_at - workflow.started_at
                    ).total_seconds()
                db.commit()
        finally:
            db.close()
            # Remove from running tasks
            if workflow_id in self.running_analyses:
                del self.running_analyses[workflow_id]
    
    def is_running(self, workflow_id: str) -> bool:
        """Check if an analysis is currently running."""
        return workflow_id in self.running_analyses
    
    def get_status(self, workflow_id: str) -> Optional[str]:
        """Get the status of a running analysis."""
        if workflow_id in self.running_analyses:
            task = self.running_analyses[workflow_id]
            if task.done():
                return "completed" if not task.exception() else "failed"
            return "running"
        return None


# Global instance
analysis_service = AnalysisService()
