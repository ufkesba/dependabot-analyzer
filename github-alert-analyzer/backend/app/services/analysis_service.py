"""Alert analysis service with workflow tracking integration."""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from app.services.models_service import alert_service, workflow_service, AlertModel, WorkflowModel

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
        # Get the alert
        alert = await alert_service.get(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Create workflow record
        workflow = WorkflowModel(
            id="", # Firestore will generate
            alert_id=alert_id,
            status="pending",
            current_phase="initial",
            started_at=datetime.now(timezone.utc),
            llm_provider=llm_provider,
            llm_model=llm_model,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        workflow = await workflow_service.create(workflow)

        workflow_id = workflow.id

        # Start background task
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
    
    async def _run_analysis(
        self,
        workflow_id: str,
        alert_id: str,
        github_token: str,
        llm_provider: str,
        llm_model: str
    ):
        """
        Run the actual analysis workflow with Firestore tracking.
        This runs in the background.
        """
        try:
            workflow = await workflow_service.get(workflow_id)
            if not workflow:
                return
            
            await workflow_service.update(workflow_id, {"status": "running"})
            
            alert = await alert_service.get(alert_id)
            if not alert:
                raise ValueError(f"Alert {alert_id} not found")
            
            # Import the analysis components
            from app.services.analysis.workflow import run_alert_analysis
            
            # Run the analysis
            result = await run_alert_analysis(
                alert=alert,
                workflow_id=workflow_id,
                github_token=github_token,
                llm_provider=llm_provider,
                llm_model=llm_model,
            )
            
            # Update workflow with final results
            completed_at = datetime.now(timezone.utc)
            total_duration_seconds = (
                completed_at - workflow.started_at
            ).total_seconds() if workflow.started_at else None
            
            # Convert confidence string to numeric score
            confidence_str = result.get("confidence_score")
            final_confidence_score = None
            if confidence_str:
                confidence_map = {"high": 0.9, "medium": 0.6, "low": 0.3}
                final_confidence_score = confidence_map.get(confidence_str.lower(), 0.5)
            
            workflow_update = {
                "status": "completed",
                "completed_at": completed_at,
                "total_duration_seconds": total_duration_seconds,
                "final_confidence_score": final_confidence_score,
                "final_verdict": result.get("verdict")
            }
            await workflow_service.update(workflow_id, workflow_update)
            
            # Update alert with status tracking from analysis results
            alert_update = {}
            # Determine risk status from verdict
            verdict = (result.get("verdict") or "").lower()
            if "false positive" in verdict or verdict == "false_positive":
                alert_update["risk_status"] = "false_positive"
            elif "true positive" in verdict or verdict == "true_positive":
                alert_update["risk_status"] = "true_positive"
            else:
                alert_update["risk_status"] = "needs_review"

            # Extract exploitability level
            exploitability = (result.get("exploitability") or "").lower()
            if "not exploitable" in exploitability or exploitability == "not_exploitable":
                alert_update["exploitability_level"] = "not_exploitable"
            elif "exploitable" in exploitability:
                alert_update["exploitability_level"] = "exploitable"
            elif "unused" in exploitability or "not used" in exploitability:
                alert_update["exploitability_level"] = "package_unused"
            elif "test" in exploitability or "dev" in exploitability:
                alert_update["exploitability_level"] = "test_only"

            # Extract action priority
            priority = (result.get("priority") or "").lower()
            if priority in ["critical", "high", "medium", "low"]:
                alert_update["action_priority"] = priority
            elif alert_update.get("risk_status") == "false_positive":
                alert_update["action_priority"] = "no_action"

            alert_update["analysis_confidence"] = final_confidence_score
            alert_update["last_analyzed_at"] = datetime.now(timezone.utc)
            
            await alert_service.update(alert_id, alert_update)
            
        except Exception as e:
            # Handle errors
            import traceback
            error_msg = str(e)
            error_trace = traceback.format_exc()
            print(f"Analysis failed for workflow {workflow_id}: {error_msg}")
            
            workflow = await workflow_service.get(workflow_id)
            if workflow:
                completed_at = datetime.now(timezone.utc)
                total_duration = (completed_at - workflow.started_at).total_seconds() if workflow.started_at else None
                await workflow_service.update(workflow_id, {
                    "status": "failed",
                    "completed_at": completed_at,
                    "error_message": error_msg,
                    "error_details": error_trace,
                    "total_duration_seconds": total_duration
                })
        finally:
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
