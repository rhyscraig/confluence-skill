"""Jira integration for cross-linking issues and tracking implementation status."""

import os
import re
from typing import Optional
from urllib.parse import urljoin

import requests
from rich.console import Console

from .models import JiraConfig, DocumentMetadata


class JiraClient:
    """Jira Cloud API client."""

    def __init__(self, config: JiraConfig):
        """Initialize Jira client.

        Args:
            config: Jira configuration
        """
        if not config.enabled or not config.instance_url:
            self.enabled = False
            return

        self.enabled = True
        self.config = config
        self.console = Console()

        # Get auth token
        token = os.getenv(config.auth_token_env)
        if not token:
            self.console.print(
                f"[yellow]Warning: {config.auth_token_env} not set, Jira integration disabled[/yellow]"
            )
            self.enabled = False
            return

        self.auth_token = token
        self.base_url = config.instance_url.rstrip("/")
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create authenticated session."""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        return session

    def _api_url(self, path: str) -> str:
        """Build API URL."""
        return urljoin(self.base_url, f"/rest/api/3/{path.lstrip('/')}")

    def find_related_issues(
        self,
        project: str,
        search_text: str,
        issue_types: Optional[list[str]] = None,
    ) -> list[dict]:
        """Find Jira issues related to service.

        Args:
            project: Jira project key
            search_text: Text to search for (service name, component)
            issue_types: Filter by issue types (e.g., ["Epic", "Story"])

        Returns:
            List of issue details
        """
        if not self.enabled:
            return []

        try:
            # Build JQL query
            jql_parts = [f'project = "{project}"', f'text ~ "{search_text}"']

            if issue_types:
                types_str = ", ".join(f'"{t}"' for t in issue_types)
                jql_parts.append(f"type in ({types_str})")

            jql = " AND ".join(jql_parts)

            response = self.session.get(
                self._api_url("search"),
                params={"jql": jql, "maxResults": 50, "fields": "key,summary,status,url"},
                timeout=10,
            )
            response.raise_for_status()

            return response.json().get("issues", [])

        except requests.RequestException as e:
            self.console.print(f"[yellow]Warning: Failed to search Jira: {e}[/yellow]")
            return []

    def find_epic_for_service(self, project: str, service_name: str) -> Optional[dict]:
        """Find epic for a service.

        Args:
            project: Jira project key
            service_name: Service/component name

        Returns:
            Epic issue or None
        """
        if not self.enabled:
            return None

        try:
            issues = self.find_related_issues(
                project,
                service_name,
                issue_types=["Epic"],
            )
            return issues[0] if issues else None
        except Exception as e:
            self.console.print(f"[yellow]Warning: Failed to find epic: {e}[/yellow]")
            return None

    def create_issue(
        self,
        project: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        epic_key: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> Optional[dict]:
        """Create a Jira issue.

        Args:
            project: Jira project key
            summary: Issue summary
            description: Issue description
            issue_type: Type of issue (Task, Bug, Story, etc.)
            epic_key: Epic to link to
            labels: Labels to add

        Returns:
            Created issue details or None
        """
        if not self.enabled:
            return None

        try:
            data = {
                "fields": {
                    "project": {"key": project},
                    "summary": summary,
                    "description": description,
                    "issuetype": {"name": issue_type},
                }
            }

            if labels:
                data["fields"]["labels"] = labels

            if epic_key and self.config.custom_fields.get("epic_link"):
                epic_field = self.config.custom_fields["epic_link"]
                data["fields"][epic_field] = epic_key

            response = self.session.post(
                self._api_url("issue"),
                json=data,
                timeout=10,
            )
            response.raise_for_status()

            issue = response.json()
            self.console.print(f"[green]✅ Created Jira issue: {issue.get('key')}[/green]")
            return issue

        except requests.RequestException as e:
            self.console.print(f"[yellow]Warning: Failed to create Jira issue: {e}[/yellow]")
            return None

    def get_issue(self, issue_key: str) -> Optional[dict]:
        """Get issue details.

        Args:
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
            Issue details or None
        """
        if not self.enabled:
            return None

        try:
            response = self.session.get(
                self._api_url(f"issue/{issue_key}"),
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.console.print(f"[yellow]Warning: Failed to get issue {issue_key}: {e}[/yellow]")
            return None


class JiraIntegration:
    """High-level Jira integration for Confluence skill."""

    def __init__(self, config: JiraConfig):
        """Initialize Jira integration.

        Args:
            config: Jira configuration
        """
        self.config = config
        self.client = JiraClient(config)
        self.console = Console()

    def link_related_issues(
        self,
        page_id: str,
        project: str,
        service_name: str,
        confluence_client,
    ) -> list[dict]:
        """Find and link related Jira issues to Confluence page.

        Args:
            page_id: Confluence page ID
            project: Jira project key
            service_name: Service/component name
            confluence_client: Confluence API client

        Returns:
            List of linked issues
        """
        if not self.config.enabled or not self.config.auto_link_related:
            return []

        issues = self.client.find_related_issues(project, service_name)

        if not issues:
            return []

        # Add comment linking to issues
        if issues:
            html_parts = ["<p><strong>Related Jira Issues:</strong></p><ul>"]
            for issue in issues:
                issue_key = issue.get("key")
                summary = issue.get("fields", {}).get("summary", "")
                status = issue.get("fields", {}).get("status", {}).get("name", "Open")
                url = issue.get("self", "").replace("/rest/api/3/issue/", "/browse/")

                html_parts.append(
                    f'<li><a href="{url}">{issue_key}</a>: {summary} '
                    f'<em>({status})</em></li>'
                )

            html_parts.append("</ul>")
            confluence_client.add_page_comment(page_id, "\n".join(html_parts))
            self.console.print(f"[green]✅ Linked {len(issues)} Jira issues[/green]")

        return issues

    def find_undocumented_apis(
        self,
        project: str,
        apis: list[dict],
    ) -> list[dict]:
        """Find APIs that don't have corresponding Jira issues.

        Args:
            project: Jira project key
            apis: List of extracted API endpoints

        Returns:
            List of undocumented APIs
        """
        if not self.config.enabled:
            return []

        # Get all issues in project
        try:
            response = self.client.session.get(
                self.client._api_url("search"),
                params={
                    "jql": f'project = "{project}" AND type in (Task, Story)',
                    "maxResults": 100,
                    "fields": "summary",
                },
                timeout=10,
            )
            response.raise_for_status()
            issues = response.json().get("issues", [])
        except requests.RequestException:
            return []

        # Extract API paths from issue summaries
        documented_paths = set()
        for issue in issues:
            summary = issue.get("fields", {}).get("summary", "").lower()
            # Match patterns like "GET /api/users", "document /api/users", etc.
            paths = re.findall(r"(?:GET|POST|PUT|DELETE|PATCH)?\s*(/\S+)", summary)
            documented_paths.update(paths)

        # Find undocumented APIs
        undocumented = []
        for api in apis:
            path = api.get("path", "").lower()
            if path and path not in documented_paths:
                undocumented.append(api)

        return undocumented

    def create_tasks_for_gaps(
        self,
        project: str,
        apis: list[dict],
        epic_key: Optional[str] = None,
    ) -> list[dict]:
        """Create Jira tasks for undocumented APIs.

        Args:
            project: Jira project key
            apis: List of extracted API endpoints
            epic_key: Epic to link tasks to

        Returns:
            List of created issues
        """
        if not self.config.enabled or not self.config.create_tasks_for_gaps:
            return []

        undocumented = self.find_undocumented_apis(project, apis)

        if not undocumented:
            self.console.print("[green]✅ All APIs documented![/green]")
            return []

        created_issues = []
        self.console.print(f"[yellow]Found {len(undocumented)} undocumented APIs[/yellow]")

        for api in undocumented:
            method = api.get("method", "GET")
            path = api.get("path", "")

            issue = self.client.create_issue(
                project,
                summary=f"Document {method} {path} endpoint",
                description=f"Add documentation for {method} {path} endpoint",
                issue_type="Task",
                epic_key=epic_key,
                labels=["documentation", "api"],
            )

            if issue:
                created_issues.append(issue)

        return created_issues

    def generate_jira_section(
        self,
        project: str,
        service_name: str,
    ) -> str:
        """Generate HTML section with Jira status.

        Args:
            project: Jira project key
            service_name: Service/component name

        Returns:
            HTML string with status information
        """
        if not self.config.enabled:
            return ""

        issues = self.client.find_related_issues(project, service_name)

        if not issues:
            return ""

        html = '<h2>Implementation Status</h2>\n'
        html += '<table><tbody><tr><th>Key</th><th>Summary</th><th>Status</th></tr>\n'

        for issue in issues[:10]:  # Limit to first 10
            key = issue.get("key", "")
            summary = issue.get("fields", {}).get("summary", "")
            status = issue.get("fields", {}).get("status", {}).get("name", "Unknown")
            url = issue.get("self", "").replace("/rest/api/3/issue/", "/browse/")

            html += (
                f'<tr><td><a href="{url}">{key}</a></td>'
                f"<td>{summary}</td>"
                f"<td><em>{status}</em></td></tr>\n"
            )

        html += "</tbody></table>\n"

        if len(issues) > 10:
            html += f"<p><em>... and {len(issues) - 10} more issues</em></p>\n"

        return html
