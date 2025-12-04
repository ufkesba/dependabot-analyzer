import os
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..agents.alert_fetcher import AlertFetcher, DependabotAlert
from ..agents.deep_analyzer import DeepAnalyzer, AnalysisReport
from ..agents.code_analyzer import CodeAnalyzer, CodeMatch
from ..agents.false_positive_checker import FalsePositiveChecker, FalsePositiveCheck
from ..llm.client import LLMClient

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
        self.analyzer = DeepAnalyzer(deep_analyzer_llm)
        self.code_analyzer = CodeAnalyzer(self.alert_fetcher.repo)
        self.false_positive_checker = FalsePositiveChecker(false_positive_llm)

        self.reports: List[AnalysisReport] = []
        self.false_positive_checks: List[FalsePositiveCheck] = []

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

        # Step 2: Analyze each alert
        console.print(f"\n[bold]Starting deep analysis of {len(alerts)} alerts...[/bold]\n")

        for i, alert in enumerate(alerts, 1):
            console.print(f"\n[bold]Alert {i}/{len(alerts)}[/bold]")

            # Step 2a: Search for vulnerable code patterns
            if self.verbose:
                console.print("[dim]→ Agent: code_analyzer[/dim]")
            console.print("[cyan]Searching for vulnerable code patterns...[/cyan]")
            code_matches = self.code_analyzer.find_vulnerable_usage(
                package_name=alert.package,
                vulnerability_id=alert.vulnerability_id,
                max_files=50
            )

            # Step 2b: Get general code context
            if self.verbose:
                console.print("[dim]→ Agent: alert_fetcher[/dim]")
            code_context = self.alert_fetcher.get_code_context(alert)

            # Step 2c: Deep analysis with code matches
            if self.verbose:
                console.print("[dim]→ Agent: deep_analyzer (LLM)[/dim]")
            report = await self.analyzer.analyze(alert, code_context, code_matches)

            # Step 2d: False positive check (only for exploitable alerts)
            fp_check = None
            if report.is_exploitable:
                if self.verbose:
                    console.print("[dim]→ Agent: false_positive_checker (LLM)[/dim]")
                console.print("[cyan]Running false positive check...[/cyan]")
                console.print(f"Running false positive check for alert #{alert.number}")
                fp_check = await self.false_positive_checker.check(
                    initial_report=report,
                    code_matches=code_matches,
                    vulnerability_details=f"{alert.description}\n\nAffected versions: {alert.affected_versions}"
                )

                # Step 2e: Apply corrections if needed
                if fp_check.is_false_positive:
                    report = await self.false_positive_checker.validate_and_correct(report, fp_check)

                self.false_positive_checks.append(fp_check)

            self.reports.append(report)

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

        # Fetch all alerts to find the specific one
        console.print(f"[cyan]Fetching alert #{alert_id} from {self.repo}...[/cyan]")
        all_alerts = self.alert_fetcher.get_alerts(state="all")

        # Find the specific alert
        target_alert = None
        for alert in all_alerts:
            if alert.number == alert_id:
                target_alert = alert
                break

        if not target_alert:
            console.print(f"[red]Error: Alert #{alert_id} not found in repository[/red]")
            return

        # Display alert info
        console.print(f"\n[bold]Alert #{target_alert.number}:[/bold] {target_alert.package}")
        console.print(f"Severity: {target_alert.severity.upper()}")
        console.print(f"CVE: {target_alert.cve_id or 'N/A'}")
        console.print(f"Summary: {target_alert.summary}\n")

        # Search for vulnerable code patterns
        if self.verbose:
            console.print("[dim]→ Agent: code_analyzer[/dim]")
        console.print("[cyan]Searching for vulnerable code patterns...[/cyan]")
        code_matches = self.code_analyzer.find_vulnerable_usage(
            package_name=target_alert.package,
            vulnerability_id=target_alert.vulnerability_id,
            max_files=50
        )

        # Get general code context
        if self.verbose:
            console.print("[dim]→ Agent: alert_fetcher[/dim]")
        console.print("[cyan]Analyzing general code usage...[/cyan]")
        code_context = self.alert_fetcher.get_code_context(target_alert)

        # Deep analysis
        if self.verbose:
            console.print("[dim]→ Agent: deep_analyzer (LLM)[/dim]")
        console.print("[cyan]Running deep AI analysis...[/cyan]\n")
        report = await self.analyzer.analyze(target_alert, code_context, code_matches)

        # False positive check (only for exploitable alerts)
        fp_check = None
        if report.is_exploitable:
            if self.verbose:
                console.print("[dim]→ Agent: false_positive_checker (LLM)[/dim]")
            console.print("[cyan]Running false positive check...[/cyan]")
            console.print(f"Running false positive check for alert #{target_alert.number}")
            fp_check = await self.false_positive_checker.check(
                initial_report=report,
                code_matches=code_matches,
                vulnerability_details=f"{target_alert.description}\n\nAffected versions: {target_alert.affected_versions}"
            )

            # Apply corrections if needed
            if fp_check.is_false_positive:
                report = await self.false_positive_checker.validate_and_correct(report, fp_check)

            self.false_positive_checks.append(fp_check)

        self.reports.append(report)

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
