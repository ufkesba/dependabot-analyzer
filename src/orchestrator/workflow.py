import os
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..agents.alert_fetcher import AlertFetcher, DependabotAlert
from ..agents.deep_analyzer import DeepAnalyzer, AnalysisReport
from ..agents.code_analyzer import CodeAnalyzer, CodeMatch
from ..agents.false_positive_checker import FalsePositiveChecker, FalsePositiveCheck
from ..agents.reflection_agent import ReflectionAgent, ReflectionResult
from ..llm.client import LLMClient
from .state import AnalysisState

console = Console()


class DependabotAnalyzer:
    """
    Main orchestrator that coordinates the analysis workflow.
    Fetches alerts, analyzes them, and generates reports.
    """

    def __init__(
        self,
        repo: str,
        github_token: Optional[str] = None,
        llm_model: str = "gemini-flash-latest",
        llm_provider: str = "google",
        verbose: bool = False
    ):
        """
        Args:
            repo: GitHub repository in format "owner/repo"
            github_token: GitHub personal access token
            llm_model: LLM model to use for analysis
            llm_provider: LLM provider (google, anthropic, openai)
            verbose: Show detailed agent activity
        """
        self.repo = repo
        self.verbose = verbose

        # Initialize components
        self.alert_fetcher = AlertFetcher(repo, github_token)
        deep_analyzer_llm = LLMClient(provider=llm_provider, model=llm_model, agent_name="deep_analyzer")
        false_positive_llm = LLMClient(provider=llm_provider, model=llm_model, agent_name="false_positive_checker")
        code_analyzer_llm = LLMClient(provider=llm_provider, model=llm_model, agent_name="code_analyzer")
        reflection_llm = LLMClient(provider=llm_provider, model=llm_model, agent_name="reflection_agent")
        self.analyzer = DeepAnalyzer(deep_analyzer_llm, verbose=verbose)
        self.code_analyzer = CodeAnalyzer(self.alert_fetcher.repo, llm_client=code_analyzer_llm, verbose=verbose)
        self.false_positive_checker = FalsePositiveChecker(false_positive_llm, verbose=verbose)
        self.reflection_agent = ReflectionAgent(reflection_llm, verbose=verbose)

        self.reports: List[AnalysisReport] = []
        self.false_positive_checks: List[FalsePositiveCheck] = []
        self.analysis_states: List[AnalysisState] = []  # Track state for each alert

    async def _process_alert_with_state(self, state: AnalysisState) -> AnalysisState:
        """
        Process a single alert with state tracking.
        This enables retry logic and context accumulation.

        Args:
            state: The AnalysisState for this alert

        Returns:
            Updated AnalysisState with results
        """
        alert = state.alert

        # Phase 1: Code Analysis
        state.current_phase = "code_analysis"
        state.increment_attempts("code_analyzer")

        if self.verbose:
            console.print("\n[bold cyan]━━━ Phase 1: Code Pattern Search ━━━[/bold cyan]")

        try:

            code_matches = await self.code_analyzer.find_vulnerable_usage(
                package_name=alert.package,
                vulnerability_id=alert.vulnerability_id,
                max_files=50,
                vulnerability_description=alert.description,
                vulnerability_summary=alert.summary
            )
            state.code_matches = code_matches
            state.add_execution("code_analyzer", success=True, matches_found=len(code_matches))

        except Exception as e:
            state.add_execution("code_analyzer", success=False, error_message=str(e))
            if self.verbose:
                console.print(f"[yellow]Warning: Code analysis failed: {str(e)[:100]}[/yellow]")
            # Continue with empty matches
            state.code_matches = []

        # Phase 2: Get Code Context
        try:
            if self.verbose:
                console.print("[dim]→ Fetching code context (manifest files, dependency info)[/dim]")
            state.code_context = self.alert_fetcher.get_code_context(alert)
            state.add_execution("alert_fetcher", success=True)
        except Exception as e:
            state.add_execution("alert_fetcher", success=False, error_message=str(e))
            if self.verbose:
                console.print(f"[yellow]Warning: Code context fetch failed: {str(e)[:100]}[/yellow]")
            state.code_context = f"Package: {alert.package} (context unavailable)"

        # Phase 3: Deep Analysis with Reflection-Based Refinement
        state.current_phase = "deep_analysis"

        if self.verbose:
            console.print("\n[bold cyan]━━━ Phase 2: Deep Analysis ━━━[/bold cyan]")

        report = None
        refinement_iteration = 0

        while True:
            # Step 3a: Run Deep Analysis
            state.increment_attempts("deep_analyzer")
            attempt_num = state.deep_analyzer_attempts

            try:
                if self.verbose and attempt_num > 1:
                    console.print(f"[dim]→ Deep analysis attempt {attempt_num}[/dim]")

                # Pass accumulated context from previous attempts
                previous_context = state.accumulated_context if state.accumulated_context else None

                report = await self.analyzer.analyze(
                    alert,
                    state.code_context,
                    state.code_matches,
                    previous_attempts=previous_context
                )
                state.reports.append(report)
                state.final_report = report
                state.add_execution("deep_analyzer", success=True, confidence=report.confidence, attempt=attempt_num)

            except Exception as e:
                state.add_execution("deep_analyzer", success=False, error_message=str(e), attempt=attempt_num)
                if self.verbose:
                    console.print(f"[yellow]Error during deep analysis (attempt {attempt_num}): {str(e)[:200]}[/yellow]")

                if state.should_retry("deep_analyzer"):
                    error_context = f"Previous attempt {attempt_num} failed with error: {str(e)[:500]}\n"
                    state.add_context(error_context)
                    continue
                else:
                    if self.verbose:
                        console.print(f"[red]Max retries reached for deep analysis[/red]")
                    state.current_phase = "failed"
                    return state

            # Step 3b: Reflection Phase (if we have a report and can still refine)
            if report and state.should_retry("reflection_agent") and refinement_iteration < state.max_refinement_iterations:
                state.current_phase = "reflection"
                state.increment_attempts("reflection_agent")
                refinement_iteration += 1

                if self.verbose:
                    console.print(f"\n[bold magenta]━━━ Reflection Check (iteration {refinement_iteration}) ━━━[/bold magenta]")

                try:

                    reflection = await self.reflection_agent.reflect(
                        alert=alert,
                        current_report=report,
                        code_matches=state.code_matches,
                        analysis_history=state.reports,
                        attempt_count=attempt_num
                    )
                    state.reflection_results.append(reflection)
                    state.add_execution("reflection_agent", success=True, needs_refinement=reflection.needs_refinement, iteration=refinement_iteration)

                    # Act on reflection result
                    if not reflection.needs_refinement or reflection.command.action == "accept_result":
                        if self.verbose:
                            console.print("[green]✓ Reflection agent accepted analysis result[/green]")
                        break
                    elif reflection.command.action == "escalate_manual":
                        if self.verbose:
                            console.print("[yellow]⚠ Reflection agent recommends manual review[/yellow]")
                        state.add_context(f"Reflection iteration {refinement_iteration}: {reflection.reasoning}")
                        break
                    elif reflection.command.action == "retry_analysis":
                        if self.verbose:
                            console.print(f"[yellow]🔄 Reflection suggests retry: {reflection.command.reason}[/yellow]")
                        # Add reflection insights to context
                        context_msg = f"Reflection iteration {refinement_iteration}:\n"
                        context_msg += f"Assessment: {reflection.confidence_assessment}\n"
                        context_msg += f"Patterns detected: {', '.join(reflection.detected_patterns)}\n"
                        context_msg += f"Reason for retry: {reflection.command.reason}\n"
                        if reflection.command.confidence_boost:
                            context_msg += f"Suggestions: {reflection.command.confidence_boost}\n"
                        if reflection.suggested_focus_areas:
                            context_msg += f"Focus on: {', '.join(reflection.suggested_focus_areas)}\n"
                        state.add_context(context_msg)

                        # Check if we can retry deep analysis
                        if state.should_retry("deep_analyzer"):
                            state.current_phase = "deep_analysis"
                            continue
                        else:
                            if self.verbose:
                                console.print("[yellow]Cannot retry - max attempts reached. Accepting current result.[/yellow]")
                            break
                    elif reflection.command.action == "search_more_code":
                        if self.verbose:
                            console.print(f"[yellow]🔍 Reflection suggests more code search: {reflection.command.reason}[/yellow]")
                        # TODO: In future, could trigger additional code search here
                        # For now, just add to context and continue
                        context_msg = f"Reflection suggests searching for: {reflection.command.search_params}\n"
                        context_msg += f"Reason: {reflection.command.reason}\n"
                        state.add_context(context_msg)
                        break

                except Exception as e:
                    state.add_execution("reflection_agent", success=False, error_message=str(e), iteration=refinement_iteration)
                    if self.verbose:
                        console.print(f"[yellow]Reflection failed: {str(e)[:200]}. Accepting current analysis.[/yellow]")
                    break
            else:
                # No reflection needed or max iterations reached
                if refinement_iteration >= state.max_refinement_iterations and self.verbose:
                    console.print(f"[yellow]Max refinement iterations ({state.max_refinement_iterations}) reached[/yellow]")
                break

        if not report:
            console.print(f"[red]Deep analysis failed after {state.deep_analyzer_attempts} attempts[/red]")
            state.current_phase = "failed"
            return state

        # Phase 4: False Positive Check (only for exploitable alerts)
        if state.final_report and state.final_report.is_exploitable:
            if self.verbose:
                console.print("\n[bold cyan]━━━ Phase 3: False Positive Check ━━━[/bold cyan]")

            state.current_phase = "fp_check"
            state.increment_attempts("false_positive_checker")

            try:

                fp_check = await self.false_positive_checker.check(
                    initial_report=state.final_report,
                    code_matches=state.code_matches,
                    vulnerability_details=f"{alert.description}\n\nAffected versions: {alert.affected_versions}"
                )

                state.false_positive_checks.append(fp_check)
                state.final_fp_check = fp_check
                state.add_execution("false_positive_checker", success=True, is_fp=fp_check.is_false_positive)

                # Apply corrections if needed
                if fp_check.is_false_positive:
                    state.final_report = await self.false_positive_checker.validate_and_correct(
                        state.final_report,
                        fp_check
                    )

            except Exception as e:
                state.add_execution("false_positive_checker", success=False, error_message=str(e))
                if self.verbose:
                    console.print(f"[yellow]Warning: False positive check failed: {str(e)[:200]}[/yellow]")

        state.current_phase = "completed"
        return state

    async def run(
        self,
        state: str = "open",
        min_severity: Optional[str] = None,
        max_alerts: Optional[int] = None
    ):
        """
        Run the full analysis workflow.

        Args:
            state: Alert state to fetch ("open", "fixed", "dismissed", "all")
            min_severity: Minimum severity to analyze (e.g., "medium")
            max_alerts: Maximum number of alerts to process
        """
        console.print(Panel.fit(
            f"[bold cyan]Dependabot Alert Analyzer[/bold cyan]\n"
            f"Repository: {self.repo}",
            border_style="cyan"
        ))

        # Step 1: Fetch alerts
        severity_filter = self._get_severity_filter(min_severity) if min_severity else None
        alerts = self.alert_fetcher.get_alerts(state=state, severity=severity_filter)

        if not alerts:
            console.print("[yellow]No alerts found matching criteria.[/yellow]")
            return

        # Limit number of alerts if specified
        if max_alerts and len(alerts) > max_alerts:
            console.print(f"[yellow]Limiting analysis to first {max_alerts} alerts[/yellow]")
            alerts = alerts[:max_alerts]

        # Display alerts table
        self._display_alerts_table(alerts)

        # Step 2: Analyze each alert with state tracking
        console.print(f"\n[bold]Starting deep analysis of {len(alerts)} alerts...[/bold]\n")

        for i, alert in enumerate(alerts, 1):
            console.print(f"\n[bold]Alert {i}/{len(alerts)}[/bold]")

            # Create analysis state for this alert
            analysis_state = AnalysisState(alert=alert)

            # Process alert with state management
            analysis_state = await self._process_alert_with_state(analysis_state)

            # Save state and results
            self.analysis_states.append(analysis_state)
            if analysis_state.final_report:
                self.reports.append(analysis_state.final_report)
            if analysis_state.final_fp_check:
                self.false_positive_checks.append(analysis_state.final_fp_check)

        # Step 3: Display summary
        self._display_summary()

    async def run_single_alert(self, alert_id: int):
        """
        Analyze a single Dependabot alert by its ID.

        Args:
            alert_id: The Dependabot alert number to analyze
        """
        console.print(Panel.fit(
            f"[bold cyan]Dependabot Alert Analyzer[/bold cyan]\n"
            f"Repository: {self.repo}\n"
            f"Alert ID: {alert_id}",
            border_style="cyan"
        ))

        # Fetch the specific alert directly
        target_alert = self.alert_fetcher.get_alert_by_id(alert_id)

        if not target_alert:
            console.print(f"[red]Error: Alert #{alert_id} not found in repository[/red]")
            return

        # Display alert info
        console.print(f"\n[bold]Alert #{target_alert.number}:[/bold] {target_alert.package}")
        console.print(f"Severity: {target_alert.severity.upper()}")
        console.print(f"CVE: {target_alert.cve_id or 'N/A'}")
        console.print(f"Summary: {target_alert.summary}\n")

        # Create analysis state for this alert
        analysis_state = AnalysisState(alert=target_alert)

        # Process alert with state management
        analysis_state = await self._process_alert_with_state(analysis_state)

        # Save state and results
        self.analysis_states.append(analysis_state)
        if analysis_state.final_report:
            self.reports.append(analysis_state.final_report)
            report = analysis_state.final_report
        else:
            console.print("[red]Analysis failed - no report generated[/red]")
            return

        if analysis_state.final_fp_check:
            self.false_positive_checks.append(analysis_state.final_fp_check)
            fp_check = analysis_state.final_fp_check
        else:
            fp_check = None

        # Display detailed result
        console.print("\n" + "="*80)
        console.print(Panel.fit("[bold]Analysis Result[/bold]", border_style="green"))

        status = "🔴 EXPLOITABLE" if report.is_exploitable else "🟢 NOT EXPLOITABLE"
        console.print(f"\n[bold]Status:[/bold] {status}")
        console.print(f"[bold]Confidence:[/bold] {report.confidence}")
        console.print(f"[bold]Priority:[/bold] {report.priority}")

        # Show false positive check result
        if fp_check and fp_check.is_false_positive:
            console.print(f"\n[yellow]⚠️  FALSE POSITIVE DETECTED[/yellow] (confidence: {fp_check.confidence})")
            console.print(f"[yellow]False Positive Reasoning:[/yellow]\n{fp_check.reasoning}")

        console.print(f"\n[bold]Reasoning:[/bold]\n{report.reasoning}")
        console.print(f"\n[bold]Impact:[/bold]\n{report.impact_assessment}")
        console.print(f"\n[bold]Recommended Action:[/bold]\n{report.recommended_action}")

        if report.test_case:
            console.print(f"\n[bold]Test Case:[/bold]\n{report.test_case}")

    def _get_severity_filter(self, min_severity: str) -> List[str]:
        """Convert minimum severity to list of severities to include"""
        severity_order = ["critical", "high", "medium", "low", "info"]
        min_index = severity_order.index(min_severity.lower())
        return severity_order[:min_index + 1]

    def _display_alerts_table(self, alerts: List[DependabotAlert]):
        """Display a table of fetched alerts"""
        table = Table(title="Dependabot Alerts", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=6)
        table.add_column("Package", style="cyan")
        table.add_column("Severity", justify="center")
        table.add_column("CVE", style="dim")
        table.add_column("Summary")

        for alert in alerts:
            # Color code severity
            severity_colors = {
                "critical": "[red]CRITICAL[/red]",
                "high": "[orange1]HIGH[/orange1]",
                "medium": "[yellow]MEDIUM[/yellow]",
                "low": "[green]LOW[/green]"
            }
            severity_display = severity_colors.get(alert.severity.lower(), alert.severity)

            table.add_row(
                str(alert.number),
                alert.package,
                severity_display,
                alert.cve_id or "N/A",
                alert.summary[:50] + "..." if len(alert.summary) > 50 else alert.summary
            )

        console.print(table)

    def _display_summary(self):
        """Display analysis summary"""
        console.print("\n" + "="*80)
        console.print(Panel.fit("[bold]Analysis Summary[/bold]", border_style="green"))

        # Count exploitable vs non-exploitable
        exploitable = [r for r in self.reports if r.is_exploitable]
        non_exploitable = [r for r in self.reports if not r.is_exploitable]

        # Count false positives
        false_positives = [fp for fp in self.false_positive_checks if fp.is_false_positive]

        # Priority breakdown
        priority_counts = {}
        for report in self.reports:
            priority_counts[report.priority] = priority_counts.get(report.priority, 0) + 1

        # Display counts
        console.print(f"\n[bold]Total Alerts Analyzed:[/bold] {len(self.reports)}")
        console.print(f"[red]🔴 Exploitable:[/red] {len(exploitable)}")
        console.print(f"[green]🟢 Not Exploitable:[/green] {len(non_exploitable)}")
        console.print(f"[yellow]⚠️  False Positives:[/yellow] {len(false_positives)}")

        console.print(f"\n[bold]Priority Breakdown:[/bold]")
        for priority in ["critical", "high", "medium", "low"]:
            count = priority_counts.get(priority, 0)
            if count > 0:
                console.print(f"  {priority.upper()}: {count}")

        # Display detailed results for exploitable alerts
        if exploitable:
            console.print(f"\n[bold red]Exploitable Alerts (Action Required):[/bold red]")
            for report in exploitable:
                console.print(f"\n[red]Alert #{report.alert_number}:[/red] {report.package}")
                console.print(f"  Priority: {report.priority}")
                console.print(f"  Confidence: {report.confidence}")
                console.print(f"  Reasoning: {report.reasoning}")
                console.print(f"  Recommended Action: {report.recommended_action}")

    def save_reports(self, output_dir: str = "./reports"):
        """Save analysis reports to JSON files"""
        import json
        from pathlib import Path

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        for report in self.reports:
            filename = f"{output_dir}/alert_{report.alert_number}_{report.package}.json"
            with open(filename, 'w') as f:
                json.dump(report.model_dump(), f, indent=2)

        console.print(f"\n[green]✓[/green] Saved {len(self.reports)} reports to {output_dir}/")
