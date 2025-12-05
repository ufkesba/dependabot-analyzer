# Agentic Workflow for Dependabot Alert Analysis

## Overview

The Dependabot Alert Analyzer uses a multi-agent workflow to accurately assess security vulnerabilities and reduce false positives. The workflow consists of five specialized agents working together, with an adaptive reflection layer for quality assurance:

## Agent Architecture

```
┌─────────────────────┐
│  Alert Fetcher      │  Fetches alerts from GitHub
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Code Analyzer      │  Searches for vulnerable code patterns
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Deep Analyzer      │  LLM-based exploitability analysis
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Reflection Agent   │  Analyzes result quality & suggests refinements
└──────────┬──────────┘
           │ (may loop back to Deep Analyzer)
           ▼
┌─────────────────────┐
│  False Positive     │  Critical validation of findings
│  Checker            │  (only for exploitable alerts)
└─────────────────────┘
```

## Agent Descriptions

### 1. Alert Fetcher Agent

**Purpose**: Retrieves Dependabot security alerts from GitHub repositories

**Key Functions**:
- Fetches alerts via GitHub API
- Filters by severity, state
- Retrieves basic code context (manifest files, imports)

**Limitations**:
- Only does generic package search
- Cannot distinguish between test and production code
- Doesn't understand vulnerable function usage patterns

---

### 2. Code Analyzer Agent

**Purpose**: Searches for actual vulnerable function usage patterns in the codebase

**Key Functions**:
- Pattern-based search for vulnerable code
- Knows specific vulnerable functions for common packages
- Filters out test code and comments
- Provides line-by-line context of vulnerable usage

**Example Patterns**:
```python
VULNERABILITY_PATTERNS = {
    "axios": {
        "GHSA-wf5p-g6vw-rhxx": VulnerabilityPattern(
            vulnerable_functions=["axios.get", "axios.post"],
            patterns=[
                r"axios\.get\(['\"]data:",  # Direct data: URI usage
                r"axios\([^)]*url[^)]*data:",  # URL parameter with data:
            ],
            description="Axios data: URI DoS vulnerability"
        )
    }
}
```

**Benefits**:
- Finds ACTUAL vulnerable code, not just package imports
- Distinguishes between production and test code
- Provides specific line numbers and context

**Example Output**:
```
Match 1: src/api/fetcher.js:42
Code: `const response = await axios.get(userProvidedUrl)`
Context:
  async function fetchData(url) {
    // User input flows here - VULNERABLE!
    const response = await axios.get(userProvidedUrl)
    return response.data
  }
```

---

### 3. Deep Analyzer Agent

**Purpose**: LLM-based analysis to determine exploitability

**Key Functions**:
- Analyzes vulnerability details
- Considers code context and patterns
- Assesses real-world exploitability
- Determines priority and impact

**Enhanced Prompt Structure**:
```markdown
## Vulnerability Details
- Package, CVE, CVSS score, description

## Vulnerable Code Patterns Found
- Specific matches with line numbers
- Code snippets and context
- Pattern that triggered the match

## General Code Context
- How the package is imported/used
- Manifest files

## Analysis Required
- Is it exploitable?
- Can attacker-controlled input reach vulnerable code?
- What's the real-world impact?
```

**Improvements Over v1**:
- Now receives specific vulnerable code matches
- Can distinguish "package used" from "vulnerable function called"
- Considers whether code is in tests vs production

---

### 4. Reflection Agent (Phase 2)

**Purpose**: Meta-analysis of assessment quality with dynamic workflow routing

**Key Functions**:
- Reviews analysis results for uncertainty or contradictions
- Detects common false positive patterns
- Suggests specific improvements or next steps
- Routes workflow adaptively (retry, accept, escalate)

**Pattern Detection**:
```python
detected_patterns = [
    "package_imported_not_used",      # Package imported but vulnerable functions never called
    "only_in_tests",                  # Vulnerability only in test code
    "hardcoded_values",               # Vulnerable function called with safe hardcoded values
    "version_only_vulnerability",     # Alert is version-based with no specific vulnerable function
    "contradictory_reasoning",        # Analysis reasoning contradicts conclusion
    "insufficient_code_context",      # Not enough code examined
]
```

**Command Actions**:
- `accept_result`: Analysis quality is acceptable, proceed
- `retry_analysis`: Re-analyze with refined context and suggestions
- `search_more_code`: Need additional code searching (future enhancement)
- `escalate_manual`: Too complex, requires human review

