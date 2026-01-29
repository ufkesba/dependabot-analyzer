"""
Code analyzer that searches for actual vulnerable function usage patterns.
Goes beyond simple package imports to find real exploitable code paths.
"""
import re
import httpx
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
    vulnerable_functions: List[str]  # EXPOSED functions to search for in application code
    patterns: List[str]  # Regex patterns to match EXPOSED function usage
    description: str
    indicators: List[str]  # Additional indicators of vulnerability (e.g., "user input", "untrusted data")
    internal_function: Optional[str] = None  # Name of internal vulnerable function if mentioned in alert
    triggering_note: Optional[str] = None  # Explanation of how exposed APIs trigger internal function


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

    # Directories to skip during code search
    SKIP_DIRS = {
        'test', 'tests', '__tests__', '__mocks__', 'fixtures', 'e2e',
        'node_modules', 'venv', '.venv', 'env', '.env',
        'dist', 'build', 'out', '.next', '.nuxt',
        '.git', 'coverage', '.nyc_output',
        'vendor', 'third_party', 'external',
    }

    # File patterns that indicate test files
    TEST_FILE_PATTERNS = [
        '.test.', '.spec.', '_test.', '_spec.',
        '.tests.', '.specs.',
        'test_', 'spec_',
    ]

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

    def __init__(
        self,
        repo: Repository.Repository,
        llm_client: Optional['LLMClient'] = None,
        verbose: bool = False,
        search_scope: str = "",
        max_files: int = 150
    ):
        """
        Initialize the CodeAnalyzer.

        Args:
            repo: GitHub repository object
            llm_client: Optional LLM client for dynamic pattern extraction
            verbose: Enable verbose output
            search_scope: Directory path to scope searches (e.g., "services/serviceB").
                         Derived from manifest_path for monorepo support.
                         Empty string means search entire repo.
            max_files: Maximum number of files to scan (default 150)
        """
        self.repo = repo
        self.llm = llm_client  # Optional LLM for dynamic pattern extraction
        self.verbose = verbose
        self.search_scope = search_scope.rstrip('/') if search_scope else ""
        self.default_max_files = max_files

        if self.verbose and self.search_scope:
            console.print(f"[cyan]Code search scoped to: {self.search_scope}/[/cyan]")

    async def fetch_package_documentation(self, package_name: str) -> Optional[str]:
        """
        Fetch documentation for a package from multiple sources.

        Args:
            package_name: Name of the package

        Returns:
            Documentation text if found, None otherwise
        """
        if self.verbose:
            console.print(f"[cyan]Fetching documentation for {package_name}...[/cyan]")

        # Try npm first (most JavaScript packages)
        npm_docs = await self._fetch_npm_docs(package_name)
        if npm_docs:
            if self.verbose:
                console.print(f"[green]Found npm documentation for {package_name}[/green]")
            return npm_docs

        # Try PyPI for Python packages
        pypi_docs = await self._fetch_pypi_docs(package_name)
        if pypi_docs:
            if self.verbose:
                console.print(f"[green]Found PyPI documentation for {package_name}[/green]")
            return pypi_docs

        # Try GitHub README
        github_docs = await self._fetch_github_readme(package_name)
        if github_docs:
            if self.verbose:
                console.print(f"[green]Found GitHub README for {package_name}[/green]")
            return github_docs

        if self.verbose:
            console.print(f"[yellow]No documentation found for {package_name}[/yellow]")
        return None

    async def _fetch_npm_docs(self, package_name: str) -> Optional[str]:
        """Fetch package documentation from npm registry"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"https://registry.npmjs.org/{package_name}")
                if response.status_code == 200:
                    data = response.json()
                    readme = data.get("readme", "")
                    latest_version = data.get("dist-tags", {}).get("latest", "")

                    # Get latest version info for API details
                    version_info = data.get("versions", {}).get(latest_version, {})

                    docs = f"# {package_name} Documentation\n\n"
                    if readme:
                        docs += readme[:5000]  # Limit readme size

                    # Add main exports info if available
                    if "main" in version_info:
                        docs += f"\n\nMain entry: {version_info['main']}\n"

                    return docs
        except Exception as e:
            if self.verbose:
                console.print(f"[dim]npm fetch failed: {str(e)[:100]}[/dim]")
        return None

    async def _fetch_pypi_docs(self, package_name: str) -> Optional[str]:
        """Fetch package documentation from PyPI"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"https://pypi.org/pypi/{package_name}/json")
                if response.status_code == 200:
                    data = response.json()
                    info = data.get("info", {})
                    description = info.get("description", "") or info.get("summary", "")

                    docs = f"# {package_name} Documentation\n\n"
                    if description:
                        docs += description[:5000]  # Limit size

                    return docs
        except Exception as e:
            if self.verbose:
                console.print(f"[dim]PyPI fetch failed: {str(e)[:100]}[/dim]")
        return None

    async def _fetch_github_readme(self, package_name: str) -> Optional[str]:
        """Fetch README from GitHub for the package"""
        try:
            # Try to find the package's GitHub repo
            # Common patterns: org/package-name, package-name/package-name
            potential_repos = [
                f"{package_name}/{package_name}",
                f"npm/{package_name}",
                f"{package_name}/node-{package_name}",
            ]

            async with httpx.AsyncClient(timeout=10.0) as client:
                for repo_path in potential_repos:
                    try:
                        response = await client.get(
                            f"https://raw.githubusercontent.com/{repo_path}/main/README.md"
                        )
                        if response.status_code == 200:
                            return f"# {package_name} README\n\n{response.text[:5000]}"

                        # Try master branch if main doesn't exist
                        response = await client.get(
                            f"https://raw.githubusercontent.com/{repo_path}/master/README.md"
                        )
                        if response.status_code == 200:
                            return f"# {package_name} README\n\n{response.text[:5000]}"
                    except:
                        continue
        except Exception as e:
            if self.verbose:
                console.print(f"[dim]GitHub fetch failed: {str(e)[:100]}[/dim]")
        return None

    async def extract_api_info(self, package_name: str, documentation: str) -> Optional[Dict[str, any]]:
        """
        Use LLM to extract public API information from documentation.

        Args:
            package_name: Name of the package
            documentation: Documentation text

        Returns:
            Dictionary with exposed_apis and internal_notes
        """
        if not self.llm:
            return None

        prompt = f"""Analyze this package documentation and extract information about the PUBLIC API surface.

Package: {package_name}

Documentation:
{documentation}

Your task:
1. Identify the EXPOSED/PUBLIC functions, methods, and classes that application developers use
2. Distinguish these from internal/private implementation details
3. Note any parsing, processing, or data handling functions

Focus on:
- Top-level exports and public APIs
- Constructor functions and main entry points
- Commonly used methods mentioned in examples
- Functions that process user input or external data

Respond in JSON format:
{{
  "exposed_apis": ["list of public function/method names"],
  "parsing_functions": ["functions that parse/process data"],
  "internal_notes": "brief notes about internal vs public APIs"
}}
"""

        try:
            response_format = {
                "exposed_apis": ["array of strings"],
                "parsing_functions": ["array of strings"],
                "internal_notes": "string"
            }

            result = await self.llm.ask_structured(
                prompt=prompt,
                response_format=response_format,
                system_prompt="You are a technical documentation analyst extracting API information.",
                max_tokens=1500
            )

            return result
        except Exception as e:
            if self.verbose:
                console.print(f"[yellow]API extraction from docs failed: {str(e)[:100]}[/yellow]")
            return None

    async def extract_vulnerable_functions(
        self,
        package_name: str,
        vulnerability_description: str,
        vulnerability_summary: str,
        api_info: Optional[Dict[str, any]] = None
    ) -> Optional[VulnerabilityPattern]:
        """
        Use LLM to extract vulnerable functions from alert description.

        Args:
            package_name: Name of the vulnerable package
            vulnerability_description: Full vulnerability description
            vulnerability_summary: Short vulnerability summary
            api_info: Optional API information extracted from package documentation

        Returns:
            VulnerabilityPattern if functions can be extracted, None otherwise
        """
        if not self.llm:
            return None

        # Build API context section if available
        api_context = ""
        if api_info:
            api_context = f"""
## Package API Information (from documentation)

**Exposed/Public APIs:**
{', '.join(api_info.get('exposed_apis', [])) if api_info.get('exposed_apis') else 'Not available'}

**Parsing/Processing Functions:**
{', '.join(api_info.get('parsing_functions', [])) if api_info.get('parsing_functions') else 'Not available'}

**Notes:**
{api_info.get('internal_notes', 'No additional notes')}

Use this information to help distinguish between internal functions and exposed APIs.
"""

        prompt = f"""Analyze this security vulnerability alert and extract information about vulnerable and exposed functions.

Package: {package_name}
Summary: {vulnerability_summary}
Description: {vulnerability_description}
{api_context}

Your task is to identify WHICH FUNCTIONS applications should search for in their code.

## CRITICAL: Internal vs Exposed Functions

Many vulnerabilities occur in **internal library functions** that applications never call directly.
Instead, they are triggered **indirectly** through **exposed API functions**.

**Your job**: Identify the EXPOSED API functions that applications actually call, NOT internal implementation details.

### How to Identify:

**Internal Vulnerable Function** (DO NOT return these):
- Usually mentioned in technical details (e.g., "the vulnerability is in the internal X parser")
- Implementation details, helper functions, recursive parsers
- Private methods, internal utilities
- Applications don't import or call these directly

**Exposed API Functions** (DO return these):
- Public APIs that applications import and call
- Entry points to the library's functionality
- Based on the vulnerability description, which exposed APIs would trigger the vulnerable code path?
- Consider: What operations would cause the internal vulnerable function to execute?

### Decision Logic:

1. Read the vulnerability description carefully
2. Identify if a specific internal function is mentioned as vulnerable
3. If YES: Reason about which PUBLIC/EXPOSED APIs would call that internal function
   - Think: "What would an application developer call to trigger this?"
   - Look for clues in the description about operations (parsing, decoding, processing, etc.)
4. If the description mentions exposed functions directly, return those
5. If unclear or too general, return empty arrays

### Response Format Examples:

**Example 1: Internal Parser Function**
Alert: "Unbounded recursion in internal parser causes DoS when processing deeply nested structures"

Reasoning: The vulnerability is in an internal parser. What exposed APIs trigger parsing?
- Look at the description for clues about what operation triggers it
- Consider: certificate parsing, data decoding, template processing, etc.

Output: {{
  "vulnerable_functions": ["<public APIs that trigger parsing based on the description>"],
  "patterns": ["<regex for those public APIs>"],
  "indicators": ["untrusted input", "user-provided data", "external source"],
  "description": "DoS via unbounded recursion in parsing",
  "internal_function": "<name of internal function if mentioned>",
  "triggering_note": "Applications trigger this by using <type of operation> functions with untrusted input"
}}

**Example 2: Directly Exposed Function**
Alert: "Command Injection via template compilation function when user input is passed"

Reasoning: The vulnerability IS in the exposed API itself

Output: {{
  "vulnerable_functions": ["<template function names from description>"],
  "patterns": ["<regex for template functions>"],
  "indicators": ["user input", "req.body", "external template"],
  "description": "Command injection via template compilation",
  "internal_function": null,
  "triggering_note": null
}}

**Example 3: General Package Behavior**
Alert: "Denial of Service due to improper header parsing in HTTP client"

Reasoning: No specific function mentioned, general behavior

Output: {{
  "vulnerable_functions": [],
  "patterns": [],
  "indicators": ["http headers", "user-controlled headers"],
  "description": "DoS via malformed HTTP headers",
  "internal_function": null,
  "triggering_note": "Affects general request handling, not a specific function"
}}

## Key Principles:

1. **Think like an application developer**: What functions would they actually call?
2. **Extract from description**: Use clues about operations (parsing, encoding, templating, etc.)
3. **Don't guess**: If the description doesn't provide enough information, return empty arrays
4. **Prefer exposed over internal**: Always return the public-facing APIs

Respond in JSON format with these fields:
- vulnerable_functions: Array of EXPOSED function names to search for (empty if unclear)
- patterns: Array of regex patterns matching the EXPOSED functions
- indicators: Array of strings indicating exploitation context
- description: Brief description of the vulnerability
- internal_function: String naming the internal vulnerable function if explicitly mentioned, null otherwise
- triggering_note: String explaining the relationship between exposed APIs and internal function, null if not applicable
"""

        try:
            response_format = {
                "vulnerable_functions": ["array of strings - EXPOSED APIs to search for"],
                "patterns": ["array of regex strings"],
                "indicators": ["array of strings"],
                "description": "string",
                "internal_function": "string or null - the actual vulnerable internal function",
                "triggering_note": "string or null - explanation of how exposed APIs trigger it"
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
                indicators=result.get("indicators", []),
                internal_function=result.get("internal_function"),
                triggering_note=result.get("triggering_note")
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
        max_files: Optional[int] = None,
        vulnerability_description: Optional[str] = None,
        vulnerability_summary: Optional[str] = None
    ) -> List[CodeMatch]:
        """
        Search codebase for actual vulnerable function usage.

        Args:
            package_name: Name of the vulnerable package
            vulnerability_id: The vulnerability ID (GHSA, CVE, etc.)
            max_files: Maximum number of files to scan (uses default_max_files if not specified)
            vulnerability_description: Full vulnerability description (for LLM extraction)
            vulnerability_summary: Short vulnerability summary (for LLM extraction)

        Returns:
            List of CodeMatch objects showing vulnerable usage
        """
        # Use instance default if not specified
        if max_files is None:
            max_files = self.default_max_files

        if self.verbose:
            scope_msg = f" in {self.search_scope}/" if self.search_scope else ""
            console.print(f"[cyan]Searching for vulnerable usage of {package_name}{scope_msg}...[/cyan]")

        # Get vulnerability pattern if we have it (fast path)
        pattern = self._get_vulnerability_pattern(package_name, vulnerability_id)

        # If no hardcoded pattern, try LLM extraction
        if not pattern and self.llm and vulnerability_description:
            if self.verbose:
                console.print(f"[cyan]No hardcoded pattern found, using LLM to extract vulnerable functions...[/cyan]")

            # Fetch package documentation to help identify exposed vs internal functions
            api_info = None
            docs = await self.fetch_package_documentation(package_name)
            if docs:
                api_info = await self.extract_api_info(package_name, docs)

            pattern = await self.extract_vulnerable_functions(
                package_name,
                vulnerability_description,
                vulnerability_summary or "",
                api_info=api_info
            )

        # If still no pattern, fall back to generic search
        if not pattern:
            if self.verbose:
                console.print(f"[yellow]No specific vulnerable functions identified, using generic search[/yellow]")
            return self._generic_package_search(package_name, max_files)

        # Display what vulnerable functions we're searching for
        if self.verbose:
            console.print(f"[cyan]Searching for vulnerable functions:[/cyan] {', '.join(pattern.vulnerable_functions)}")
            if pattern.patterns:
                console.print(f"[dim]Using {len(pattern.patterns)} regex patterns[/dim]")

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

    def _is_test_file(self, file_path: str) -> bool:
        """
        Check if a file path indicates a test file.

        Handles patterns like:
        - *.test.ts, *.spec.js
        - test_*.py, spec_*.rb
        - Files in test directories
        """
        file_lower = file_path.lower()

        # Check for test file naming patterns
        for pattern in self.TEST_FILE_PATTERNS:
            if pattern in file_lower:
                return True

        # Check if file is in a test-related directory
        path_parts = file_path.split('/')
        for part in path_parts[:-1]:  # Check directories, not filename
            if part.lower() in self.SKIP_DIRS:
                return True

        return False

    def _is_test_or_comment(self, line: str) -> bool:
        """Check if line is a test, comment, or non-production code"""
        line_lower = line.lower().strip()

        # Check for comments
        if line_lower.startswith('//') or line_lower.startswith('#'):
            return True

        # Check for test patterns in the line content
        test_indicators = [
            'test(',
            'describe(',
            'it(',
            'expect(',
            'assert.',
            'jest.',
            'mocha.',
            'chai.',
            'sinon.',
            'pytest.',
            'unittest.',
            'curl ',
            'echo ',
            '// test',
            '# test',
            '@test',
            '@pytest',
        ]

        return any(indicator in line_lower for indicator in test_indicators)

    def _get_code_files(self, max_files: int = 150):
        """
        Get code files from repository, scoped to search_scope directory.

        For monorepos, this ensures we only search within the relevant
        service/package directory based on the manifest_path.
        """
        files_to_search = []

        try:
            # Start from scoped directory or repo root
            start_path = self.search_scope if self.search_scope else ""

            if self.verbose and start_path:
                console.print(f"[dim]→ Searching files in: {start_path}/[/dim]")

            contents = self.repo.get_contents(start_path)

            # Handle case where start_path is a single file (shouldn't happen, but be safe)
            if not isinstance(contents, list):
                contents = [contents]

            self._collect_files_recursive(contents, files_to_search, max_files)

            if self.verbose:
                console.print(f"[dim]→ Found {len(files_to_search)} code files to scan[/dim]")

        except Exception as e:
            console.print(f"[yellow]Warning: Error collecting files: {str(e)}[/yellow]")
            # If scoped path fails, try falling back to root (with warning)
            if self.search_scope:
                console.print(f"[yellow]Falling back to root search...[/yellow]")
                try:
                    contents = self.repo.get_contents("")
                    self._collect_files_recursive(contents, files_to_search, max_files)
                except Exception as e2:
                    console.print(f"[red]Root search also failed: {str(e2)}[/red]")

        return files_to_search

    def _collect_files_recursive(self, contents, files_list: List, max_files: int):
        """Recursively collect code files, skipping test/build directories"""
        if len(files_list) >= max_files:
            return

        for content in contents:
            if len(files_list) >= max_files:
                break

            # Get the last path component for directory checking
            path_parts = content.path.split('/')
            current_name = path_parts[-1].lower() if path_parts else ""

            # Skip directories that don't contain production code
            if content.type == "dir":
                # Check if this directory name should be skipped
                if current_name in self.SKIP_DIRS:
                    continue
                # Also skip if any parent path component is a skip dir
                if any(part.lower() in self.SKIP_DIRS for part in path_parts):
                    continue

                try:
                    self._collect_files_recursive(
                        self.repo.get_contents(content.path),
                        files_list,
                        max_files
                    )
                except:
                    pass
            elif self._is_code_file(content.name) and not self._is_test_file(content.path):
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
