"""
Code analyzer that searches for actual vulnerable function usage patterns.
Goes beyond simple package imports to find real exploitable code paths.
"""
import re
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel
from rich.console import Console
from github import Repository

console = Console()

# Import only for type hints, actual LLM client passed in
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..llm.client import LLMClient


class VulnerabilityPattern(BaseModel):
    """Pattern to match vulnerable code usage"""
    package: str
    vulnerability_id: str
    vulnerable_functions: List[str]  # Functions/methods that are vulnerable
    patterns: List[str]  # Regex patterns to match vulnerable usage
    description: str
    indicators: List[str]  # Additional indicators of vulnerability


class CodeMatch(BaseModel):
    """A match of vulnerable code"""
    file_path: str
    line_number: int
    code_snippet: str
    matched_pattern: str
    context: str  # Surrounding code for context


class CodeAnalyzer:
    """
    Analyzes code to find actual vulnerable function usage patterns.
    """

    # Known vulnerability patterns for common packages
    VULNERABILITY_PATTERNS = {
        "axios": {
            "GHSA-wf5p-g6vw-rhxx": VulnerabilityPattern(
                package="axios",
                vulnerability_id="GHSA-wf5p-g6vw-rhxx",
                vulnerable_functions=["axios.get", "axios.post", "axios"],
                patterns=[
                    r"axios\.get\(['\"]data:",  # Direct data: URI usage
                    r"axios\.post\(['\"]data:",
                    r"axios\(['\"]data:",
                    r"axios\([^)]*url[^)]*data:",  # URL parameter with data:
                ],
                description="Axios data: URI DoS vulnerability",
                indicators=[
                    "user-controlled URL",
                    "external URL input",
                    "request URL from query/body",
                    "untrusted URL source"
                ]
            )
        },
        "express": {
            "prototype-pollution": VulnerabilityPattern(
                package="express",
                vulnerability_id="prototype-pollution",
                vulnerable_functions=["express.json", "express.urlencoded"],
                patterns=[
                    r"express\.json\(\)",
                    r"express\.urlencoded\(",
                ],
                description="Express body parser prototype pollution",
                indicators=[
                    "req.body",
                    "Object.assign",
                    "merge objects",
                ]
            )
        },
        "lodash": {
            "GHSA-35jh-r3h4-6jhm": VulnerabilityPattern(
                package="lodash",
                vulnerability_id="GHSA-35jh-r3h4-6jhm",
                vulnerable_functions=["_.template", "lodash.template"],
                patterns=[
                    r"_\.template\(",
                    r"lodash\.template\(",
                ],
                description="Command Injection via template function",
                indicators=[
                    "user input",
                    "req.body",
                    "req.query",
                    "req.params",
                    "untrusted data"
                ]
            ),
            "GHSA-29mw-wpgm-hmr9": VulnerabilityPattern(
                package="lodash",
                vulnerability_id="GHSA-29mw-wpgm-hmr9",
                vulnerable_functions=["_.merge", "_.mergeWith", "_.defaultsDeep"],
                patterns=[
                    r"_\.merge\(",
                    r"_\.mergeWith\(",
                    r"_\.defaultsDeep\(",
                    r"lodash\.merge\(",
                    r"lodash\.mergeWith\(",
                    r"lodash\.defaultsDeep\(",
                ],
                description="Prototype Pollution via merge functions",
                indicators=[
                    "req.body",
                    "req.query",
                    "user input",
                    "JSON.parse",
                    "untrusted object"
                ]
            ),
            "GHSA-jf85-cpcp-j695": VulnerabilityPattern(
                package="lodash",
                vulnerability_id="GHSA-jf85-cpcp-j695",
                vulnerable_functions=["_.zipObjectDeep"],
                patterns=[
                    r"_\.zipObjectDeep\(",
                    r"lodash\.zipObjectDeep\(",
                ],
                description="Prototype Pollution via zipObjectDeep",
                indicators=[
                    "user input",
                    "req.body",
                    "untrusted array"
                ]
            )
        }
    }

    def __init__(self, repo: Repository.Repository, llm_client: Optional['LLMClient'] = None, verbose: bool = False):
        self.repo = repo
        self.llm = llm_client  # Optional LLM for dynamic pattern extraction
        self.verbose = verbose

    async def extract_vulnerable_functions(
        self,
        package_name: str,
        vulnerability_description: str,
        vulnerability_summary: str
    ) -> Optional[VulnerabilityPattern]:
        """
        Use LLM to extract vulnerable functions from alert description.

        Args:
            package_name: Name of the vulnerable package
            vulnerability_description: Full vulnerability description
            vulnerability_summary: Short vulnerability summary

        Returns:
            VulnerabilityPattern if functions can be extracted, None otherwise
        """
        if not self.llm:
            return None

        prompt = f"""Analyze this security vulnerability alert and extract the vulnerable functions.

Package: {package_name}
Summary: {vulnerability_summary}
Description: {vulnerability_description}

Your task is to identify:
1. Which specific functions/methods in this package are vulnerable (if any are mentioned)
2. What regex patterns would match usage of these vulnerable functions
3. What indicators suggest the vulnerability is being exploited (e.g., "user input", "req.body")

IMPORTANT:
- Some vulnerabilities affect ALL uses of a package, not specific functions. If no specific functions are mentioned, return empty arrays.
- Only include functions that are explicitly mentioned as vulnerable in the description.
- If the vulnerability is version-based only (e.g., "all versions below X.Y.Z are vulnerable") with no specific function mentioned, return empty arrays.

Examples:

Example 1 (Specific functions):
Alert: "Command Injection in lodash via _.template() when user-controlled input is passed"
Output: {{
  "vulnerable_functions": ["_.template", "lodash.template"],
  "patterns": ["_\\\\.template\\\\(", "lodash\\\\.template\\\\("],
  "indicators": ["user input", "req.body", "req.query", "req.params"]
}}

Example 2 (No specific functions):
Alert: "Denial of Service in axios versions below 1.2.3 due to improper header parsing"
Output: {{
  "vulnerable_functions": [],
  "patterns": [],
  "indicators": ["http headers", "user-controlled headers"]
}}

Example 3 (Multiple functions):
Alert: "Prototype Pollution in lodash via _.merge, _.mergeWith, and _.defaultsDeep"
Output: {{
  "vulnerable_functions": ["_.merge", "_.mergeWith", "_.defaultsDeep", "lodash.merge", "lodash.mergeWith", "lodash.defaultsDeep"],
  "patterns": ["_\\\\.merge\\\\(", "_\\\\.mergeWith\\\\(", "_\\\\.defaultsDeep\\\\(", "lodash\\\\.merge\\\\(", "lodash\\\\.mergeWith\\\\(", "lodash\\\\.defaultsDeep\\\\("],
  "indicators": ["req.body", "req.query", "JSON.parse", "user input"]
}}

Respond in JSON format with these fields:
- vulnerable_functions: Array of function names (empty if no specific functions mentioned)
- patterns: Array of regex patterns to search for (empty if no specific functions)
- indicators: Array of strings that indicate exploitation (can be populated even if no specific functions)
- description: Brief description of the vulnerability
"""

        try:
            response_format = {
                "vulnerable_functions": ["array of strings"],
                "patterns": ["array of regex strings"],
                "indicators": ["array of strings"],
                "description": "string"
            }

            result = await self.llm.ask_structured(
                prompt=prompt,
                response_format=response_format,
                system_prompt="You are a security expert analyzing vulnerability descriptions to extract vulnerable function names and search patterns.",
                max_tokens=2000
            )

            # If no vulnerable functions found, return None
            if not result.get("vulnerable_functions") or len(result["vulnerable_functions"]) == 0:
                if self.verbose:
                    console.print(f"[yellow]LLM found no specific vulnerable functions for {package_name}[/yellow]")
                return None

            # Create VulnerabilityPattern from LLM response
            pattern = VulnerabilityPattern(
                package=package_name,
                vulnerability_id="llm_extracted",
                vulnerable_functions=result["vulnerable_functions"],
                patterns=result["patterns"],
                description=result["description"],
                indicators=result.get("indicators", [])
            )

            if self.verbose:
                console.print(f"[green]LLM extracted {len(pattern.vulnerable_functions)} vulnerable functions[/green]")
            return pattern

        except Exception as e:
            if self.verbose:
                console.print(f"[yellow]LLM extraction failed: {str(e)[:200]}[/yellow]")
            return None

    async def find_vulnerable_usage(
        self,
        package_name: str,
        vulnerability_id: str,
        max_files: int = 50,
        vulnerability_description: Optional[str] = None,
        vulnerability_summary: Optional[str] = None
    ) -> List[CodeMatch]:
        """
        Search codebase for actual vulnerable function usage.

        Args:
            package_name: Name of the vulnerable package
            vulnerability_id: The vulnerability ID (GHSA, CVE, etc.)
            max_files: Maximum number of files to scan
            vulnerability_description: Full vulnerability description (for LLM extraction)
            vulnerability_summary: Short vulnerability summary (for LLM extraction)

        Returns:
            List of CodeMatch objects showing vulnerable usage
        """
        if self.verbose:
            console.print(f"[cyan]Searching for vulnerable usage of {package_name}...[/cyan]")

        # Get vulnerability pattern if we have it (fast path)
        pattern = self._get_vulnerability_pattern(package_name, vulnerability_id)

        # If no hardcoded pattern, try LLM extraction
        if not pattern and self.llm and vulnerability_description:
            if self.verbose:
                console.print(f"[cyan]No hardcoded pattern found, using LLM to extract vulnerable functions...[/cyan]")
            pattern = await self.extract_vulnerable_functions(
                package_name,
                vulnerability_description,
                vulnerability_summary or ""
            )

        # If still no pattern, fall back to generic search
        if not pattern:
            if self.verbose:
                console.print(f"[yellow]No specific vulnerable functions identified, using generic search[/yellow]")
            return self._generic_package_search(package_name, max_files)

        matches = []
        files_scanned = 0

        try:
            # Get relevant files
            files = self._get_code_files(max_files)

            for file_content in files:
                if files_scanned >= max_files:
                    break

                files_scanned += 1

                try:
                    file_text = file_content.decoded_content.decode('utf-8')

                    # First check if package is imported/required
                    if not self._has_package_import(file_text, package_name):
                        continue

                    # Now look for vulnerable patterns
                    file_matches = self._find_patterns_in_file(
                        file_text,
                        file_content.path,
                        pattern
                    )
                    matches.extend(file_matches)

                except Exception as e:
                    if self.verbose:
                        console.print(f"[dim]Skipping {file_content.path}: {str(e)}[/dim]")
                    continue

            if self.verbose:
                console.print(f"[green]Found {len(matches)} potential vulnerable usage patterns in {files_scanned} files[/green]")

        except Exception as e:
            if self.verbose:
                console.print(f"[red]Error during code analysis: {str(e)}[/red]")

        return matches

    def _get_vulnerability_pattern(
        self,
        package_name: str,
        vulnerability_id: str
    ) -> Optional[VulnerabilityPattern]:
        """Get the vulnerability pattern for a package/vulnerability"""
        package_patterns = self.VULNERABILITY_PATTERNS.get(package_name, {})
        return package_patterns.get(vulnerability_id)

    def _has_package_import(self, file_text: str, package_name: str) -> bool:
        """Check if file imports/requires the package"""
        import_patterns = [
            rf"require\(['\"]({package_name})['\"]",
            rf"from\s+['\"]({package_name})['\"]",
            rf"import\s+.*from\s+['\"]({package_name})['\"]",
            rf"import\s+({package_name})",
        ]

        for pattern in import_patterns:
            if re.search(pattern, file_text):
                return True
        return False

    def _find_patterns_in_file(
        self,
        file_text: str,
        file_path: str,
        pattern: VulnerabilityPattern
    ) -> List[CodeMatch]:
        """Find vulnerable patterns in a file"""
        matches = []
        lines = file_text.split('\n')

        for i, line in enumerate(lines, 1):
            # Check each vulnerability pattern
            for regex_pattern in pattern.patterns:
                if re.search(regex_pattern, line):
                    # Found a match! Get context
                    context_start = max(0, i - 5)
                    context_end = min(len(lines), i + 5)
                    context = '\n'.join(lines[context_start:context_end])

                    match = CodeMatch(
                        file_path=file_path,
                        line_number=i,
                        code_snippet=line.strip(),
                        matched_pattern=regex_pattern,
                        context=context
                    )
                    matches.append(match)

        return matches

    def _generic_package_search(
        self,
        package_name: str,
        max_files: int
    ) -> List[CodeMatch]:
        """Generic search for package usage when no specific pattern exists"""
        matches = []
        files = self._get_code_files(max_files)

        for file_content in files[:10]:  # Limit generic search
            try:
                file_text = file_content.decoded_content.decode('utf-8')

                if package_name in file_text:
                    lines = file_text.split('\n')
                    for i, line in enumerate(lines, 1):
                        if package_name in line and not self._is_test_or_comment(line):
                            context_start = max(0, i - 3)
                            context_end = min(len(lines), i + 3)
                            context = '\n'.join(lines[context_start:context_end])

                            match = CodeMatch(
                                file_path=file_content.path,
                                line_number=i,
                                code_snippet=line.strip(),
                                matched_pattern="generic_usage",
                                context=context
                            )
                            matches.append(match)
            except:
                continue

        return matches

    def _is_test_or_comment(self, line: str) -> bool:
        """Check if line is a test, comment, or non-production code"""
        line_lower = line.lower().strip()

        # Check for comments
        if line_lower.startswith('//') or line_lower.startswith('#'):
            return True

        # Check for test patterns
        test_indicators = [
            'test(',
            'describe(',
            'it(',
            'expect(',
            'curl ',
            'echo ',
            '// test',
            '# test',
        ]

        return any(indicator in line_lower for indicator in test_indicators)

    def _get_code_files(self, max_files: int = 50):
        """Get code files from repository"""
        files_to_search = []

        try:
            contents = self.repo.get_contents("")
            self._collect_files_recursive(contents, files_to_search, max_files)
        except Exception as e:
            console.print(f"[yellow]Warning: Error collecting files: {str(e)}[/yellow]")

        return files_to_search

    def _collect_files_recursive(self, contents, files_list: List, max_files: int):
        """Recursively collect code files"""
        if len(files_list) >= max_files:
            return

        for content in contents:
            if len(files_list) >= max_files:
                break

            # Skip common directories that don't contain production code
            skip_dirs = ['test', 'tests', '__tests__', 'node_modules', 'venv',
                        'dist', 'build', '.git', 'coverage']
            if any(skip in content.path for skip in skip_dirs):
                continue

            if content.type == "dir":
                try:
                    self._collect_files_recursive(
                        self.repo.get_contents(content.path),
                        files_list,
                        max_files
                    )
                except:
                    pass
            elif self._is_code_file(content.name):
                files_list.append(content)

    def _is_code_file(self, filename: str) -> bool:
        """Check if file is a source code file"""
        code_extensions = [
            '.js', '.ts', '.jsx', '.tsx',
            '.py', '.java', '.go', '.rb',
            '.php', '.cs', '.cpp', '.c'
        ]
        return any(filename.endswith(ext) for ext in code_extensions)

    def analyze_exploitability(
        self,
        matches: List[CodeMatch],
        vulnerability_pattern: Optional[VulnerabilityPattern]
    ) -> Tuple[bool, str]:
        """
        Analyze if the found matches are actually exploitable.

        Returns:
            Tuple of (is_exploitable, reasoning)
        """
        if not matches:
            return False, "Package is imported but no vulnerable function usage found"

        # Filter out test code
        production_matches = [
            m for m in matches
            if not any(skip in m.file_path.lower()
                      for skip in ['test', '__test__', 'spec', 'mock'])
        ]

        if not production_matches:
            return False, f"Found {len(matches)} matches but all appear to be in test/mock code"

        if vulnerability_pattern:
            # Check for indicators
            reasoning_parts = [
                f"Found {len(production_matches)} vulnerable function usage(s) in production code:"
            ]

            for match in production_matches[:3]:  # Show top 3
                reasoning_parts.append(
                    f"- {match.file_path}:{match.line_number}: {match.code_snippet}"
                )

            return True, "\n".join(reasoning_parts)

        return True, f"Found {len(production_matches)} usage(s) of package in production code"
