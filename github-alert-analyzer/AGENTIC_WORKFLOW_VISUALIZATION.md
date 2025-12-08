# Agentic Workflow Visualization

This implementation adds comprehensive visualization of the agentic analysis workflow for GitHub Dependabot alerts.

## Overview

The system tracks and displays the execution of multiple AI agents that analyze security alerts, showing:
- Individual agent executions with timing and results
- Phase-based organization of the workflow
- Retry attempts and refinement iterations
- Success/failure tracking
- Code analysis results
- Final confidence scores and verdicts

## Architecture

### Backend Components

#### 1. Database Models (`app/models/agent_execution.py`)

**AnalysisWorkflow**
- Represents a complete analysis workflow for an alert
- Tracks overall status, timing, and summary metrics
- Stores final results (confidence score, verdict, etc.)
- Links to multiple agent executions

**AgentExecution**
- Individual agent execution within a workflow
- Records agent name, phase, execution order
- Stores output summary, structured data, and errors
- Tracks timing and attempt numbers

#### 2. API Schemas (`app/api/schemas/workflow.py`)

- `AgentExecutionResponse`: Individual agent execution details
- `AnalysisWorkflowResponse`: Workflow summary
- `AnalysisWorkflowDetailResponse`: Full workflow with all executions
- `WorkflowPhaseStats`: Statistics per phase
- `WorkflowSummary`: High-level workflow overview

#### 3. API Routes (`app/api/routes/workflows.py`)

**Endpoints:**
- `GET /api/workflows/{workflow_id}` - Get full workflow details
- `GET /api/workflows/{workflow_id}/summary` - Get workflow summary with phase stats
- `GET /api/workflows/alert/{alert_id}` - List all workflows for an alert
- `GET /api/workflows/{workflow_id}/executions` - Get agent executions (optionally filtered by phase)
- `GET /api/workflows/{workflow_id}/phases` - List all phases in workflow

### Frontend Components

#### 1. Components

**AgentExecutionCard** (`src/components/AgentExecutionCard.tsx`)
- Displays individual agent execution
- Shows status, timing, output, and errors
- Expandable to view detailed information
- Color-coded by success/failure status

**WorkflowTimeline** (`src/components/WorkflowTimeline.tsx`)
- Visualizes workflow as a vertical timeline
- Groups executions by phase
- Shows phase progression with visual connectors
- Displays phase-level success/failure

**WorkflowStats** (`src/components/WorkflowStats.tsx`)
- Summary statistics dashboard
- Displays key metrics (agents executed, success rate, etc.)
- Shows timing information
- Displays final confidence score and verdict
- Shows accumulated context from retries

#### 2. Pages

**Alert Detail Page** (`src/app/dashboard/alerts/[id]/page.tsx`)
- Displays alert information
- Lists all analysis workflows for the alert
- Clickable workflow cards showing status and metrics
- Button to start new analysis

**Workflow Detail Page** (`src/app/dashboard/workflows/[id]/page.tsx`)
- Full workflow visualization
- Shows alert context at top
- Displays workflow statistics
- Shows agent execution timeline
- Displays code context if available

## Data Flow

### During Analysis (needs integration)

```
Agentic Analysis Script
  ↓
Creates AnalysisWorkflow
  ↓
For each agent execution:
  - Create AgentExecution record
  - Set status to 'running'
  - Execute agent
  - Update with results
  - Increment workflow counters
  ↓
Update final workflow results
```

### Viewing Workflow

```
User clicks alert
  ↓
Fetch alert details + workflows
  ↓
Display workflows list
  ↓
User clicks workflow
  ↓
Fetch full workflow with executions
  ↓
Display timeline visualization
```

## Workflow Phases

The system tracks these phases:

1. **initial** - Workflow initialization
2. **code_analysis** - Code pattern search and analysis
3. **deep_analysis** - Deep vulnerability analysis
4. **reflection** - Reflection agent reviewing results
5. **fp_check** - False positive checking
6. **completed** - Successfully completed
7. **failed** - Failed execution

## Agent Types

The system tracks these agents:

- `alert_fetcher` - Fetches alert data from GitHub
- `code_analyzer` - Searches for vulnerable code patterns
- `deep_analyzer` - Performs detailed vulnerability analysis
- `false_positive_checker` - Determines if alert is false positive
- `reflection_agent` - Reviews and suggests refinements

## Integration with Existing Agentic Workflow

To integrate with the existing analysis script (`src/orchestrator/workflow.py`), you need to:

1. **Import the models and database session**
```python
from app.models import AnalysisWorkflow, AgentExecution
from app.core.database import SessionLocal
```

2. **Create workflow at start**
```python
def _process_alert_with_state(self, state: AnalysisState) -> AnalysisState:
    db = SessionLocal()
    
    # Create workflow record
    workflow = AnalysisWorkflow(
        alert_id=alert.id,  # Map from DependabotAlert to DB Alert
        status="running",
        current_phase="initial",
        started_at=datetime.now(timezone.utc)
    )
    db.add(workflow)
    db.commit()
```

3. **Record each agent execution**
```python
# Before agent execution
execution = AgentExecution(
    analysis_workflow_id=workflow.id,
    agent_name="code_analyzer",
    execution_order=state.code_analyzer_attempts,
    phase="code_analysis",
    status="running",
    started_at=datetime.now(timezone.utc),
    attempt_number=state.code_analyzer_attempts
)
db.add(execution)
db.commit()

# After agent execution
execution.completed_at = datetime.now(timezone.utc)
execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
execution.success = True  # or False
execution.output_summary = "Found 5 vulnerable code patterns"
execution.output_data = {"matches": len(code_matches), "files": files}
execution.status = "completed"
db.commit()
```

4. **Update workflow on completion**
```python
workflow.status = "completed"
workflow.completed_at = datetime.now(timezone.utc)
workflow.total_duration_seconds = (workflow.completed_at - workflow.started_at).total_seconds()
workflow.final_confidence_score = report.confidence
workflow.final_verdict = "false_positive" if fp_check.is_false_positive else "true_positive"
db.commit()
```

## Database Schema

The new tables will be automatically created when the backend starts:

- `analysis_workflows` - Workflow records
- `agent_executions` - Individual agent execution records

Both tables include foreign key relationships to existing `alerts` table.

## Usage

### Backend

Start the backend server:
```bash
cd github-alert-analyzer/backend
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

Start the frontend:
```bash
cd github-alert-analyzer/frontend
npm run dev
```

### Navigation

1. Go to `/dashboard/alerts`
2. Click on any alert
3. View workflow list or start new analysis
4. Click on a workflow to see detailed execution timeline

## Features

- ✅ Real-time workflow status tracking
- ✅ Phase-based visualization
- ✅ Agent execution details with timing
- ✅ Error tracking and display
- ✅ Retry and refinement tracking
- ✅ Success rate metrics
- ✅ Code analysis results display
- ✅ Confidence scoring
- ✅ Interactive timeline with expandable details
- ✅ Clean, modern UI with color-coded status

## Future Enhancements

- [ ] Real-time updates via WebSocket
- [ ] Workflow comparison view
- [ ] Export workflow results
- [ ] Trigger new analysis from UI
- [ ] Filter and search workflows
- [ ] Workflow templates
- [ ] Performance metrics and insights
