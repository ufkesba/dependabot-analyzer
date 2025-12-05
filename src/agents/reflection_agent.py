"""
Reflection Agent - Analyzes uncertain or contradictory analysis results.

Inspired by Trail of Bits Buttercup's reflection pattern, this agent:
1. Detects patterns in analysis results (low confidence, contradictions, edge cases)
2. Determines if more information is needed
3. Suggests next steps (retry with different approach, gather more code, accept result)
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from rich.console import Console

from ..llm.client import LLMClient
from .alert_fetcher import DependabotAlert
from .deep_analyzer import AnalysisReport
from .code_analyzer import CodeMatch

console = Console()


class AnalysisCommand(BaseModel):
    """
    Command pattern for dynamic workflow routing.
    Agents return commands specifying what should happen next.
    """
    action: Literal["retry_analysis", "search_more_code", "accept_result", "escalate_manual"]
    reason: str
    next_agent: Optional[str] = None  # Which agent to invoke next
    search_params: Optional[dict] = Field(default_factory=dict)  # Parameters for next search
    confidence_boost: Optional[str] = None  # Suggestions to improve confidence


class ReflectionResult(BaseModel):
    """Result of reflection analysis"""
    needs_refinement: bool
    confidence_assessment: str  # "acceptable", "needs_improvement", "contradictory"
    detected_patterns: List[str]  # Patterns found: "unused_package", "test_only", "hardcoded_values", etc.
    command: AnalysisCommand
    reasoning: str
    suggested_focus_areas: List[str] = Field(default_factory=list)


class ReflectionAgent:
    """
    Meta-agent that analyzes the quality of analysis results.
    Determines if results are uncertain and suggests next steps.
    """

    def __init__(self, llm_client: LLMClient, verbose: bool = False):
        self.llm = llm_client
        self.verbose = verbose

    async def reflect(
        self,
        alert: DependabotAlert,
        current_report: AnalysisReport,
        code_matches: List[CodeMatch],
        analysis_history: List[AnalysisReport],
        attempt_count: int
    ) -> ReflectionResult:
        """
        Analyze the quality of current analysis and determine next steps.

        Args:
            alert: The Dependabot alert being analyzed
            current_report: Latest analysis report
            code_matches: Code patterns found
            analysis_history: Previous analysis attempts
            attempt_count: How many times we've attempted analysis

        Returns:
            ReflectionResult with assessment and recommended action
        """
        if self.verbose:
            console.print("[magenta]🤔 Reflecting on analysis quality...[/magenta]")

        prompt = self._build_reflection_prompt(
            alert=alert,
            current_report=current_report,
            code_matches=code_matches,
            analysis_history=analysis_history,
            attempt_count=attempt_count
        )

        response_format = {
            "needs_refinement": "boolean",
            "confidence_assessment": "string (acceptable/needs_improvement/contradictory)",
            "detected_patterns": ["list of patterns like: package_imported_not_used, only_in_tests, hardcoded_values, version_only_vulnerability, etc."],
            "reasoning": "string - explain what you observed and why refinement is/isn't needed",
            "suggested_focus_areas": ["list of specific areas to investigate further"],
            "command": {
                "action": "string (retry_analysis/search_more_code/accept_result/escalate_manual)",
                "reason": "string - why this action is recommended",
                "next_agent": "string or null (code_analyzer/deep_analyzer/null)",
                "search_params": {
                    "description": "optional dict with search suggestions like: {\"search_terms\": [\"term1\", \"term2\"], \"focus_files\": [\"file1.js\"]}",
                },
                "confidence_boost": "string or null - specific suggestions to improve confidence"
            }
        }

        try:
            reflection = await self.llm.ask_structured(
                prompt=prompt,
                response_format=response_format,
                system_prompt=self._get_system_prompt(),
                max_tokens=4096
            )

            # Parse command
            command_data = reflection["command"]
            command = AnalysisCommand(
                action=command_data["action"],
                reason=command_data["reason"],
                next_agent=command_data.get("next_agent"),
                search_params=command_data.get("search_params", {}),
                confidence_boost=command_data.get("confidence_boost")
            )

            result = ReflectionResult(
                needs_refinement=reflection["needs_refinement"],
                confidence_assessment=reflection["confidence_assessment"],
                detected_patterns=reflection["detected_patterns"],
                command=command,
                reasoning=reflection["reasoning"],
                suggested_focus_areas=reflection.get("suggested_focus_areas", [])
            )

            # Print reflection summary (verbose only)
            if self.verbose:
                console.print(f"[magenta]Confidence: {result.confidence_assessment}[/magenta]")
                console.print(f"[magenta]Needs refinement: {result.needs_refinement}[/magenta]")
                if result.detected_patterns:
                    console.print(f"[magenta]Patterns detected: {', '.join(result.detected_patterns)}[/magenta]")
                console.print(f"[magenta]Recommended action: {result.command.action}[/magenta]")

            return result

        except Exception as e:
            if self.verbose:
                console.print(f"[yellow]Reflection failed: {str(e)[:200]}[/yellow]")
            # Default to accepting result if reflection fails
            return ReflectionResult(
                needs_refinement=False,
                confidence_assessment="acceptable",
                detected_patterns=["reflection_failed"],
                command=AnalysisCommand(
                    action="accept_result",
                    reason=f"Reflection agent encountered error: {str(e)[:200]}"
                ),
                reasoning=f"Unable to perform reflection due to error. Accepting current analysis as-is.",
                suggested_focus_areas=[]
            )

    def _get_system_prompt(self) -> str:
        """System prompt for reflection agent"""
        return """You are a meta-analyst reviewing the quality of security vulnerability analyses.

