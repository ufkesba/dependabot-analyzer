# CLAUDE.md - Project Guide for Claude Code

This document provides context for AI assistants working on this codebase.

## Project Overview

**Dependabot Alert Analyzer** is an AI-powered security tool that analyzes GitHub Dependabot alerts to determine actual exploitability. It reduces false positives by checking whether vulnerable code paths are actually executed in the codebase.

### Problem Being Solved

Dependabot generates many false positives. A vulnerability in a library doesn't matter if:
- The vulnerable function is never called
- The code is only in tests
- Attacker input can't reach the vulnerable code
- The vulnerable code path is behind other mitigations

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Orchestrator                             │
│                    (src/orchestrator/workflow.py)                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Alert Fetcher │   │ Code Analyzer │   │ Deep Analyzer │
│  (GitHub API) │   │(Pattern Match)│   │  (LLM-based)  │
└───────────────┘   └───────────────┘   └───────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Reflection   │   │ False Positive│   │   Analysis    │
│    Agent      │   │    Checker    │   │     State     │
└───────────────┘   └───────────────┘   └───────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point with typer commands |
| `src/orchestrator/workflow.py` | Main orchestrator coordinating all agents |
| `src/orchestrator/state.py` | Analysis state tracking and retry management |
| `src/agents/alert_fetcher.py` | GitHub API integration, lock file parsing, monorepo detection |
| `src/agents/code_analyzer.py` | Vulnerable code pattern searching (scoped to manifest directory) |
| `src/agents/deep_analyzer.py` | LLM-powered exploitability assessment |
| `src/agents/reflection_agent.py` | Quality meta-analysis & workflow routing |
| `src/agents/false_positive_checker.py` | Validation of exploitable findings |
| `src/llm/client.py` | Multi-provider LLM wrapper (Anthropic, Google, OpenAI) |

## Data Flow

```
GitHub Dependabot Alert
        │
        ▼
[Alert Fetcher] ──► Fetch alerts + manifest files + lock file info
        │
        ▼
[Code Analyzer] ──► Search for vulnerable function patterns
        │           (scoped to manifest directory for monorepos)
        ▼
[Deep Analyzer] ──► LLM analysis of exploitability
        │
        ▼
[Reflection Agent] ──► Quality check, may trigger retry
        │
        ▼
[False Positive Checker] ──► Validate exploitable findings
        │
        ▼
    JSON Report
```

## Monorepo Support

The analyzer supports monorepos by scoping searches to the directory containing the manifest file:

- Alert for `services/serviceA/package.json` → only searches `services/serviceA/`
- Alert for root `package.json` → searches entire repo

Key function: `get_search_scope_from_manifest()` in `alert_fetcher.py`

Monorepo tooling detection:
- npm/yarn workspaces
- lerna.json
- pnpm-workspace.yaml
- nx.json
- turbo.json

## LLM Integration

The `LLMClient` in `src/llm/client.py` supports:
- **Anthropic Claude** (default) - `claude-haiku-4-5-20251001`, `claude-sonnet-4-20250514`
- **Google Gemini** - `gemini-2.0-flash-exp`
- **OpenAI GPT** - `gpt-4o`

Key method: `ask_structured()` - Returns JSON-parsed responses with retry logic.

## Common Tasks

### Adding a New Vulnerability Pattern

Edit `src/agents/code_analyzer.py`, add to `VULNERABILITY_PATTERNS`:

```python
"package-name": {
    "GHSA-xxxx-yyyy-zzzz": VulnerabilityPattern(
        package="package-name",
        vulnerability_id="GHSA-xxxx-yyyy-zzzz",
        vulnerable_functions=["functionName"],
        patterns=[r"functionName\("],
        description="Description of vulnerability",
        indicators=["user input", "req.body"]
    )
}
```

### Adding a New Agent

1. Create file in `src/agents/`
2. Follow pattern from existing agents (Pydantic models for I/O)
3. Add to orchestrator workflow in `src/orchestrator/workflow.py`
4. Update state tracking in `src/orchestrator/state.py` if needed

### Modifying the Analysis Prompt

Edit `_build_analysis_prompt()` in `src/agents/deep_analyzer.py`

## Testing

```bash
# Run a single alert analysis with verbose output
python main.py analyze-alert owner/repo 42 -v

# Run against a monorepo
python main.py analyze owner/monorepo --max-files 200 -v
```

## Environment Variables

```bash
GITHUB_TOKEN=        # Required - needs 'repo' scope
ANTHROPIC_API_KEY=   # For Claude
GOOGLE_API_KEY=      # For Gemini
OPENAI_API_KEY=      # For GPT
```

## Web Application

The `github-alert-analyzer/` directory contains a full-stack web app:
- **Backend**: FastAPI (`github-alert-analyzer/backend/`)
- **Frontend**: Next.js 15 (`github-alert-analyzer/frontend/`)
- **Database**: PostgreSQL via Supabase

The web app wraps the CLI analysis with:
- User authentication (JWT + GitHub OAuth)
- Persistent analysis history
- Dashboard with statistics
- Workflow execution visualization

## Code Style

- Python 3.11+
- Pydantic for data models
- async/await for I/O operations
- Rich for console output
- Type hints throughout

## Important Patterns

### State Accumulation
Failed analysis attempts feed context to retries via `AnalysisState.add_context()`

### Scoped Search
`CodeAnalyzer` accepts `search_scope` parameter to limit file searches for monorepos

### Reflection Loop
`ReflectionAgent` can route analysis back for retry with accumulated insights

### False Positive Validation
Extra skeptical check on findings marked as exploitable
