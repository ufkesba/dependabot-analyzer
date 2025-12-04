"""
False positive checker that validates vulnerability findings.
Uses LLM to critically examine whether a flagged vulnerability is actually exploitable.
"""
from typing import Optional
from pydantic import BaseModel
from rich.console import Console

from ..llm.client import LLMClient
from .deep_analyzer import AnalysisReport
from .code_analyzer import CodeMatch

console = Console()


class FalsePositiveCheck(BaseModel):
    """Result of false positive analysis"""
    is_false_positive: bool
    confidence: str  # "high", "medium", "low"
    reasoning: str
    corrected_priority: Optional[str] = None
    corrected_exploitability: Optional[bool] = None


class FalsePositiveChecker:
    """
    Agent that critically examines vulnerability findings to identify false positives.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def check(
        self,
        initial_report: AnalysisReport,
        code_matches: list[CodeMatch],
        vulnerability_details: str
    ) -> FalsePositiveCheck:
        """
        Examine an analysis report to determine if it's a false positive.

        Args:
            initial_report: The initial vulnerability analysis
            code_matches: Actual code matches found
            vulnerability_details: Detailed vulnerability information

        Returns:
            FalsePositiveCheck with validation results
        """
        console.print(f"[cyan]Running false positive check for alert #{initial_report.alert_number}[/cyan]")

        prompt = self._build_check_prompt(initial_report, code_matches, vulnerability_details)

        response_format = {
            "is_false_positive": "boolean (true if this is a false positive, false if it's a real vulnerability)",
            "confidence": "string (high/medium/low)",
            "reasoning": "string (detailed explanation of the decision)",
            "corrected_priority": "string or null (critical/high/medium/low if priority needs correction)",
            "corrected_exploitability": "boolean or null (corrected value if initial assessment was wrong)"
        }

        try:
            result = await self.llm.ask_structured(
                prompt=prompt,
                response_format=response_format,
                system_prompt=self._get_system_prompt()
            )

            check = FalsePositiveCheck(
                is_false_positive=result["is_false_positive"],
                confidence=result["confidence"],
                reasoning=result["reasoning"],
                corrected_priority=result.get("corrected_priority"),
                corrected_exploitability=result.get("corrected_exploitability")
            )

            if check.is_false_positive:
                console.print(f"[yellow]⚠️  Identified as FALSE POSITIVE (confidence: {check.confidence})[/yellow]")
            else:
                console.print(f"[green]✓ Confirmed as legitimate vulnerability[/green]")

            return check

        except Exception as e:
            console.print(f"[red]Error during false positive check: {str(e)}[/red]")
            raise

    def _get_system_prompt(self) -> str:
        """System prompt for the false positive checker"""
        return """You are a critical security analyst specializing in identifying false positives in vulnerability reports.

Your role is to be SKEPTICAL and THOROUGH. Challenge assumptions made in vulnerability assessments.

Key principles:
1. **Evidence-based**: Only confirm vulnerabilities with clear evidence of exploitability
2. **Context matters**: Consider how the code is actually used, not just theoretical risks
3. **Test code is not vulnerable**: Usage in tests, examples, or documentation is NOT a vulnerability
4. **User input required**: Most vulnerabilities require attacker-controlled input to exploit
5. **Defense in depth**: Consider mitigations and protections in place

Common false positive patterns to watch for:
- Package is used, but vulnerable functions are not called
- Vulnerable functions are called, but with hardcoded/safe values
- Usage is only in test files, scripts, or development code
- The vulnerability requires specific conditions that don't exist in the codebase
- The vulnerability is in transitive dependencies not directly used
- The code path with vulnerability is never executed
- There are validations/sanitizations in place that prevent exploitation

Be thorough but fair. If there's genuine risk, confirm it. If it's a false positive, say so clearly."""

    def _build_check_prompt(
        self,
        initial_report: AnalysisReport,
        code_matches: list[CodeMatch],
        vulnerability_details: str
    ) -> str:
        """Build the prompt for false positive checking"""

        # Format code matches
        if code_matches:
            matches_text = "\n\n".join([
                f"**Match {i+1}**: {match.file_path}:{match.line_number}\n"
                f"Code: `{match.code_snippet}`\n"
                f"Context:\n```\n{match.context}\n```"
                for i, match in enumerate(code_matches[:5])  # Limit to 5 matches
            ])
        else:
            matches_text = "No specific vulnerable code patterns found."

        return f"""Critically examine this vulnerability finding to determine if it's a FALSE POSITIVE.

## Initial Analysis Report
- Alert #: {initial_report.alert_number}
- Package: {initial_report.package}
- Vulnerability ID: {initial_report.vulnerability_id}
- Initial Assessment: {"EXPLOITABLE" if initial_report.is_exploitable else "NOT EXPLOITABLE"}
- Confidence: {initial_report.confidence}
- Priority: {initial_report.priority}

### Initial Reasoning
{initial_report.reasoning}

### Impact Assessment
{initial_report.impact_assessment}

### Recommended Action
{initial_report.recommended_action}

## Vulnerability Details
{vulnerability_details}

## Actual Code Matches Found
{matches_text}

## Affected Code Paths (from initial report)
{', '.join(initial_report.code_paths_affected) if initial_report.code_paths_affected else 'None specified'}

## Your Task

Critically analyze this finding and determine:

1. **Is this a FALSE POSITIVE?**
   - Are the code matches in test/development/example code only?
   - Is the vulnerable function actually being called with user-controlled input?
   - Are there mitigations or validations that prevent exploitation?
   - Is the vulnerability description matching the actual code usage?

2. **Evidence Quality**
   - How strong is the evidence of actual exploitability?
   - Are there specific, credible attack vectors?
   - Or is this just theoretical risk based on package presence?

3. **Specific Red Flags for False Positives**
   - ❌ "Package is used" but no vulnerable function calls shown
   - ❌ All matches are in test files, curl commands, or scripts
   - ❌ Vulnerable functions called with hardcoded, safe values
   - ❌ The attack requires conditions that don't exist in the code
   - ❌ Reasoning is generic, not specific to this codebase

4. **Corrected Assessment**
   - If the initial report was wrong, provide corrected priority and exploitability
   - If it was correct, confirm the findings

Be thorough and evidence-based. Your job is to catch mistakes and false alarms."""

    async def validate_and_correct(
        self,
        report: AnalysisReport,
        check: FalsePositiveCheck
    ) -> AnalysisReport:
        """
        Update report based on false positive check results.

        Args:
            report: Original analysis report
            check: False positive check results

        Returns:
            Corrected report
        """
        if not check.is_false_positive:
            # No correction needed
            return report

        # Update report with corrections
        corrected = report.model_copy()

        if check.corrected_exploitability is not None:
            corrected.is_exploitable = check.corrected_exploitability

        if check.corrected_priority:
            corrected.priority = check.corrected_priority

        # Append false positive reasoning to the report
        corrected.reasoning = (
            f"{report.reasoning}\n\n"
            f"**FALSE POSITIVE CHECK**: {check.reasoning}"
        )

        return corrected