**Example Reflection**:
```
Initial Analysis:
  🟢 NOT EXPLOITABLE (confidence: low)
  Reasoning: "Package is used but unclear if vulnerable functions are called"

Reflection Assessment:
  Confidence: needs_improvement
  Patterns: ["insufficient_code_context"]
  Command: retry_analysis
  Suggestions: "Focus on checking if _.template, _.merge, or _.set are used"

Refined Analysis (attempt 2):
  🟢 NOT EXPLOITABLE (confidence: high)
  Reasoning: "Code search found no usage of _.template, _.merge, or _.set. Only _.get is used which is safe."

Reflection Assessment:
  Confidence: acceptable
  Command: accept_result ✓
```

**Benefits**:
- Catches uncertain or contradictory analyses
- Provides specific improvement suggestions
- Adaptive workflow based on quality assessment
- Reduces manual review burden

---

### 5. False Positive Checker Agent

**Purpose**: Critical validation layer that challenges the deep analyzer's findings

**Key Principles**:
- **Skeptical by default**: Assumes findings might be false positives
- **Evidence-based**: Only confirms vulnerabilities with clear evidence
- **Context-aware**: Considers how code is actually used

**Common False Positive Patterns**:
1. ❌ Package used but vulnerable functions never called
2. ❌ Vulnerable functions called with hardcoded/safe values
3. ❌ Usage only in test files, scripts, or examples
4. ❌ Vulnerability requires conditions that don't exist
5. ❌ User input cannot reach vulnerable code path

**Example Validation**:

**Before False Positive Check**:
```
Alert #8: axios GHSA-wf5p-g6vw-rhxx
Priority: HIGH
Confidence: high
Reasoning: The application uses axios...
```

**After False Positive Check**:
```
⚠️ FALSE POSITIVE DETECTED (confidence: high)

Reasoning:
While axios is imported in the project, the only usage found is in a
test script (test-ssrf.sh) using curl to test the endpoint. The actual
application code in src/ does not call axios at all. The vulnerable
data: URI handling is never invoked in production code.

Corrected Priority: LOW
Corrected Exploitability: false
```

---

## Workflow Steps

For each Dependabot alert:

### Step 1: Fetch Alert
- Retrieve alert details from GitHub
- Get basic code context (manifest files, dependency info)

### Step 2: Search for Vulnerable Patterns
```python
code_matches = code_analyzer.find_vulnerable_usage(
    package_name=alert.package,
    vulnerability_id=alert.vulnerability_id
)
```
- Uses hardcoded patterns for known vulnerabilities
- Falls back to LLM extraction for unknown vulnerabilities
- Returns specific line numbers and code snippets

### Step 3: Deep Analysis with Reflection
```python
# Initial analysis
report = analyzer.analyze(
    alert=alert,
    code_context=code_context,
    code_matches=code_matches
)

# Reflection check (up to 2 iterations)
reflection = reflection_agent.reflect(
    alert=alert,
    current_report=report,
    code_matches=code_matches,
    analysis_history=previous_reports,
    attempt_count=current_attempt
)

# Act on reflection command
if reflection.command.action == "retry_analysis":
    # Add reflection insights to accumulated context
    # Loop back to Deep Analysis with refined guidance
    ...
elif reflection.command.action == "accept_result":
    # Proceed to next phase
    ...
```

### Step 4: False Positive Check (Only for Exploitable Alerts)
```python
if report.is_exploitable:
    fp_check = false_positive_checker.check(
        initial_report=report,
        code_matches=code_matches,
        vulnerability_details=alert.description
    )
```

### Step 5: Apply Corrections
```python
if fp_check.is_false_positive:
    report = false_positive_checker.validate_and_correct(report, fp_check)
```

---

## Key Improvements

### Phase 1: Code Pattern Search
- ✅ Specific vulnerable function detection
- ✅ LLM-powered pattern extraction for unknown vulnerabilities
- ✅ Distinguishes test vs. production code

### Phase 2: Reflection & Iterative Refinement
- ✅ Adaptive workflow routing based on confidence
- ✅ Pattern detection for common false positive scenarios
- ✅ Context accumulation across analysis attempts
- ✅ Graceful degradation when limits reached

## Key Improvements Over v1

### Problem: Axios Alert #8 False Positive

