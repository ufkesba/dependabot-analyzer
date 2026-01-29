import os
import json
from typing import List, Optional, Dict, Any
from github import Github, Auth
from pydantic import BaseModel
from rich.console import Console

console = Console()


def get_search_scope_from_manifest(manifest_path: str) -> str:
    """
    Derive search scope from manifest file path.

    For monorepos, this scopes searches to the relevant service/package directory.

    Examples:
        "package.json" -> "" (root, search everything)
        "services/serviceA/package.json" -> "services/serviceA"
        "packages/utils/package.json" -> "packages/utils"
        "apps/web/requirements.txt" -> "apps/web"

    Args:
        manifest_path: Path to the manifest file (package.json, requirements.txt, etc.)

    Returns:
        Directory path to scope searches, or empty string for root
    """
    if not manifest_path:
        return ""

    # Get directory containing the manifest
    manifest_dir = os.path.dirname(manifest_path)

    # Root manifest = search everything
    if not manifest_dir or manifest_dir == ".":
        return ""

    return manifest_dir


class MonorepoInfo(BaseModel):
    """Information about monorepo configuration"""
    is_monorepo: bool = False
    tool: Optional[str] = None  # npm-workspaces, yarn-workspaces, lerna, pnpm, nx, turborepo
    workspaces: List[str] = []  # List of workspace patterns/paths
    root_package_json: bool = False


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

        # Cache monorepo info (detected lazily)
        self._monorepo_info: Optional[MonorepoInfo] = None

    def detect_monorepo(self) -> MonorepoInfo:
        """
        Detect if the repository is a monorepo and what tooling it uses.

        Checks for:
        - npm/yarn workspaces in package.json
        - lerna.json
        - pnpm-workspace.yaml
        - nx.json
        - turbo.json

        Returns:
            MonorepoInfo with detection results
        """
        if self._monorepo_info is not None:
            return self._monorepo_info

        info = MonorepoInfo()

        # Check root package.json for workspaces
        try:
            pkg_content = self.repo.get_contents("package.json")
            pkg_json = json.loads(pkg_content.decoded_content.decode('utf-8'))
            info.root_package_json = True

            # Check for workspaces field
            workspaces = pkg_json.get("workspaces", [])
            if workspaces:
                # Handle both array and object format
                if isinstance(workspaces, dict):
                    workspaces = workspaces.get("packages", [])

                info.is_monorepo = True
                info.workspaces = workspaces
                info.tool = "npm-workspaces"

                # Check if it's specifically yarn
                try:
                    self.repo.get_contents("yarn.lock")
                    info.tool = "yarn-workspaces"
                except:
                    pass

        except Exception:
            pass

        # Check for lerna.json
        if not info.is_monorepo:
            try:
                lerna_content = self.repo.get_contents("lerna.json")
                lerna_json = json.loads(lerna_content.decoded_content.decode('utf-8'))
                info.is_monorepo = True
                info.tool = "lerna"
                info.workspaces = lerna_json.get("packages", ["packages/*"])
            except:
                pass

        # Check for pnpm-workspace.yaml
        if not info.is_monorepo:
            try:
                self.repo.get_contents("pnpm-workspace.yaml")
                info.is_monorepo = True
                info.tool = "pnpm"
                # Simple parsing - could be improved
                info.workspaces = ["packages/*"]
            except:
                pass

        # Check for nx.json
        if not info.is_monorepo:
            try:
                self.repo.get_contents("nx.json")
                info.is_monorepo = True
                info.tool = "nx"
            except:
                pass

        # Check for turbo.json
        if not info.is_monorepo:
            try:
                self.repo.get_contents("turbo.json")
                info.is_monorepo = True
                info.tool = "turborepo"
            except:
                pass

        self._monorepo_info = info

        if info.is_monorepo:
            console.print(f"[cyan]Detected monorepo: {info.tool}[/cyan]")
            if info.workspaces:
                console.print(f"[dim]Workspaces: {', '.join(info.workspaces[:5])}[/dim]")

        return info

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

        For monorepos, scopes the search to the directory containing the manifest.

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

            # Determine search scope from manifest path
            search_scope = get_search_scope_from_manifest(alert.manifest_path)

            # Try to get lock file for actual dependency versions
            lock_file_info = self._get_lock_file_info(alert.manifest_path, alert.package)

            # Search for usage of the package in the codebase (scoped)
            usage_examples = []
            package_name = alert.package

            # Search for require/import statements within scope
            try:
                # Start from scoped directory or root
                start_path = search_scope if search_scope else ""
                contents = self.repo.get_contents(start_path)

                if not isinstance(contents, list):
                    contents = [contents]

                files_to_search = []

                # Skip directories for faster collection
                skip_dirs = {'test', 'tests', '__tests__', '__mocks__', 'node_modules',
                            'venv', 'dist', 'build', '.git', 'coverage', 'fixtures', 'e2e'}

                def collect_files(contents):
                    for content in contents:
                        path_parts = content.path.split('/')
                        current_name = path_parts[-1].lower() if path_parts else ""

                        if content.type == "dir":
                            if current_name in skip_dirs:
                                continue
                            try:
                                collect_files(self.repo.get_contents(content.path))
                            except:
                                pass
                        elif content.name.endswith(('.js', '.ts', '.jsx', '.tsx', '.py', '.go', '.java', '.rb')):
                            # Skip test files
                            if not any(p in content.name.lower() for p in ['.test.', '.spec.', '_test.', '_spec.']):
                                files_to_search.append(content)

                collect_files(contents)

                # Search first 15 files for package usage (increased from 10)
                for file_content in files_to_search[:15]:
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

            # Build context string
            context_parts = [
                f"Manifest file: {alert.manifest_path}",
                f"Package: {alert.package}",
            ]

            if search_scope:
                context_parts.append(f"Search scope: {search_scope}/")

            context_parts.append(f"\nManifest content:\n{manifest_text[:1000]}")

            if lock_file_info:
                context_parts.append(f"\nLock file information:\n{lock_file_info}")

            context_parts.append(f"\nCode usage examples:\n{usage_text}")

            return "\n".join(context_parts)

        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch code context: {str(e)}[/yellow]")
            return f"Manifest file: {alert.manifest_path}\nPackage: {alert.package}"

    def _get_lock_file_info(self, manifest_path: str, package_name: str) -> Optional[str]:
        """
        Try to get dependency information from lock files.

        Supports:
        - package-lock.json (npm)
        - yarn.lock
        - pnpm-lock.yaml

        Args:
            manifest_path: Path to the manifest file
            package_name: Name of the package to look up

        Returns:
            String with lock file info, or None if not found
        """
        manifest_dir = os.path.dirname(manifest_path) or ""

        # Try different lock file types
        lock_files = [
            ("package-lock.json", self._parse_npm_lock),
            ("yarn.lock", self._parse_yarn_lock),
            ("pnpm-lock.yaml", self._parse_pnpm_lock),
        ]

        for lock_filename, parser in lock_files:
            lock_path = os.path.join(manifest_dir, lock_filename) if manifest_dir else lock_filename

            try:
                lock_content = self.repo.get_contents(lock_path)
                lock_text = lock_content.decoded_content.decode('utf-8')

                info = parser(lock_text, package_name)
                if info:
                    return f"Source: {lock_filename}\n{info}"

            except Exception:
                # Lock file doesn't exist or can't be parsed
                continue

        return None

    def _parse_npm_lock(self, lock_content: str, package_name: str) -> Optional[str]:
        """Parse package-lock.json for dependency info"""
        try:
            lock_data = json.loads(lock_content)

            # package-lock.json v2/v3 format
            packages = lock_data.get("packages", {})

            # Look for the package in dependencies
            info_parts = []

            for path, pkg_info in packages.items():
                if package_name in path:
                    version = pkg_info.get("version", "unknown")
                    resolved = pkg_info.get("resolved", "")
                    dev = pkg_info.get("dev", False)

                    info_parts.append(f"  - {path}: v{version}")
                    if dev:
                        info_parts.append("    (dev dependency)")
                    if resolved:
                        info_parts.append(f"    resolved: {resolved[:80]}...")

            # Also check legacy format (lockfileVersion 1)
            deps = lock_data.get("dependencies", {})
            if package_name in deps:
                pkg_info = deps[package_name]
                version = pkg_info.get("version", "unknown")
                dev = pkg_info.get("dev", False)
                info_parts.append(f"  - {package_name}: v{version}")
                if dev:
                    info_parts.append("    (dev dependency)")

            if info_parts:
                return "Installed versions:\n" + "\n".join(info_parts[:5])  # Limit output

        except json.JSONDecodeError:
            pass

        return None

    def _parse_yarn_lock(self, lock_content: str, package_name: str) -> Optional[str]:
        """Parse yarn.lock for dependency info (simple text parsing)"""
        try:
            info_parts = []
            lines = lock_content.split('\n')
            in_package = False
            current_version = None

            for line in lines:
                # yarn.lock format: "package@version":
                if line.startswith(f'"{package_name}@') or line.startswith(f'{package_name}@'):
                    in_package = True
                    continue

                if in_package:
                    if line.startswith('  version'):
                        # Extract version
                        version = line.split('"')[1] if '"' in line else line.split()[-1]
                        info_parts.append(f"  - {package_name}: v{version}")
                        in_package = False

                    # New package block starts
                    if line and not line.startswith(' '):
                        in_package = False

            if info_parts:
                return "Installed versions:\n" + "\n".join(info_parts[:3])

        except Exception:
            pass

        return None

    def _parse_pnpm_lock(self, lock_content: str, package_name: str) -> Optional[str]:
        """Parse pnpm-lock.yaml for dependency info (simple text parsing)"""
        try:
            info_parts = []

            # Simple search for package entries
            for line in lock_content.split('\n'):
                if f'/{package_name}/' in line or f"'{package_name}" in line:
                    # Extract version from path like /lodash/4.17.21:
                    if '/' in line:
                        parts = line.strip().rstrip(':').split('/')
                        for i, part in enumerate(parts):
                            if part == package_name and i + 1 < len(parts):
                                version = parts[i + 1].split(':')[0]
                                info_parts.append(f"  - {package_name}: v{version}")
                                break

            if info_parts:
                return "Installed versions:\n" + "\n".join(set(info_parts)[:3])

        except Exception:
            pass

        return None