Your role is to:
1. Assess if the current analysis is confident and well-reasoned
2. Detect common patterns that indicate false positives or need more investigation
3. Suggest concrete next steps to improve analysis quality

Common patterns to detect:
- **package_imported_not_used**: Package is imported but vulnerable functions never called
- **only_in_tests**: Vulnerability only affects test code, not production
- **hardcoded_values**: Vulnerable function called with hardcoded safe values
- **version_only_vulnerability**: Alert is version-based with no specific vulnerable function
- **dependency_of_dependency**: Transitive dependency with unclear usage
- **contradictory_reasoning**: Analysis reasoning contradicts the conclusion
- **insufficient_code_context**: Not enough code was examined to make confident assessment
- **missing_data_flow_analysis**: Need to trace how user input reaches vulnerable code

Be pragmatic:
- Low confidence on first attempt → suggest specific improvements
- Medium confidence after retry → might be acceptable
- High confidence → accept result
- Contradictory reasoning → retry with clarification
- Max attempts reached → escalate to manual review if still uncertain

Focus on actionable suggestions, not generic advice."""

    def _build_reflection_prompt(
        self,
        alert: DependabotAlert,
        current_report: AnalysisReport,
        code_matches: List[CodeMatch],
        analysis_history: List[AnalysisReport],
        attempt_count: int
    ) -> str:
        """Build the reflection prompt"""

        # Format code matches summary
        matches_summary = ""
        if code_matches:
            matches_summary = f"\n{len(code_matches)} vulnerable code pattern(s) found:\n"
            for i, match in enumerate(code_matches[:3], 1):
                matches_summary += f"  {i}. {match.file_path}:{match.line_number} - `{match.code_snippet[:60]}...`\n"
            if len(code_matches) > 3:
                matches_summary += f"  ... and {len(code_matches) - 3} more\n"
        else:
            matches_summary = "\nNo vulnerable code patterns were found in the codebase.\n"

        # Format history
        history_section = ""
        if len(analysis_history) > 1:
            history_section = "\n## Previous Attempts\n\n"
            for i, report in enumerate(analysis_history[:-1], 1):
                history_section += f"**Attempt {i}**:\n"
                history_section += f"- Exploitable: {report.is_exploitable}\n"
                history_section += f"- Confidence: {report.confidence}\n"
                history_section += f"- Reasoning excerpt: {report.reasoning[:200]}...\n\n"

        return f"""Review this vulnerability analysis and determine if it needs refinement:

## Alert Information
- Package: {alert.package}
- Vulnerability ID: {alert.vulnerability_id}
- Severity: {alert.severity}
- Summary: {alert.summary}
- Description: {alert.description[:300]}...

## Code Search Results
{matches_summary}

## Current Analysis (Attempt {attempt_count})
- **Exploitable**: {current_report.is_exploitable}
- **Confidence**: {current_report.confidence}
- **Priority**: {current_report.priority}
- **Reasoning**: {current_report.reasoning}
- **Impact**: {current_report.impact_assessment}
- **Recommended Action**: {current_report.recommended_action}

{history_section}

## Your Task

Analyze the quality of this assessment and determine:

1. **Is the confidence level appropriate?**
   - Does the reasoning support the conclusion?
   - Is there contradictory information?
   - Are there unexplored angles?

2. **What patterns do you detect?**
   - Package imported but not used?
   - Only used in test code?
   - Vulnerable function called with safe hardcoded values?
   - Missing critical information?

3. **What should happen next?**
   - `accept_result`: Analysis is good enough (even if medium confidence)
   - `retry_analysis`: Re-analyze with more context (specify what to focus on)
   - `search_more_code`: Need to search for additional code patterns (specify what)
   - `escalate_manual`: Max attempts reached or too complex for automation

4. **Specific improvements** (if refinement needed):
   - What should the next analysis focus on?
   - What questions need answering?
   - What code should be searched?

Be practical:
- After 2-3 attempts, accept "medium" confidence if reasoning is sound
- Only retry if you have SPECIFIC suggestions for improvement
- Consider the cost/benefit of additional analysis

Provide your reflection in structured JSON format."""
