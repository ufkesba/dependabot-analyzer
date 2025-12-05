"""
State management for analysis workflow.
Tracks history, retries, and accumulated context across agent invocations.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from ..agents.alert_fetcher import DependabotAlert
from ..agents.deep_analyzer import AnalysisReport
from ..agents.code_analyzer import CodeMatch
from ..agents.false_positive_checker import FalsePositiveCheck


class AgentExecution(BaseModel):
    """Record of a single agent execution"""
    agent_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalysisState(BaseModel):
    """
    Centralized state object that flows through all agents.
    Preserves history and enables learning from previous attempts.
    """
    # Core data
    alert: DependabotAlert

    # Accumulated results
    code_matches: List[CodeMatch] = Field(default_factory=list)
    code_context: Optional[str] = None
    reports: List[AnalysisReport] = Field(default_factory=list)
    false_positive_checks: List[FalsePositiveCheck] = Field(default_factory=list)

    # Retry tracking
    code_analyzer_attempts: int = 0
    deep_analyzer_attempts: int = 0
    false_positive_checker_attempts: int = 0
    max_retries_per_agent: int = 3

    # Execution history
    execution_history: List[AgentExecution] = Field(default_factory=list)
    accumulated_context: str = ""  # Context from previous failed attempts

    # Workflow state
    current_phase: str = "initial"  # initial, code_analysis, deep_analysis, fp_check, completed, failed
    needs_retry: bool = False
    retry_reason: Optional[str] = None

    # Final result
    final_report: Optional[AnalysisReport] = None
    final_fp_check: Optional[FalsePositiveCheck] = None

    class Config:
        arbitrary_types_allowed = True

    def add_execution(
        self,
        agent_name: str,
        success: bool,
        error_message: Optional[str] = None,
        **metadata
    ) -> None:
        """Record an agent execution"""
        execution = AgentExecution(
            agent_name=agent_name,
            success=success,
            error_message=error_message,
            metadata=metadata
        )
        self.execution_history.append(execution)

    def should_retry(self, agent_name: str) -> bool:
        """Check if agent should retry based on attempt count"""
        attempt_map = {
            "code_analyzer": self.code_analyzer_attempts,
            "deep_analyzer": self.deep_analyzer_attempts,
            "false_positive_checker": self.false_positive_checker_attempts,
        }
        attempts = attempt_map.get(agent_name, 0)
        return attempts < self.max_retries_per_agent

    def increment_attempts(self, agent_name: str) -> None:
        """Increment retry counter for an agent"""
        if agent_name == "code_analyzer":
            self.code_analyzer_attempts += 1
        elif agent_name == "deep_analyzer":
            self.deep_analyzer_attempts += 1
        elif agent_name == "false_positive_checker":
            self.false_positive_checker_attempts += 1

    def get_latest_report(self) -> Optional[AnalysisReport]:
        """Get the most recent analysis report"""
        return self.reports[-1] if self.reports else None

    def get_latest_fp_check(self) -> Optional[FalsePositiveCheck]:
        """Get the most recent false positive check"""
        return self.false_positive_checks[-1] if self.false_positive_checks else None

    def add_context(self, context: str) -> None:
        """Accumulate context from failed attempts for future retries"""
        if self.accumulated_context:
            self.accumulated_context += f"\n\n---\n\n{context}"
        else:
            self.accumulated_context = context

    def get_error_summary(self) -> str:
        """Get summary of all errors encountered"""
        errors = [
            f"- [{ex.agent_name}] {ex.error_message}"
            for ex in self.execution_history
            if not ex.success and ex.error_message
        ]
        return "\n".join(errors) if errors else "No errors recorded"

    def get_success_rate(self) -> float:
        """Calculate success rate of agent executions"""
        if not self.execution_history:
            return 1.0
        successful = sum(1 for ex in self.execution_history if ex.success)
        return successful / len(self.execution_history)
