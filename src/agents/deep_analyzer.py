from typing import Optional, List
from pydantic import BaseModel
from rich.console import Console

from ..llm.client import LLMClient
from .alert_fetcher import DependabotAlert
from .code_analyzer import CodeMatch

console = Console()


class AnalysisReport(BaseModel):
    """Structured analysis report for a Dependabot alert"""
    alert_number: int
    package: str
    vulnerability_id: str
    is_exploitable: bool
    confidence: str  # "high", "medium", "low"
    reasoning: str
    impact_assessment: str
    code_paths_affected: list[str]
    test_case: Optional[str] = None
    recommended_action: str
    priority: str  # "critical", "high", "medium", "low"


class DeepAnalyzer:
    """
    Performs deep analysis of Dependabot alerts using LLM reasoning.
    Determines if vulnerabilities are actually exploitable in the codebase context.
    """

    def __init__(self, llm_client: LLMClient, verbose: bool = False):
        self.llm = llm_client
        self.verbose = verbose

    async def analyze(
        self,
        alert: DependabotAlert,
        code_context: str,
        code_matches: Optional[List[CodeMatch]] = None,
        previous_attempts: Optional[str] = None
    ) -> AnalysisReport:
        """
        Perform comprehensive analysis of a security alert.

        Args:
            alert: The Dependabot alert to analyze
            code_context: Relevant code showing how the dependency is used
            code_matches: Specific vulnerable code patterns found (optional)
            previous_attempts: Context from previous failed attempts (optional)

        Returns:
            AnalysisReport with exploitability assessment and recommendations
        """
        if self.verbose:
            console.print(f"\n[cyan]Analyzing alert #{alert.number}: {alert.package}[/cyan]")

        # Build analysis prompt
        prompt = self._build_analysis_prompt(alert, code_context, code_matches, previous_attempts)

        # Define expected response structure
        response_format = {
            "is_exploitable": "boolean (true or false, NOT a string)",
            "confidence": "string (high/medium/low)",
            "reasoning": "string",
            "impact_assessment": "string",
            "code_paths_affected": ["list of file paths or 'unknown'"],
            "test_case": "string or null",
            "recommended_action": "string",
            "priority": "string (critical/high/medium/low)"
        }

        # Retry logic for LLM failures
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Get structured analysis from LLM
                analysis = await self.llm.ask_structured(
                    prompt=prompt,
                    response_format=response_format,
                    system_prompt=self._get_system_prompt(),
                    max_tokens=4096 if attempt > 0 else 8192  # Reduce tokens on retry
                )

                report = AnalysisReport(
                    alert_number=alert.number,
                    package=alert.package,
                    vulnerability_id=alert.vulnerability_id,
                    is_exploitable=analysis["is_exploitable"],
                    confidence=analysis["confidence"],
                    reasoning=analysis["reasoning"][:2000] if len(analysis["reasoning"]) > 2000 else analysis["reasoning"],  # Truncate if too long
                    impact_assessment=analysis["impact_assessment"],
                    code_paths_affected=analysis["code_paths_affected"],
                    test_case=analysis.get("test_case"),
                    recommended_action=analysis["recommended_action"],
                    priority=analysis["priority"]
                )

                # Print summary
                status = "🔴 EXPLOITABLE" if report.is_exploitable else "🟢 NOT EXPLOITABLE"
                console.print(f"{status} (confidence: {report.confidence})")
                if self.verbose:
                    console.print(f"Priority: {report.priority}")

                return report

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    console.print(f"[yellow]Retry {attempt + 1}/{max_retries} due to error: {str(e)[:100]}[/yellow]")
                    continue
                else:
                    console.print(f"[red]Error during analysis after {max_retries} attempts: {str(e)[:200]}[/red]")
                    # Return a default "unknown" report instead of crashing
                    return AnalysisReport(
                        alert_number=alert.number,
                        package=alert.package,
                        vulnerability_id=alert.vulnerability_id,
                        is_exploitable=False,
                        confidence="low",
                        reasoning=f"Analysis failed due to LLM error: {str(last_error)[:500]}",
                        impact_assessment="Unable to assess - analysis failed",
                        code_paths_affected=["unknown"],
                        test_case=None,
                        recommended_action="Manual review required - automated analysis failed",
                        priority="medium"
                    )

    def _get_system_prompt(self) -> str:
        """System prompt defining the analyzer's role and approach"""
        return """You are a security analyst specializing in vulnerability assessment.

Your task is to analyze Dependabot security alerts and determine if they are actually exploitable in the specific codebase context.

Key principles:
1. Be skeptical - many Dependabot alerts are false positives or non-exploitable in practice
2. Consider the actual usage patterns - a vulnerability in a library doesn't matter if the vulnerable code path is never executed
3. Assess if user input can reach the vulnerable code
4. Consider defense-in-depth measures that may mitigate the issue
5. Provide clear, actionable reasoning

Focus on practical exploitability, not theoretical risk."""

    def _build_analysis_prompt(
        self,
        alert: DependabotAlert,
        code_context: str,
        code_matches: Optional[List[CodeMatch]] = None,
        previous_attempts: Optional[str] = None
    ) -> str:
        """Build the detailed analysis prompt"""

        # Format code matches if provided
        matches_section = ""
        if code_matches:
            matches_section = "\n## Vulnerable Code Patterns Found\n\n"
            matches_section += "The following specific vulnerable code patterns were identified:\n\n"
            for i, match in enumerate(code_matches[:5], 1):  # Limit to 5 matches
                matches_section += f"### Match {i}: {match.file_path}:{match.line_number}\n"
                matches_section += f"**Code**: `{match.code_snippet}`\n"
                matches_section += f"**Pattern**: {match.matched_pattern}\n"
                matches_section += f"**Context**:\n```\n{match.context}\n```\n\n"
        else:
            matches_section = "\n## Vulnerable Code Patterns\n\nNo specific vulnerable function usage patterns were found. This suggests the package may be imported but the vulnerable functions are not being used.\n\n"

        # Add previous attempts context if provided
        previous_context = ""
        if previous_attempts:
            previous_context = f"\n## Previous Analysis Attempts\n\n{previous_attempts}\n\nPlease take this context into account and provide a more accurate analysis.\n\n"

        return f"""Analyze this Dependabot security alert for actual exploitability:

## Vulnerability Details
- Package: {alert.package}
- Vulnerability ID: {alert.vulnerability_id}
- CVE: {alert.cve_id or 'N/A'}
- Severity: {alert.severity} (CVSS: {alert.cvss_score or 'N/A'})
- Summary: {alert.summary}

## Description
{alert.description}

## Version Information
- Affected versions: {alert.affected_versions}
- Patched versions: {alert.patched_versions or 'Not specified'}

{matches_section}

## General Code Context
{code_context}

{previous_context}

## Analysis Required

Perform a thorough analysis to determine:

1. **Exploitability**: Can this vulnerability actually be exploited in this codebase?
   - Is the vulnerable code path actually used?
   - Can attacker-controlled input reach the vulnerable code?
   - Are there any mitigating factors in how the package is used?

2. **Impact**: If exploitable, what's the real-world impact?
   - Data exposure?
   - Remote code execution?
   - Denial of service?
   - Limited to specific scenarios?

3. **Code Paths**: Which parts of the codebase are affected?
   - List specific files/functions if identifiable
   - Note if the dependency is only used in tests/dev

4. **Test Case**: If exploitable, provide a proof-of-concept test case or attack scenario

5. **Priority**: Based on exploitability and impact, what's the priority?
   - Critical: Actively exploitable, high impact
   - High: Likely exploitable, significant impact
   - Medium: Potentially exploitable, moderate impact
   - Low: Unlikely to be exploitable or low impact

6. **Recommended Action**:
   - Upgrade immediately?
   - Upgrade during next maintenance?
   - Monitor but defer?
   - Mark as false positive?

Provide your analysis in structured JSON format."""
