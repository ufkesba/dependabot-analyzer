# Agentic Workflow for Dependabot Alert Analysis

## Overview

The Dependabot Alert Analyzer uses a multi-agent workflow to accurately assess security vulnerabilities and reduce false positives. The workflow consists of four specialized agents working together:

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
│  False Positive     │  Critical validation of findings
│  Checker            │
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

### 4. False Positive Checker Agent

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
- Get basic code context

### Step 2: Search for Vulnerable Patterns
```python
code_matches = code_analyzer.find_vulnerable_usage(
    package_name=alert.package,
    vulnerability_id=alert.vulnerability_id
)
```

### Step 3: Deep Analysis
```python
report = analyzer.analyze(
    alert=alert,
    code_context=code_context,
    code_matches=code_matches  # NEW: Specific vulnerable patterns
)
```

### Step 4: False Positive Check
```python
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

## Key Improvements Over v1

### Problem: Axios Alert #8 False Positive

**v1 Behavior**:
- Found `axios` in test script
- Reported as HIGH priority exploitable
- Recommended immediate upgrade

**v2 Behavior with Agentic Workflow**:
1. **Code Analyzer**: Searches for `axios.get()` calls with `data:` URIs
2. **Deep Analyzer**: Receives both generic context AND specific pattern matches
3. **False Positive Checker**: Notices only match is in test curl command
4. **Result**: Correctly identifies as false positive

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

```
Alert 1/10: axios

[1/5] Searching for vulnerable code patterns...
Found 0 vulnerable usage patterns in 23 files

[2/5] Analyzing general code usage...
Package found in: package.json, test-ssrf.sh

[3/5] Running deep AI analysis...
Status: 🟢 NOT EXPLOITABLE
Priority: low
Confidence: high

[4/5] Running false positive check...
✓ Confirmed as false positive

Analysis Result:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  FALSE POSITIVE DETECTED (confidence: high)

False Positive Reasoning:
No vulnerable code patterns found in production code. The package
is listed in package.json but vulnerable functions (axios with
data: URIs) are never called. Only test scripts use axios.

Recommended Action:
Mark as false positive. No immediate action required.
```

---

## Benefits of This Approach

1. **Reduced False Positives**: Multi-layer validation catches incorrect assessments
2. **Specific Evidence**: Shows exact lines of vulnerable code
3. **Context-Aware**: Understands difference between test and production code
4. **Extensible**: Easy to add new vulnerability patterns
5. **Transparent**: Shows reasoning at each step

---

## Future Enhancements

- [ ] Add more vulnerability patterns for common packages
- [ ] Integrate with static analysis tools (e.g., Semgrep)
- [ ] Add data flow analysis to track user input to vulnerable functions
- [ ] Machine learning to identify new vulnerable patterns
- [ ] Integration with CI/CD for automated analysis
