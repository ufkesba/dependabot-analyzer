import os
from typing import List, Optional
from github import Github, Auth
from pydantic import BaseModel
from rich.console import Console

console = Console()


class DependabotAlert(BaseModel):
    """Structured representation of a Dependabot security alert"""
    number: int
    state: str
    dependency: str
    package: str
    vulnerability_id: str
    cve_id: Optional[str] = None
    severity: str
    cvss_score: Optional[float] = None
    summary: str
    description: str
    affected_versions: str
    patched_versions: Optional[str] = None
    current_version: str
    manifest_path: str
    url: str


class AlertFetcher:
    """
    Fetches Dependabot security alerts from a GitHub repository.
    """

    def __init__(self, repo_name: str, github_token: Optional[str] = None):
        """
        Args:
            repo_name: Repository in format "owner/repo"
            github_token: GitHub personal access token (or from env)
        """
        self.repo_name = repo_name
        token = github_token or os.getenv("GITHUB_TOKEN")

        if not token:
            raise ValueError("GitHub token not found. Set GITHUB_TOKEN environment variable.")

        auth = Auth.Token(token)
        self.gh = Github(auth=auth)
        self.repo = self.gh.get_repo(repo_name)

    def get_alert_by_id(self, alert_id: int) -> Optional[DependabotAlert]:
        """
        Fetch a specific Dependabot alert by its ID.

        Args:
            alert_id: The alert number to fetch

        Returns:
            DependabotAlert object if found, None otherwise
        """
        console.print(f"[cyan]Fetching alert #{alert_id} from {self.repo_name}...[/cyan]")

        try:
            # Get specific Dependabot alert using the API endpoint
            url = f"/repos/{self.repo_name}/dependabot/alerts/{alert_id}"
            headers, alert = self.repo._requester.requestJsonAndCheck("GET", url)

            # Parse alert data from API response
            security_advisory = alert.get('security_advisory', {})
            security_vulnerability = alert.get('security_vulnerability', {})
            dependency = alert.get('dependency', {})

            alert_severity = security_advisory.get('severity', 'unknown').lower()

            # Extract CVE ID from identifiers
            cve_id = None
            for identifier in security_advisory.get('identifiers', []):
                if identifier.get('type') == 'CVE':
                    cve_id = identifier.get('value')
                    break

            dependabot_alert = DependabotAlert(
                number=alert.get('number'),
                state=alert.get('state', 'open'),
                dependency=dependency.get('package', {}).get('name', 'unknown'),
                package=dependency.get('package', {}).get('name', 'unknown'),
                vulnerability_id=security_advisory.get('ghsa_id', 'unknown'),
                cve_id=cve_id,
                severity=alert_severity,
                cvss_score=security_advisory.get('cvss', {}).get('score'),
                summary=security_advisory.get('summary', ''),
                description=security_advisory.get('description', ''),
                affected_versions=security_vulnerability.get('vulnerable_version_range', 'unknown'),
                patched_versions=security_vulnerability.get('first_patched_version', {}).get('identifier'),
                current_version=dependency.get('package', {}).get('ecosystem', 'unknown'),
                manifest_path=dependency.get('manifest_path', 'unknown'),
                url=alert.get('html_url', '')
            )

            console.print(f"[green]✓[/green] Found alert #{alert_id}")
            return dependabot_alert

        except Exception as e:
            console.print(f"[red]Error fetching alert #{alert_id}: {str(e)}[/red]")
            return None

    def get_alerts(
        self,
        state: str = "open",
        severity: Optional[List[str]] = None
    ) -> List[DependabotAlert]:
        """
        Fetch Dependabot alerts from the repository.

        Args:
            state: Alert state ("open", "fixed", "dismissed", or "all")
            severity: Filter by severity levels (e.g., ["high", "critical"])

        Returns:
            List of DependabotAlert objects
        """
        console.print(f"[cyan]Fetching {state} Dependabot alerts from {self.repo_name}...[/cyan]")

        try:
            # Get Dependabot alerts using the correct API endpoint
            # Note: This requires the repo to have Dependabot alerts enabled
            url = f"/repos/{self.repo_name}/dependabot/alerts"
            if state != "all":
                url += f"?state={state}"

            headers, data = self.repo._requester.requestJsonAndCheck("GET", url)

            dependabot_alerts = []
            alert_count = 0

            for alert in data:
                alert_count += 1

                # Parse alert data from API response
                security_advisory = alert.get('security_advisory', {})
                security_vulnerability = alert.get('security_vulnerability', {})
                dependency = alert.get('dependency', {})

                alert_severity = security_advisory.get('severity', 'unknown').lower()

                # Filter by severity if specified
                if severity and alert_severity not in [s.lower() for s in severity]:
                    continue

                # Extract CVE ID from identifiers
                cve_id = None
                for identifier in security_advisory.get('identifiers', []):
                    if identifier.get('type') == 'CVE':
                        cve_id = identifier.get('value')
                        break

                dependabot_alert = DependabotAlert(
                    number=alert.get('number'),
                    state=alert.get('state', 'open'),
                    dependency=dependency.get('package', {}).get('name', 'unknown'),
                    package=dependency.get('package', {}).get('name', 'unknown'),
                    vulnerability_id=security_advisory.get('ghsa_id', 'unknown'),
                    cve_id=cve_id,
                    severity=alert_severity,
                    cvss_score=security_advisory.get('cvss', {}).get('score'),
                    summary=security_advisory.get('summary', ''),
                    description=security_advisory.get('description', ''),
                    affected_versions=security_vulnerability.get('vulnerable_version_range', 'unknown'),
                    patched_versions=security_vulnerability.get('first_patched_version', {}).get('identifier'),
                    current_version=dependency.get('package', {}).get('ecosystem', 'unknown'),
                    manifest_path=dependency.get('manifest_path', 'unknown'),
                    url=alert.get('html_url', '')
                )

                dependabot_alerts.append(dependabot_alert)

            console.print(f"[green]✓[/green] Found {len(dependabot_alerts)} alerts matching criteria (scanned {alert_count} total)")
            return dependabot_alerts

        except Exception as e:
            console.print(f"[red]Error fetching alerts: {str(e)}[/red]")
            raise

    def get_code_context(self, alert: DependabotAlert, context_lines: int = 50) -> str:
        """
        Get code context around where the vulnerable dependency is used.

        Args:
            alert: The Dependabot alert
            context_lines: Number of lines of context to retrieve

        Returns:
            String containing relevant code context
        """
        try:
            # Get the manifest file (package.json, requirements.txt, etc.)
            manifest_content = self.repo.get_contents(alert.manifest_path)
            manifest_text = manifest_content.decoded_content.decode('utf-8')

            # Search for usage of the package in the codebase
            usage_examples = []
            package_name = alert.package

            # Search for require/import statements
            try:
                # Get all JavaScript/TypeScript files
                contents = self.repo.get_contents("")
                files_to_search = []

                def collect_files(contents):
                    for content in contents:
                        if content.type == "dir":
                            try:
                                collect_files(self.repo.get_contents(content.path))
                            except:
                                pass
                        elif content.name.endswith(('.js', '.ts', '.jsx', '.tsx', '.py')):
                            files_to_search.append(content)

                collect_files(contents)

                # Search first 10 files for package usage
                for file_content in files_to_search[:10]:
                    try:
                        file_text = file_content.decoded_content.decode('utf-8')
                        # Check if package is used
                        if package_name in file_text or f"require('{package_name}')" in file_text or f"from '{package_name}'" in file_text:
                            usage_examples.append(f"\n--- {file_content.path} ---\n{file_text[:2000]}")
                    except:
                        continue

            except Exception as e:
                console.print(f"[yellow]Warning: Could not search for package usage: {str(e)}[/yellow]")

            usage_text = "\n".join(usage_examples[:3]) if usage_examples else "No usage found in scanned files."

            return f"""
Manifest file: {alert.manifest_path}
Package: {alert.package}

Manifest content:
{manifest_text[:1000]}

Code usage examples:
{usage_text}
"""

        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch code context: {str(e)}[/yellow]")
            return f"Manifest file: {alert.manifest_path}\nPackage: {alert.package}"
