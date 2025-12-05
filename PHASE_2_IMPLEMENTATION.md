# Phase 2: Reflection Agent Implementation

## Overview

Phase 2 introduces a **Reflection Agent** that analyzes the quality of vulnerability assessments and dynamically adjusts the workflow based on confidence levels and detected patterns. This is inspired by Trail of Bits' Buttercup architecture.

## Key Components

### 1. Reflection Agent (`src/agents/reflection_agent.py`)

A meta-agent that reviews analysis results and determines if refinement is needed.

**Key Features:**
- Analyzes uncertainty and contradictions in analysis results
- Detects common patterns indicating false positives or edge cases
- Returns structured commands for dynamic workflow routing
- Provides specific suggestions to improve confidence

**Detected Patterns:**
- `package_imported_not_used`: Package imported but vulnerable functions not called
- `only_in_tests`: Vulnerability only in test code, not production
- `hardcoded_values`: Vulnerable function called with safe hardcoded values
- `version_only_vulnerability`: Alert is version-based with no specific vulnerable function
- `dependency_of_dependency`: Transitive dependency with unclear usage
- `contradictory_reasoning`: Analysis reasoning contradicts the conclusion
- `insufficient_code_context`: Not enough code examined
- `missing_data_flow_analysis`: Need to trace user input to vulnerable code

### 2. Analysis Command Pattern (`AnalysisCommand` model)

Enables dynamic workflow routing through structured commands.

**Command Actions:**
- `accept_result`: Analysis is acceptable, proceed
- `retry_analysis`: Re-run deep analysis with refined context
- `search_more_code`: Need additional code pattern searching (future enhancement)
- `escalate_manual`: Too complex for automation, requires human review

**Command Structure:**
```python
class AnalysisCommand(BaseModel):
    action: Literal["retry_analysis", "search_more_code", "accept_result", "escalate_manual"]
    reason: str
    next_agent: Optional[str]  # Which agent to invoke next
    search_params: Optional[dict]  # Parameters for next search
    confidence_boost: Optional[str]  # Suggestions to improve confidence
```

### 3. Iterative Refinement Loop

The orchestrator now supports adaptive workflows with reflection-based refinement.

**Workflow:**
```
1. Code Analysis → Find vulnerable patterns
2. Deep Analysis → Assess exploitability
3. Reflection → Review analysis quality
   ├─ Accept → Proceed to False Positive Check
   ├─ Retry → Back to Deep Analysis with context
   ├─ Search → Add to context (future: trigger new search)
   └─ Escalate → Accept with manual review flag
4. False Positive Check (if exploitable)
5. Complete
```

**Configuration:**
- Max refinement iterations: 2 (configurable via `AnalysisState.max_refinement_iterations`)
- Max deep analyzer attempts: 3 (existing)
- Graceful degradation when limits reached

### 4. Enhanced State Tracking

Updated `AnalysisState` to track reflection attempts and results.

**New Fields:**
- `reflection_results`: List of all reflection assessments
- `reflection_agent_attempts`: Counter for reflection iterations
- `max_refinement_iterations`: Configurable limit (default: 2)

## How It Works

### Example Flow: Low Confidence Analysis

```
Alert: lodash prototype pollution vulnerability

Attempt 1: Deep Analysis
├─ Result: "is_exploitable: false, confidence: low"
└─ Reasoning: "Package is used but unclear if vulnerable functions are called"

Reflection 1:
├─ Assessment: "needs_improvement"
├─ Patterns: ["insufficient_code_context"]
├─ Command: "retry_analysis"
└─ Suggestions: "Focus on checking if _.template, _.merge, or _.set are used"

Attempt 2: Deep Analysis (with reflection context)
├─ Result: "is_exploitable: false, confidence: high"
└─ Reasoning: "Code search found no usage of _.template, _.merge, or _.set. Only _.get is used which is safe."

Reflection 2:
├─ Assessment: "acceptable"
├─ Command: "accept_result"
└─ Outcome: Analysis complete ✓
```

