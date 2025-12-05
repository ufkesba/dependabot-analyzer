#!/usr/bin/env python3
"""
Dependabot Alert Analyzer
Analyzes Dependabot security alerts using AI to determine actual exploitability.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestrator import DependabotAnalyzer

app = typer.Typer(help="Analyze Dependabot security alerts for exploitability")
console = Console()

# Load environment variables from .env file
load_dotenv()


@app.command()
def analyze(
    repo: str = typer.Argument(..., help="GitHub repository (format: owner/repo)"),
    github_token: Optional[str] = typer.Option(None, "--github-token", help="GitHub personal access token"),
    state: str = typer.Option("open", "--state", help="Alert state: open, fixed, dismissed, or all"),
    min_severity: Optional[str] = typer.Option("medium", "--min-severity", help="Minimum severity: critical, high, medium, low"),
    max_alerts: Optional[int] = typer.Option(None, "--max-alerts", help="Maximum number of alerts to analyze"),
    model: str = typer.Option("claude-3-5-sonnet-20241022", "--model", help="LLM model to use"),
    provider: str = typer.Option("anthropic", "--provider", help="LLM provider: anthropic, google, openai"),
    no_save: bool = typer.Option(False, "--no-save", help="Skip saving analysis reports"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed agent activity"),
):
    """
    Analyze Dependabot security alerts in a GitHub repository.

    Example:
        python main.py analyze owner/repo --min-severity high --max-alerts 5
    """
    # Validate environment
    if not github_token:
        github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        console.print("[red]Error: GitHub token not found. Set GITHUB_TOKEN environment variable or use --github-token[/red]")
        raise typer.Exit(1)

    api_key_env = {
        "google": "GOOGLE_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY"
    }

    required_key = api_key_env.get(provider)
    if required_key and not os.getenv(required_key):
        console.print(f"[red]Error: {required_key} environment variable not set[/red]")
        raise typer.Exit(1)

    # Run analysis
    async def run_analysis():
        analyzer = DependabotAnalyzer(
            repo=repo,
            github_token=github_token,
            llm_model=model,
            llm_provider=provider,
            verbose=verbose
        )

        await analyzer.run(
            state=state,
            min_severity=min_severity,
            max_alerts=max_alerts
        )

        if not no_save and analyzer.reports:
            analyzer.save_reports()

    asyncio.run(run_analysis())


@app.command()
def analyze_alert(
    repo: str = typer.Argument(..., help="GitHub repository (format: owner/repo)"),
    alert_id: int = typer.Argument(..., help="Dependabot alert number to analyze"),
    github_token: Optional[str] = typer.Option(None, "--github-token", help="GitHub personal access token"),
    model: str = typer.Option("claude-3-5-sonnet-20241022", "--model", help="LLM model to use"),
    provider: str = typer.Option("anthropic", "--provider", help="LLM provider: anthropic, google, openai"),
    no_save: bool = typer.Option(False, "--no-save", help="Skip saving analysis reports"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed agent activity"),
):
    """
    Analyze a specific Dependabot alert by its ID.

    Example:
        python main.py analyze-alert owner/repo 7
    """
    # Validate environment
    if not github_token:
        github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        console.print("[red]Error: GitHub token not found. Set GITHUB_TOKEN environment variable or use --github-token[/red]")
        raise typer.Exit(1)

    api_key_env = {
        "google": "GOOGLE_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY"
    }

    required_key = api_key_env.get(provider)
    if required_key and not os.getenv(required_key):
        console.print(f"[red]Error: {required_key} environment variable not set[/red]")
        raise typer.Exit(1)

    # Run analysis
    async def run_single_alert_analysis():
        analyzer = DependabotAnalyzer(
            repo=repo,
            github_token=github_token,
            llm_model=model,
            llm_provider=provider,
            verbose=verbose
        )

        await analyzer.run_single_alert(alert_id=alert_id)

        if not no_save and analyzer.reports:
            analyzer.save_reports()

    asyncio.run(run_single_alert_analysis())


@app.command()
def init():
    """
    Initialize configuration by creating .env file from template.
    """
    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        overwrite = typer.confirm(".env file already exists. Overwrite?")
        if not overwrite:
            console.print("[yellow]Initialization cancelled[/yellow]")
            raise typer.Exit(0)

    if env_example.exists():
        import shutil
        shutil.copy(env_example, env_file)
        console.print("[green]✓[/green] Created .env file from template")
        console.print("[yellow]⚠[/yellow]  Please edit .env and add your API keys:")
        console.print("  - ANTHROPIC_API_KEY (primary - from https://console.anthropic.com/settings/keys)")
        console.print("  - GOOGLE_API_KEY (fallback - from https://aistudio.google.com/app/apikey)")
        console.print("  - GITHUB_TOKEN (from https://github.com/settings/tokens)")
    else:
        console.print("[red]Error: .env.example not found[/red]")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information"""
    console.print("Dependabot Alert Analyzer v0.1.0")
    console.print("Using AI to analyze Dependabot security alerts")


if __name__ == "__main__":
    app()
