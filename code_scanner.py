"""Code repository scanning and extraction."""

import ast
import json
import re
from pathlib import Path
from typing import Optional
from subprocess import run, PIPE

from rich.console import Console

from .models import CodeAnalysisConfig


class CodeScanner:
    """Scans code repositories to extract documentation-relevant information."""

    def __init__(self, config: CodeAnalysisConfig):
        """Initialize code scanner.

        Args:
            config: Code analysis configuration
        """
        self.config = config
        self.console = Console()

    def scan_repos(self) -> dict:
        """Scan repositories and extract information.

        Returns:
            Extracted information organized by type
        """
        if not self.config.enabled or not self.config.repos:
            return {}

        results = {
            "apis": [],
            "architecture": [],
            "dependencies": [],
            "classes": [],
            "functions": [],
            "config": [],
            "errors": [],
            "examples": [],
        }

        for repo_config in self.config.repos:
            repo_path = Path(repo_config.get("path"))
            if not repo_path.is_absolute():
                repo_path = Path("/Users/craighoad/Repos") / repo_path

            if not repo_path.exists():
                self.console.print(f"[yellow]Warning: Repo not found: {repo_path}[/yellow]")
                continue

            self.console.print(f"[blue]Scanning: {repo_path}[/blue]")

            # Scan for each extraction type
            if "apis" in self.config.extract:
                results["apis"].extend(self._extract_apis(repo_path, repo_config))

            if "architecture" in self.config.extract:
                results["architecture"].extend(self._extract_architecture(repo_path, repo_config))

            if "dependencies" in self.config.extract:
                results["dependencies"].extend(self._extract_dependencies(repo_path, repo_config))

            if "classes" in self.config.extract:
                results["classes"].extend(self._extract_classes(repo_path, repo_config))

            if "functions" in self.config.extract:
                results["functions"].extend(self._extract_functions(repo_path, repo_config))

        return results

    def _get_files(self, repo_path: Path, repo_config: dict) -> list[Path]:
        """Get files matching include/exclude patterns.

        Args:
            repo_path: Repository path
            repo_config: Repository configuration

        Returns:
            List of file paths
        """
        include_patterns = repo_config.get("include_patterns", ["**/*.py", "**/*.ts", "**/*.go"])
        exclude_patterns = repo_config.get("exclude_patterns", [])

        files = []
        for pattern in include_patterns:
            files.extend(repo_path.glob(pattern))

        # Filter by exclude patterns
        filtered = []
        for f in files:
            excluded = False
            for pattern in exclude_patterns:
                if f.match(pattern):
                    excluded = True
                    break
            if not excluded:
                filtered.append(f)

        # Limit file count
        return filtered[: self.config.max_files_to_analyze]

    def _extract_apis(self, repo_path: Path, repo_config: dict) -> list[dict]:
        """Extract API endpoints and routes.

        Args:
            repo_path: Repository path
            repo_config: Repository configuration

        Returns:
            List of API information
        """
        apis = []

        # Look for common API patterns
        for file_path in self._get_files(repo_path, repo_config):
            if file_path.suffix == ".py":
                apis.extend(self._extract_python_apis(file_path))
            elif file_path.suffix in [".ts", ".js"]:
                apis.extend(self._extract_typescript_apis(file_path))
            elif file_path.suffix == ".go":
                apis.extend(self._extract_go_apis(file_path))

        return apis

    def _extract_python_apis(self, file_path: Path) -> list[dict]:
        """Extract Python API endpoints (Flask, FastAPI, Django).

        Args:
            file_path: Python file path

        Returns:
            List of API definitions
        """
        apis = []

        try:
            with open(file_path) as f:
                content = f.read()

            # Find Flask/FastAPI routes
            route_patterns = [
                r'@(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
                r'@(?:app|router)\.route\(["\']([^"\']+)["\'].*methods=\[([^\]]+)\]',
            ]

            for pattern in route_patterns:
                for match in re.finditer(pattern, content):
                    apis.append({
                        "type": "endpoint",
                        "method": match.group(1).upper() if match.lastindex >= 1 else "GET",
                        "path": match.group(2) if match.lastindex >= 2 else "",
                        "file": str(file_path),
                    })
        except Exception as e:
            self.console.print(f"[yellow]Error parsing {file_path}: {e}[/yellow]")

        return apis

    def _extract_typescript_apis(self, file_path: Path) -> list[dict]:
        """Extract TypeScript API endpoints (Express, NestJS).

        Args:
            file_path: TypeScript file path

        Returns:
            List of API definitions
        """
        apis = []

        try:
            with open(file_path) as f:
                content = f.read()

            # Find Express/NestJS routes
            patterns = [
                r'app\.(?:get|post|put|delete|patch)\(["\']([^"\']+)["\']',
                r'@(?:Get|Post|Put|Delete|Patch)\(["\']([^"\']+)["\']',
            ]

            for pattern in patterns:
                for match in re.finditer(pattern, content):
                    apis.append({
                        "type": "endpoint",
                        "path": match.group(1),
                        "file": str(file_path),
                    })
        except Exception as e:
            self.console.print(f"[yellow]Error parsing {file_path}: {e}[/yellow]")

        return apis

    def _extract_go_apis(self, file_path: Path) -> list[dict]:
        """Extract Go API endpoints.

        Args:
            file_path: Go file path

        Returns:
            List of API definitions
        """
        apis = []

        try:
            with open(file_path) as f:
                content = f.read()

            # Find router definitions
            pattern = r'r\.(?:GET|POST|PUT|DELETE)\(["\']([^"\']+)["\']'

            for match in re.finditer(pattern, content):
                apis.append({
                    "type": "endpoint",
                    "path": match.group(1),
                    "file": str(file_path),
                })
        except Exception as e:
            self.console.print(f"[yellow]Error parsing {file_path}: {e}[/yellow]")

        return apis

    def _extract_architecture(self, repo_path: Path, repo_config: dict) -> list[dict]:
        """Extract architectural information.

        Args:
            repo_path: Repository path
            repo_config: Repository configuration

        Returns:
            List of architecture information
        """
        architecture = []

        # Count file types
        file_counts = {}
        for file_path in self._get_files(repo_path, repo_config):
            ext = file_path.suffix
            file_counts[ext] = file_counts.get(ext, 0) + 1

        architecture.append({
            "type": "file_structure",
            "summary": f"Repository contains {len(file_counts)} file types",
            "details": file_counts,
        })

        return architecture

    def _extract_dependencies(self, repo_path: Path, repo_config: dict) -> list[dict]:
        """Extract dependencies from manifest files.

        Args:
            repo_path: Repository path
            repo_config: Repository configuration

        Returns:
            List of dependencies
        """
        dependencies = []

        # Check for Python requirements
        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            dependencies.append({
                                "type": "python",
                                "name": line.split("==")[0].split(">=")[0],
                                "spec": line,
                            })
            except Exception as e:
                self.console.print(f"[yellow]Error reading requirements.txt: {e}[/yellow]")

        # Check for Node packages
        pkg_json = repo_path / "package.json"
        if pkg_json.exists():
            try:
                with open(pkg_json) as f:
                    data = json.load(f)
                    for pkg, version in data.get("dependencies", {}).items():
                        dependencies.append({
                            "type": "npm",
                            "name": pkg,
                            "version": version,
                        })
            except Exception as e:
                self.console.print(f"[yellow]Error reading package.json: {e}[/yellow]")

        return dependencies

    def _extract_classes(self, repo_path: Path, repo_config: dict) -> list[dict]:
        """Extract class definitions.

        Args:
            repo_path: Repository path
            repo_config: Repository configuration

        Returns:
            List of classes
        """
        classes = []

        for file_path in self._get_files(repo_path, repo_config):
            if file_path.suffix == ".py":
                try:
                    with open(file_path) as f:
                        tree = ast.parse(f.read())

                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            classes.append({
                                "type": "class",
                                "name": node.name,
                                "file": str(file_path.relative_to(repo_path)),
                                "methods": [
                                    m.name for m in node.body if isinstance(m, ast.FunctionDef)
                                ],
                            })
                except Exception as e:
                    self.console.print(f"[yellow]Error parsing {file_path}: {e}[/yellow]")

        return classes

    def _extract_functions(self, repo_path: Path, repo_config: dict) -> list[dict]:
        """Extract function definitions.

        Args:
            repo_path: Repository path
            repo_config: Repository configuration

        Returns:
            List of functions
        """
        functions = []

        for file_path in self._get_files(repo_path, repo_config):
            if file_path.suffix == ".py":
                try:
                    with open(file_path) as f:
                        tree = ast.parse(f.read())

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            # Only include module-level functions
                            if isinstance(node, ast.FunctionDef):
                                functions.append({
                                    "type": "function",
                                    "name": node.name,
                                    "file": str(file_path.relative_to(repo_path)),
                                })
                except Exception as e:
                    self.console.print(f"[yellow]Error parsing {file_path}: {e}[/yellow]")

        return functions