**v1 Behavior**:
- Found `axios` in test script
- Reported as HIGH priority exploitable
- Recommended immediate upgrade

**v2 Behavior with Agentic Workflow**:
1. **Code Analyzer**: Searches for `axios.get()` calls with `data:` URIs
2. **Deep Analyzer**: Receives both generic context AND specific pattern matches
3. **Reflection Agent**: Reviews confidence and suggests improvements if needed
4. **False Positive Checker**: Notices only match is in test curl command
5. **Result**: Correctly identifies as false positive

### Before:
```bash
Alert #8: axios
  Priority: high
  Reasoning: The application uses axios to fetch data from URLs...
```

### After:
```bash
Alert #8: axios
  Priority: low
  ⚠️  FALSE POSITIVE DETECTED (confidence: high)

  Reasoning: Package is imported but vulnerable functions are not called
  in production code. Only usage is in test/example scripts.
```

---

## Adding New Vulnerability Patterns

To improve detection for a specific vulnerability:

1. **Add to `code_analyzer.py`**:
```python
VULNERABILITY_PATTERNS = {
    "package-name": {
        "VULN-ID": VulnerabilityPattern(
            package="package-name",
            vulnerability_id="GHSA-xxxx-xxxx-xxxx",
            vulnerable_functions=["func1", "func2"],
            patterns=[
                r"regex_pattern_1",
                r"regex_pattern_2",
            ],
            description="Brief description",
            indicators=["user input", "external data"]
        )
    }
}
```

2. **Test the pattern**:
```python
matches = code_analyzer.find_vulnerable_usage(
    package_name="package-name",
    vulnerability_id="GHSA-xxxx-xxxx-xxxx"
)
```

---

## Example: Full Analysis Output

### Non-Verbose Mode (Default)
```
Alert 1/28
🟢 NOT EXPLOITABLE (confidence: high)

Alert 2/28
🔴 EXPLOITABLE (confidence: high)
⚠️  Identified as FALSE POSITIVE (confidence: high)

Alert 3/28
🟢 NOT EXPLOITABLE (confidence: medium)
```

### Verbose Mode (--verbose)
```
Alert 1/10: axios

━━━ Phase 1: Code Pattern Search ━━━
Searching for vulnerable usage of axios...
No hardcoded pattern found, using LLM to extract vulnerable functions...
LLM extracted 2 vulnerable functions
Found 0 potential vulnerable usage patterns in 23 files
→ Fetching code context (manifest files, dependency info)

━━━ Phase 2: Deep Analysis ━━━

Analyzing alert #1: axios
🟢 NOT EXPLOITABLE (confidence: high)
Priority: low

━━━ Reflection Check (iteration 1) ━━━
🤔 Reflecting on analysis quality...
Confidence: acceptable
Needs refinement: False
Patterns detected: package_imported_not_used
Recommended action: accept_result
✓ Reflection agent accepted analysis result

Analysis complete.
```

---

## Benefits of This Approach

1. **Reduced False Positives**: Multi-layer validation catches incorrect assessments
2. **Adaptive Quality Control**: Reflection agent ensures high-confidence results
3. **Iterative Refinement**: Automatically retries with improved context when needed
4. **Specific Evidence**: Shows exact lines of vulnerable code
5. **Context-Aware**: Understands difference between test and production code
6. **Extensible**: Easy to add new vulnerability patterns
7. **Transparent**: Shows reasoning at each step (in verbose mode)
8. **Clean Output**: Concise results by default, detailed info when needed

---

## Future Enhancements

### Phase 3 (Planned)
- [ ] **Structured Tool System**: Give agents access to tools (grep, dataflow analysis, call graphs)
- [ ] **Dynamic Code Search**: Act on reflection `search_more_code` commands
- [ ] **Command Pattern Extensions**: More sophisticated agent routing

### Long Term
- [ ] Add more vulnerability patterns for common packages
- [ ] Integrate with static analysis tools (e.g., Semgrep)
- [ ] Add data flow analysis to track user input to vulnerable functions
- [ ] Machine learning to identify new vulnerable patterns
- [ ] Integration with CI/CD for automated analysis
- [ ] Learning from past false positives

## Related Documentation

- [PHASE_2_IMPLEMENTATION.md](./PHASE_2_IMPLEMENTATION.md) - Detailed Phase 2 implementation notes
- [TODO.md](./TODO.md) - Roadmap for future phases
