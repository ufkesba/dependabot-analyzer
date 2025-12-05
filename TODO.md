# TODO

## Agent Architecture Improvements (Inspired by Trail of Bits Buttercup)

### Phase 1: Quick Wins (1-2 days)

- [x] **Add Analysis State Tracking** ✅ COMPLETED
  - Created `AnalysisState` Pydantic model in `src/orchestrator/state.py`
  - Tracks: alert data, code matches, reports, retry counts, previous errors, accumulated context
  - Added execution history tracking with timestamps
  - Benefits: Enable learning from previous attempts, better error recovery

- [x] **Implement Retry with Context** ✅ COMPLETED
  - Added retry logic in orchestrator that learns from previous failures
  - Deep analyzer now receives `previous_attempts` parameter with accumulated context
  - Retries on low confidence (up to 3 attempts per agent)
  - Passes previous error messages and reasoning to subsequent attempts

- [x] **Add Confidence-Based Routing** ✅ COMPLETED
  - Automatically retries when Deep Analyzer returns "low" confidence
  - Retries once for "medium" confidence to try for higher confidence
  - Accumulated context from previous attempts improves subsequent analyses

### Phase 2: Reflection Agent (3-5 days)

- [x] **Create Reflection Agent** ✅ COMPLETED
  - Created `ReflectionAgent` class in `src/agents/reflection_agent.py`
  - Analyzes uncertain or contradictory results with LLM-powered meta-analysis
  - Detects patterns: "package_imported_not_used", "only_in_tests", "hardcoded_values", "version_only_vulnerability", etc.
  - Suggests next steps: retry analysis, search more code, accept result, or escalate to manual review
  - Returns `AnalysisCommand` objects for dynamic routing

- [x] **Implement Dynamic Workflow Routing** ✅ COMPLETED
  - Created `AnalysisCommand` Pydantic model with action types: retry_analysis, search_more_code, accept_result, escalate_manual
  - Integrated into orchestrator workflow with command interpretation
  - Supports branching: Deep Analyzer → Reflection → Deep Analyzer (with refined context)
  - Orchestrator acts on reflection commands adaptively

- [x] **Add Iterative Refinement** ✅ COMPLETED
  - Implemented reflection loop in `workflow.py` with max 2 refinement iterations (configurable)
  - Tracks reflection attempts in `AnalysisState`
  - Accumulates context from reflection insights (patterns detected, confidence boost suggestions)
  - Stops when: reflection accepts result, max iterations reached, or escalation recommended
  - Gracefully degrades when max attempts exceeded

### Phase 3: Advanced Patterns (1-2 weeks)

- [ ] **Implement Command Pattern**
  - Decouple agent decisions from execution
  - Agents return commands like: `AnalysisCommand(next_agent="code_analyzer", reason="need data flow")`
  - Orchestrator interprets and executes commands

- [ ] **Add Structured Tool System**
  - Create tool registry: GrepTool, DataFlowTool, CallGraphTool, TestDetectorTool
  - Make tools available to LLM agents via function calling
  - Log all tool usage for observability

- [ ] **Implement State Machine Workflow**
  - Consider LangGraph for complex conditional routing
  - Enable parallel execution of independent analysis steps
  - Add loop detection and circuit breakers

### Phase 4: Observability & Reliability (Optional)

- [ ] **Add Telemetry Integration**
  - OpenTelemetry spans for each agent execution
  - Track: execution time, success rates, confidence distributions, false positive rates
  - Export to monitoring system (Prometheus/Grafana)

- [ ] **Implement Graceful Degradation**
  - Return best-effort results when max retries reached
  - Add timeout handling for long-running analyses
  - Provide partial results with uncertainty indicators

- [ ] **Add Queue-Based Architecture (if scaling needed)**
  - Use Redis or asyncio.Queue for distributed processing
  - Enable multi-worker parallel analysis
  - Add task registry for tracking analysis lifecycle

### Code Quality Improvements

- [x] **Dynamic Vulnerability Pattern Extraction** ✅ COMPLETED
  - Added LLM-powered `extract_vulnerable_functions()` method to CodeAnalyzer
  - Automatically extracts vulnerable functions from alert descriptions
  - Falls back to LLM extraction when no hardcoded pattern exists
  - Handles cases where no specific functions are mentioned (version-only vulnerabilities)
  - Examples: Extracts `_.template` from "Command Injection via _.template()"

- [x] **Add More Vulnerability Patterns** ✅ PARTIALLY COMPLETED
  - Expanded `VULNERABILITY_PATTERNS` in `code_analyzer.py`
  - Added lodash patterns: GHSA-35jh-r3h4-6jhm (template), GHSA-29mw-wpgm-hmr9 (merge), GHSA-jf85-cpcp-j695 (zipObjectDeep)
  - Added axios pattern: GHSA-wf5p-g6vw-rhxx (data: URI DoS)
  - LLM extraction now covers packages without hardcoded patterns

- [ ] **Improve Data Flow Analysis**
  - Track user input sources: request params, env vars, file reads
  - Trace data flow to vulnerable function calls
  - Detect sanitization/validation that prevents exploitation

- [ ] **Enhance Test Detection**
  - Better heuristics for test vs production code
  - Detect: test files, example scripts, documentation code
  - Weight production code matches higher

### Buttercup Key Learnings Applied

**What Buttercup Does Well:**
1. **Reflection-Based Learning**: Dedicated agent analyzes failures and adjusts strategy
2. **Accumulated State**: All history preserved, enabling context-aware retries
3. **Dynamic Routing**: Agents decide next steps via Command pattern
4. **Tool System**: Structured capabilities (grep, get_function, get_callers, etc.)
5. **Fail-Safe Defaults**: Graceful degradation when retries exhausted
6. **Type Safety**: Pydantic models everywhere for validation

**What to Adopt:**
- ✅ State preservation across attempts (Phase 1)
- ✅ Reflection agent for uncertain results (Phase 2)
- ✅ Command-based routing (Phase 3)
- ⚠️ Tool system (Phase 3, if needed)
- ❌ Redis queues (only if scaling beyond single machine)
- ❌ LangGraph state machine (only if routing becomes complex)

**What Your Current Architecture Does Better:**
- Simpler for linear analysis workflows
- Easier to understand and debug
- Lower operational complexity
- Sufficient for most Dependabot alert analysis

### Documentation

- [ ] Update AGENTIC_WORKFLOW.md with new architecture decisions
- [ ] Document state management approach
- [ ] Add examples of reflection agent decision-making
- [ ] Create runbook for adding new vulnerability patterns

