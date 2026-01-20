from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict
from app.services.firestore import FirestoreService

# Internal models with ID field
class RepositoryModel(BaseModel):
    id: str
    user_id: str
    github_repo_id: int
    full_name: str
    description: Optional[str] = None
    is_private: bool = False
    is_monitored: bool = True
    primary_language: Optional[str] = None
    sync_status: str = "pending"
    last_synced_at: Optional[datetime] = None
    alert_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AlertModel(BaseModel):
    id: str
    repository_id: str
    github_alert_number: int
    package_name: str
    package_ecosystem: str
    manifest_path: Optional[str] = None
    severity: str
    state: str = "open"
    vulnerable_version_range: Optional[str] = None
    patched_version: Optional[str] = None
    github_created_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    dismissed_by: Optional[str] = None
    dismissed_reason: Optional[str] = None
    fixed_at: Optional[datetime] = None
    risk_status: Optional[str] = None
    exploitability_level: Optional[str] = None
    action_priority: Optional[str] = None
    analysis_confidence: Optional[float] = None
    last_analyzed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkflowModel(BaseModel):
    id: str
    alert_id: str
    status: str = "pending"
    current_phase: Optional[str] = None
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
    final_summary: Optional[str] = None
    accumulated_context: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None
    code_matches_found: int = 0
    code_context: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RepositoryFirestoreService(FirestoreService[RepositoryModel]):
    def __init__(self):
        super().__init__("repositories", RepositoryModel)

    async def get_by_user(self, user_id: str) -> List[RepositoryModel]:
        return await self.list(filters=[("user_id", "==", user_id)])

class AlertFirestoreService(FirestoreService[AlertModel]):
    def __init__(self):
        super().__init__("alerts", AlertModel)

    async def get_by_repository(self, repository_id: str) -> List[AlertModel]:
        return await self.list(filters=[("repository_id", "==", repository_id)])

class WorkflowFirestoreService(FirestoreService[WorkflowModel]):
    def __init__(self):
        super().__init__("workflows", WorkflowModel)

    async def get_by_alert(self, alert_id: str) -> List[WorkflowModel]:
        return await self.list(filters=[("alert_id", "==", alert_id)])

class AlertAnalysisModel(BaseModel):
    id: str
    alert_id: str
    llm_config_id: Optional[str] = None
    llm_provider: str
    llm_model: str
    status: str = "pending"
    analysis_result: Optional[str] = None
    raw_response: Optional[str] = None
    confidence_score: Optional[float] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    processing_time_seconds: Optional[float] = None
    error_message: Optional[str] = None
    analyzed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AlertAnalysisFirestoreService(FirestoreService[AlertAnalysisModel]):
    def __init__(self):
        super().__init__("alert_analyses", AlertAnalysisModel)

    async def get_by_alert(self, alert_id: str) -> List[AlertAnalysisModel]:
        return await self.list(filters=[("alert_id", "==", alert_id)], order_by="created_at")

class AgentExecutionModel(BaseModel):
    id: str
    analysis_workflow_id: str
    agent_name: str
    execution_order: int
    phase: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    success: bool = False
    output_summary: Optional[str] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    attempt_number: int = 1
    extra_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AgentExecutionFirestoreService(FirestoreService[AgentExecutionModel]):
    def __init__(self):
        super().__init__("agent_executions", AgentExecutionModel)

    async def get_by_workflow(self, workflow_id: str) -> List[AgentExecutionModel]:
        return await self.list(filters=[("analysis_workflow_id", "==", workflow_id)], order_by="execution_order")

class LLMConfigModel(BaseModel):
    id: str
    user_id: str
    provider: str
    api_key: str
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    is_default: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LLMConfigFirestoreService(FirestoreService[LLMConfigModel]):
    def __init__(self):
        super().__init__("llm_configurations", LLMConfigModel)

    async def get_by_user(self, user_id: str) -> List[LLMConfigModel]:
        return await self.list(filters=[("user_id", "==", user_id)])

repository_service = RepositoryFirestoreService()
alert_service = AlertFirestoreService()
workflow_service = WorkflowFirestoreService()
execution_service = AgentExecutionFirestoreService()
analysis_service = AlertAnalysisFirestoreService()
llm_config_service = LLMConfigFirestoreService()
