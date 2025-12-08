"""
Workflow runner that integrates with database tracking.
This is a bridge between the existing agentic analysis code and the web app.
"""
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session
from rich.console import Console

# Add the parent directory to path to import existing analysis code
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from src.orchestrator.workflow import DependabotAnalyzer
from src.orchestrator.state import AnalysisState
from app.models import Alert, AgentExecution
from app.core.config import settings

console = Console()


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
    
    # Set API key in environment based on provider
    # The LLMClient uses os.getenv() so we need to set it in the environment
    if llm_provider == 'anthropic':
        api_key = settings.anthropic_api_key
        if api_key:
            os.environ['ANTHROPIC_API_KEY'] = api_key
    elif llm_provider == 'google':
        api_key = settings.google_api_key
        if api_key:
            os.environ['GOOGLE_API_KEY'] = api_key
    elif llm_provider == 'openai':
        api_key = settings.openai_api_key
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key
    
    # Create the analyzer
    analyzer = DependabotAnalyzer(
        repo=repo_full_name,
        github_token=github_token,
        llm_model=llm_model,
        llm_provider=llm_provider,
        verbose=True
    )
    
    # Fetch the specific alert by ID from GitHub
    target_alert = analyzer.alert_fetcher.get_alert_by_id(alert.github_alert_number)
    
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
            # Build comprehensive output data from execution metadata
            output_data = execution.metadata.copy() if execution.metadata else {}
            
            # Try to capture LLM model info for this specific agent
            agent_llm_info = None
            try:
                if execution.agent_name == "deep_analyzer" and hasattr(analyzer.analyzer, 'llm'):
                    agent_llm_info = {
                        "provider": analyzer.analyzer.llm.provider,
                        "model": analyzer.analyzer.llm.model
                    }
                elif execution.agent_name == "false_positive_checker" and hasattr(analyzer.false_positive_checker, 'llm'):
                    agent_llm_info = {
                        "provider": analyzer.false_positive_checker.llm.provider,
                        "model": analyzer.false_positive_checker.llm.model
                    }
                elif execution.agent_name == "code_analyzer" and hasattr(analyzer.code_analyzer, 'llm_client'):
                    agent_llm_info = {
                        "provider": analyzer.code_analyzer.llm_client.provider,
                        "model": analyzer.code_analyzer.llm_client.model
                    }
                elif execution.agent_name == "reflection_agent" and hasattr(analyzer.reflection_agent, 'llm'):
                    agent_llm_info = {
                        "provider": analyzer.reflection_agent.llm.provider,
                        "model": analyzer.reflection_agent.llm.model
                    }
            except:
                pass  # If we can't get LLM info, that's okay
            
            if agent_llm_info:
                output_data["llm_model_used"] = agent_llm_info
            
            # Add structured summary based on agent type
            if execution.agent_name == "deep_analyzer" and result_state.final_report:
                report = result_state.final_report
                output_data.update({
                    "full_response": {
                        "alert_number": report.alert_number,
                        "package": report.package,
                        "vulnerability_id": report.vulnerability_id,
                        "is_exploitable": report.is_exploitable,
                        "confidence": report.confidence,
                        "reasoning": report.reasoning,
                        "impact_assessment": report.impact_assessment,
                        "code_paths_affected": report.code_paths_affected,
                        "test_case": report.test_case,
                        "recommended_action": report.recommended_action,
                        "priority": report.priority
                    }
                })
                output_summary = f"Exploitable: {report.is_exploitable} | Confidence: {report.confidence} | Priority: {report.priority}\n\n{report.reasoning}"
            elif execution.agent_name == "false_positive_checker" and result_state.final_fp_check:
                fp_check = result_state.final_fp_check
                output_data.update({
                    "full_response": {
                        "is_false_positive": fp_check.is_false_positive,
                        "confidence": fp_check.confidence,
                        "reasoning": fp_check.reasoning,
                        "corrected_priority": fp_check.corrected_priority,
                        "corrected_exploitability": fp_check.corrected_exploitability
                    }
                })
                output_summary = f"False Positive: {fp_check.is_false_positive} | Confidence: {fp_check.confidence}\n\n{fp_check.reasoning}"
            elif execution.agent_name == "reflection_agent" and result_state.reflection_results:
                # Get the latest reflection result
                reflection = result_state.reflection_results[-1]
                output_data.update({
                    "full_response": {
                        "needs_refinement": reflection.needs_refinement,
                        "confidence_assessment": reflection.confidence_assessment,
                        "detected_patterns": reflection.detected_patterns,
                        "reasoning": reflection.reasoning,
                        "suggested_focus_areas": reflection.suggested_focus_areas,
                        "command": {
                            "action": reflection.command.action,
                            "reason": reflection.command.reason,
                            "next_agent": reflection.command.next_agent,
                            "confidence_boost": reflection.command.confidence_boost
                        }
                    }
                })
                output_summary = f"Refinement Needed: {reflection.needs_refinement} | Assessment: {reflection.confidence_assessment}\n\n{reflection.reasoning}"
            elif execution.agent_name == "code_analyzer":
                matches_found = len(result_state.code_matches) if result_state.code_matches else 0
                output_data["matches_found"] = matches_found
                if result_state.code_matches:
                    output_data["full_response"] = {
                        "code_matches": [
                            {
                                "file_path": match.file_path,
                                "line_number": match.line_number,
                                "code_snippet": match.code_snippet,
                                "matched_pattern": match.matched_pattern,
                                "context": match.context
                            }
                            for match in result_state.code_matches[:10]  # Limit to first 10 matches
                        ]
                    }
                output_summary = f"Found {matches_found} code matches"
            else:
                output_summary = f"{execution.agent_name} execution"
            
            tracker.log_execution(
                agent_name=execution.agent_name,
                phase=state.current_phase,
                status="completed" if execution.success else "failed",
                success=execution.success,
                error_message=execution.error_message,
                output_summary=output_summary,
                output_data=output_data,
                attempt_number=1
            )
            
            # Note: Individual agents may use different LLM models
            # LLM model info is captured in the JSON conversation logs
            # at logs/conversations/{agent_name}_{session_id}_{num}.json
        
        # Extract final results
        final_report = result_state.final_report
        final_fp_check = result_state.final_fp_check
        
        # Determine verdict based on available information
        # Priority: 
        # 1. If reflection accepted AND has good confidence -> use final report
        # 2. If false positive check exists with high confidence -> use FP check
        # 3. If reflection uncertain but FP check confident -> use FP check
        # 4. Use final report if available
        # 5. Default to needs_review
        verdict = "needs_review"  # Default if uncertain
        exploitability = None
        priority = None
        
        console.print(f"[cyan]Determining final verdict for alert...[/cyan]")
        
        # Check if we have a confident false positive check result
        has_confident_fp_check = (
            final_fp_check and 
            hasattr(final_fp_check, 'confidence') and 
            final_fp_check.confidence == "high"
        )
        
        # Check reflection results first
        if result_state.reflection_results:
            last_reflection = result_state.reflection_results[-1]
            console.print(f"[dim]Reflection: needs_refinement={last_reflection.needs_refinement}, confidence={last_reflection.confidence_assessment}[/dim]")
            
            # If reflection accepted the result and confidence is acceptable
            if (not last_reflection.needs_refinement and 
                last_reflection.confidence_assessment == "acceptable"):
                # Use the final report's assessment
                if final_report:
                    # Determine verdict based on exploitability
                    if hasattr(final_report, 'is_exploitable'):
                        if final_report.is_exploitable:
                            verdict = "true_positive"
                            console.print(f"[green]✓ Verdict: TRUE POSITIVE (exploitable per final report, reflection accepted)[/green]")
                        else:
                            verdict = "false_positive"
                            console.print(f"[green]✓ Verdict: FALSE POSITIVE (not exploitable per final report, reflection accepted)[/green]")
                    else:
                        console.print(f"[yellow]⚠ Final report missing is_exploitable field - checking FP check[/yellow]")
                        # Fall through to FP check
                    # Extract exploitability level
                    if hasattr(final_report, 'is_exploitable'):
                        exploitability = "exploitable" if final_report.is_exploitable else "not_exploitable"
                    # Extract priority
                    if hasattr(final_report, 'priority'):
                        priority = final_report.priority
                else:
                    console.print(f"[yellow]⚠ No final report available - checking FP check[/yellow]")
            
            # If reflection uncertain but we have confident FP check, trust the FP check
            elif has_confident_fp_check and last_reflection.confidence_assessment != "contradictory":
                verdict = "false_positive" if final_fp_check.is_false_positive else "true_positive"
                console.print(f"[green]✓ Verdict from FP check (reflection uncertain but FP check confident): {verdict.upper()}[/green]")
                if hasattr(final_fp_check, 'exploitability'):
                    exploitability = final_fp_check.exploitability
                if hasattr(final_fp_check, 'corrected_priority'):
                    priority = final_fp_check.corrected_priority
            
            elif last_reflection.confidence_assessment == "contradictory":
                # Even with contradictions, if FP check is confident, use it
                if has_confident_fp_check:
                    verdict = "false_positive" if final_fp_check.is_false_positive else "true_positive"
                    console.print(f"[yellow]⚠ Reflection found contradictions, but FP check is confident: {verdict.upper()}[/yellow]")
                    if hasattr(final_fp_check, 'exploitability'):
                        exploitability = final_fp_check.exploitability
                    if hasattr(final_fp_check, 'corrected_priority'):
                        priority = final_fp_check.corrected_priority
                else:
                    verdict = "needs_review"
                    console.print(f"[yellow]⚠ Verdict: NEEDS REVIEW (reflection found contradictions, no confident FP check)[/yellow]")
            else:
                # Reflection requested refinement - check if we have other confident signals
                if has_confident_fp_check:
                    verdict = "false_positive" if final_fp_check.is_false_positive else "true_positive"
                    console.print(f"[green]✓ Verdict from FP check (reflection requested refinement but FP check confident): {verdict.upper()}[/green]")
                    if hasattr(final_fp_check, 'exploitability'):
                        exploitability = final_fp_check.exploitability
                    if hasattr(final_fp_check, 'corrected_priority'):
                        priority = final_fp_check.corrected_priority
                else:
                    console.print(f"[yellow]⚠ Reflection requested refinement and no confident FP check - defaulting to needs_review[/yellow]")
        
        # Then check false positive check results (if not already used above)
        elif final_fp_check:
            verdict = "false_positive" if final_fp_check.is_false_positive else "true_positive"
            console.print(f"[green]✓ Verdict from FP check: {verdict.upper()}[/green]")
            if hasattr(final_fp_check, 'exploitability'):
                exploitability = final_fp_check.exploitability
            if hasattr(final_fp_check, 'corrected_priority'):
                priority = final_fp_check.corrected_priority
        
        # Finally fall back to final report
        elif final_report:
            if hasattr(final_report, 'is_exploitable'):
                verdict = "true_positive" if final_report.is_exploitable else "false_positive"
                console.print(f"[green]✓ Verdict from final report: {verdict.upper()}[/green]")
                if hasattr(final_report, 'is_exploitable'):
                    exploitability = "exploitable" if final_report.is_exploitable else "not_exploitable"
                if hasattr(final_report, 'priority'):
                    priority = final_report.priority
            else:
                console.print(f"[yellow]⚠ Final report missing is_exploitable field - defaulting to needs_review[/yellow]")
        else:
            console.print(f"[yellow]⚠ No analysis results available - defaulting to needs_review[/yellow]")
        
        console.print(f"[cyan]Final determination: {verdict.upper()}[/cyan]")
        
        result = {
            "confidence_score": final_report.confidence if final_report else None,
            "verdict": verdict,
            "exploitability": exploitability,
            "priority": priority,
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