### Example Flow: Contradictory Reasoning

```
Attempt 1: Deep Analysis
├─ Result: "is_exploitable: true, confidence: medium"
└─ Reasoning: "Package is imported... but no vulnerable code paths found"

Reflection 1:
├─ Assessment: "contradictory"
├─ Patterns: ["contradictory_reasoning", "package_imported_not_used"]
├─ Command: "retry_analysis"
└─ Suggestions: "Clarify: if no vulnerable code paths exist, should be marked as not exploitable"

Attempt 2: Deep Analysis (with clarification)
├─ Result: "is_exploitable: false, confidence: high"
└─ Reasoning: "Package is imported but vulnerable functions are never called"

Reflection 2:
└─ Command: "accept_result" ✓
```

## Benefits

1. **Higher Confidence**: Reflection catches uncertain or contradictory analyses
2. **Adaptive Workflows**: Dynamic routing based on analysis quality
3. **Context Accumulation**: Each iteration builds on previous insights
4. **Pattern Detection**: Identifies common false positive scenarios
5. **Graceful Degradation**: Accepts results when refinement limits reached
6. **Observability**: All reflection decisions tracked in state

## Integration Points

### In Orchestrator (`workflow.py`)

```python
# After deep analysis completes
if report and state.should_retry("reflection_agent"):
    reflection = await self.reflection_agent.reflect(
        alert=alert,
        current_report=report,
        code_matches=state.code_matches,
        analysis_history=state.reports,
        attempt_count=attempt_num
    )

    # Act on reflection command
    if reflection.command.action == "retry_analysis":
        # Add reflection insights to context
        state.add_context(reflection.reasoning)
        # Loop back to deep analysis
        continue
    elif reflection.command.action == "accept_result":
        break
```

### Usage

No changes required for end users. The reflection agent runs automatically:

```bash
# Same command as before
python main.py analyze owner/repo

# Verbose mode shows reflection agent activity
python main.py analyze owner/repo --verbose
```

## Future Enhancements (Phase 3)

- **Dynamic Code Search**: Act on `search_more_code` commands
- **Tool System**: Provide reflection agent with structured tools (grep, dataflow, etc.)
- **Learning**: Track reflection patterns to improve future analyses
- **Parallel Analysis**: Run multiple analysis strategies in parallel

## Comparison with Buttercup

| Feature | Buttercup | Phase 2 Implementation |
|---------|-----------|----------------------|
| Reflection Agent | ✅ Yes | ✅ Yes |
| Command Pattern | ✅ Yes | ✅ Yes |
| State Preservation | ✅ Yes | ✅ Yes (Phase 1) |
| Iterative Refinement | ✅ Yes | ✅ Yes |
| Tool System | ✅ Structured tools | ⚠️ Future (Phase 3) |
| Dynamic Code Search | ✅ Yes | ⚠️ Future (Phase 3) |
| LangGraph State Machine | ✅ Yes | ❌ Not needed (simpler workflow) |

## Testing

Run the analyzer to see reflection in action:

```bash
# Test with a repo that has Dependabot alerts
python main.py analyze myorg/myrepo --verbose

# Watch for reflection agent messages:
# "🤔 Reflecting on analysis quality..."
# "🔄 Reflection suggests retry: ..."
# "✓ Reflection agent accepted analysis result"
```

## Metrics

The reflection agent tracks:
- `needs_refinement`: Boolean indicating if retry needed
- `confidence_assessment`: "acceptable" | "needs_improvement" | "contradictory"
- `detected_patterns`: List of patterns found
- `iteration`: Which refinement iteration (1 or 2)

All metrics stored in `AnalysisState.execution_history` for post-analysis review.

---

**Status**: ✅ Phase 2 Complete

**Next**: Phase 3 - Advanced Patterns (Tool System, Structured Capabilities)
