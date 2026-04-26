"""Confluence Cloud API wrapper with safety features and rate limiting."""

import hashlib
import os
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from rich.console import Console

from .models import ConfluenceConfig


class RateLimiter:
    """Simple token-bucket rate limiter."""

    def __init__(self, rate_per_minute: int):
        """Initialize rate limiter.

        Args:
            rate_per_minute: Number of operations allowed per minute
        """
        self.rate_per_minute = rate_per_minute
        self.min_interval = 60.0 / rate_per_minute
        self.last_request = 0.0

    def wait(self) -> None:
        """Wait if necessary to maintain rate limit."""
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()


class ConfluenceClient:
    """Confluence Cloud API client with rate limiting and safety features."""

    def __init__(self, config: ConfluenceConfig):
        """Initialize Confluence client.

        Args:
            config: Confluence configuration
        """
        self.config = config
        self.console = Console()
        self.rate_limiter = RateLimiter(config.rate_limit_per_minute)

        # Get auth token
        token = os.getenv(config.auth_token_env)
        if not token:
            raise ValueError(f"Set {config.auth_token_env} environment variable")

        self.auth_token = token
        self.session = self._create_session()
        self._page_cache: dict[str, dict] = {}
        self._permission_cache: dict[str, bool] = {}

    def _create_session(self) -> requests.Session:
        """Create session with retries and timeouts."""
        session = requests.Session()

        # Add retry strategy for transient failures
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "POST", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Set auth headers
        session.headers.update({
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ConfluenceSkill/1.0",
        })

        return session

    def _api_url(self, path: str) -> str:
        """Build API URL."""
        base = urljoin(self.config.instance_url, "/wiki/api/v2/")
        return urljoin(base, path.lstrip("/"))

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Make API request with rate limiting and error handling.

        Args:
            method: HTTP method
            path: API path
            data: Request body
            params: Query parameters

        Returns:
            Response JSON

        Raises:
            requests.HTTPError: On API error
        """
        self.rate_limiter.wait()

        url = self._api_url(path)
        try:
            response = self.session.request(
                method,
                url,
                json=data,
                params=params,
                timeout=self.config.api_timeout_seconds,
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.HTTPError as e:
            self.console.print(f"[red]API Error: {e.response.status_code} {e.response.reason}[/red]")
            if e.response.text:
                self.console.print(f"[red]{e.response.text}[/red]")
            raise

    def get_space(self, space_key: str) -> dict:
        """Get space by key.

        Args:
            space_key: Space key

        Returns:
            Space details
        """
        return self._request("GET", f"spaces/{space_key}")

    def find_page_by_title(self, space_key: str, title: str) -> Optional[dict]:
        """Find page by title in space.

        Args:
            space_key: Space key
            title: Page title

        Returns:
            Page details or None
        """
        # Check cache first
        cache_key = f"{space_key}:{title}"
        if cache_key in self._page_cache:
            return self._page_cache[cache_key]

        response = self._request(
            "GET",
            "pages",
            params={
                "space-key": space_key,
                "title": title,
                "limit": 1,
            },
        )

        if response.get("results"):
            page = response["results"][0]
            self._page_cache[cache_key] = page
            return page

        return None

    def search_pages(self, space_key: str, query: str = "", limit: int = 50) -> list[dict]:
        """Search pages by title or content.

        Args:
            space_key: Space key
            query: Search query
            limit: Max results

        Returns:
            List of matching pages
        """
        try:
            params = {"space-key": space_key, "limit": limit}
            if query:
                params["title-query"] = query

            response = self._request("GET", "pages", params=params)
            return response.get("results", [])
        except requests.HTTPError:
            return []

    def get_page(self, page_id: str, include_body: bool = False) -> dict:
        """Get page by ID.

        Args:
            page_id: Page ID
            include_body: Include page body content

        Returns:
            Page details
        """
        body_format = "storage" if include_body else None
        params = {}
        if body_format:
            params["body-format"] = body_format

        return self._request("GET", f"pages/{page_id}", params=params)

    def get_page_content(self, page_id: str) -> str:
        """Get page body content.

        Args:
            page_id: Page ID

        Returns:
            Page content (storage format)
        """
        page = self.get_page(page_id, include_body=True)
        return page.get("body", {}).get("storage", {}).get("value", "")

    def create_page(
        self,
        space_key: str,
        title: str,
        body: str,
        parent_page_id: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> dict:
        """Create new page.

        Args:
            space_key: Space key
            title: Page title
            body: Page body (storage format)
            parent_page_id: Parent page ID
            labels: Page labels

        Returns:
            Created page details

        Raises:
            ValueError: If validation fails
        """
        # Validate inputs
        valid, error = InputValidator.validate_space_key(space_key)
        if not valid:
            raise ValueError(f"Invalid space key: {error}")

        valid, error = InputValidator.validate_page_title(title)
        if not valid:
            raise ValueError(f"Invalid page title: {error}")

        valid, error = InputValidator.validate_content_size(body)
        if not valid:
            raise ValueError(f"Content too large: {error}")

        if labels:
            valid, error = InputValidator.validate_labels(labels)
            if not valid:
                raise ValueError(f"Invalid labels: {error}")

        data = {
            "spaceId": self.get_space(space_key)["id"],
            "type": "page",
            "title": title,
            "body": {
                "representation": "storage",
                "value": body,
            },
        }

        if parent_page_id:
            data["parentId"] = parent_page_id

        page = self._request("POST", "pages", data=data)

        # Add labels if provided
        if labels:
            self._add_labels(page["id"], labels)

        # Invalidate cache
        self._page_cache.clear()

        return page

    def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
        labels: Optional[list[str]] = None,
    ) -> dict:
        """Update existing page.

        Args:
            page_id: Page ID
            title: New title
            body: New body (storage format)
            labels: Page labels

        Returns:
            Updated page details

        Raises:
            ValueError: If validation fails
        """
        # Validate inputs
        valid, error = InputValidator.validate_page_title(title)
        if not valid:
            raise ValueError(f"Invalid page title: {error}")

        valid, error = InputValidator.validate_content_size(body)
        if not valid:
            raise ValueError(f"Content too large: {error}")

        if labels:
            valid, error = InputValidator.validate_labels(labels)
            if not valid:
                raise ValueError(f"Invalid labels: {error}")

        page = self.get_page(page_id)
        version = page.get("version", {}).get("number", 0)

        data = {
            "type": "page",
            "title": title,
            "body": {
                "representation": "storage",
                "value": body,
            },
            "version": {
                "number": version + 1,
            },
        }

        updated_page = self._request("PUT", f"pages/{page_id}", data=data)

        # Update labels
        if labels:
            self._add_labels(page_id, labels)

        # Invalidate cache
        self._page_cache.clear()

        return updated_page

    def delete_page(self, page_id: str) -> bool:
        """Delete a page.

        Args:
            page_id: Page ID

        Returns:
            True if deleted successfully
        """
        self._request("DELETE", f"pages/{page_id}")
        self._page_cache.clear()
        return True

    def add_page_comment(self, page_id: str, comment: str) -> dict:
        """Add comment to page.

        Args:
            page_id: Page ID
            comment: Comment text (storage format)

        Returns:
            Comment details
        """
        data = {
            "body": {
                "representation": "storage",
                "value": comment,
            },
        }
        return self._request("POST", f"pages/{page_id}/comments", data=data)

    def check_write_permission(self, space_key: str) -> bool:
        """Check if user can write to space.

        Args:
            space_key: Space key

        Returns:
            True if user has write permission
        """
        # Check cache
        if space_key in self._permission_cache:
            return self._permission_cache[space_key]

        try:
            # Try to get space - if successful, user likely has access
            self.get_space(space_key)
            self._permission_cache[space_key] = True
            return True
        except requests.HTTPError as e:
            if e.response.status_code == 403:
                self._permission_cache[space_key] = False
                return False
            raise

    def _add_labels(self, page_id: str, labels: list[str]) -> None:
        """Add labels to a page.

        Args:
            page_id: Page ID
            labels: Labels to add

        Raises:
            ValueError: If labels are invalid
        """
        if not labels:
            return

        valid, error = InputValidator.validate_labels(labels)
        if not valid:
            raise ValueError(f"Invalid labels: {error}")

        for label in labels:
            data = {"name": label}
            try:
                self._request("POST", f"pages/{page_id}/labels", data=data)
            except requests.HTTPError as e:
                self.console.print(f"[yellow]Warning: Could not add label '{label}': {e}[/yellow]")

    def bulk_add_labels(self, page_ids: list[str], labels: list[str]) -> dict:
        """Add labels to multiple pages.

        Args:
            page_ids: List of page IDs
            labels: Labels to add to all pages

        Returns:
            Results with success/failure counts

        Raises:
            ValueError: If labels are invalid
        """
        valid, error = InputValidator.validate_labels(labels)
        if not valid:
            raise ValueError(f"Invalid labels: {error}")

        results = {"success": 0, "failed": 0, "errors": []}

        for page_id in page_ids:
            for label in labels:
                try:
                    self._add_labels(page_id, [label])
                    results["success"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({"page_id": page_id, "label": label, "error": str(e)})

        return results

    def set_page_properties(self, page_id: str, properties: dict) -> bool:
        """Set custom properties on a page.

        Args:
            page_id: Page ID
            properties: Key-value pairs to set

        Returns:
            True if successful
        """
        try:
            data = {"key": "page-properties", "value": properties}
            self._request("PUT", f"pages/{page_id}/properties", data=data)
            return True
        except requests.HTTPError as e:
            self.console.print(f"[yellow]Warning: Could not set page properties: {e}[/yellow]")
            return False

    def get_page_hash(self, page_id: str) -> str:
        """Get content hash of page for change detection.

        Args:
            page_id: Page ID

        Returns:
            MD5 hash of page content
        """
        content = self.get_page_content(page_id)
        return hashlib.md5(content.encode()).hexdigest()

    def validate_space(self, space_key: str) -> bool:
        """Validate that space exists and is accessible.

        Args:
            space_key: Space key

        Returns:
            True if space exists and is accessible
        """
        try:
            self.get_space(space_key)
            return True
        except requests.HTTPError as e:
            if e.response.status_code in (403, 404):
                return False
            raise

    def list_child_pages(self, parent_page_id: str) -> list[dict]:
        """List all child pages of a parent page.

        Args:
            parent_page_id: Parent page ID

        Returns:
            List of child page objects
        """
        try:
            response = self._request(
                "GET",
                f"pages/{parent_page_id}/children",
                params={"limit": 250},
            )
            pages = []
            if isinstance(response, dict):
                pages = response.get("results", [])
            elif isinstance(response, list):
                pages = response
            return pages
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return []
            raise

    def archive_page(self, page_id: str) -> bool:
        """Archive a page instead of permanently deleting it.

        Args:
            page_id: Page ID

        Returns:
            True if archived successfully
        """
        data = {"status": "archived"}
        try:
            self._request("PUT", f"pages/{page_id}", data=data)
            self._page_cache.clear()
            return True
        except requests.HTTPError as e:
            self.console.print(f"[yellow]Warning: Could not archive page: {e}[/yellow]")
            return False

    def is_page_accessible(self, page_id: str) -> bool:
        """Check if page is accessible.

        Args:
            page_id: Page ID

        Returns:
            True if page is accessible
        """
        try:
            self.get_page(page_id)
            return True
        except requests.HTTPError as e:
            if e.response.status_code in (403, 404):
                return False
            raise


class InputValidator:
    """Validates user input for Confluence operations."""

    @staticmethod
    def validate_space_key(space_key: str) -> tuple[bool, str]:
        """Validate Confluence space key format.

        Args:
            space_key: Space key to validate

        Returns:
            (is_valid, error_message)
        """
        if not space_key:
            return False, "Space key cannot be empty"
        if len(space_key) > 255:
            return False, "Space key cannot exceed 255 characters"
        if not space_key.replace("-", "").replace("_", "").isalnum():
            return False, "Space key can only contain alphanumerics, hyphens, and underscores"
        return True, ""

    @staticmethod
    def validate_page_title(title: str) -> tuple[bool, str]:
        """Validate page title.

        Args:
            title: Page title to validate

        Returns:
            (is_valid, error_message)
        """
        if not title or not title.strip():
            return False, "Page title cannot be empty"
        if len(title) > 255:
            return False, f"Page title cannot exceed 255 characters (got {len(title)})"
        if len(title) < 3:
            return False, "Page title must be at least 3 characters"
        return True, ""

    @staticmethod
    def validate_labels(labels: list[str]) -> tuple[bool, str]:
        """Validate label list.

        Args:
            labels: Labels to validate

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(labels, list):
            return False, "Labels must be a list"
        if len(labels) > 50:
            return False, f"Cannot add more than 50 labels (got {len(labels)})"

        for label in labels:
            if not label or not label.strip():
                return False, "Label cannot be empty"
            if len(label) > 100:
                return False, f"Label cannot exceed 100 characters: '{label}'"

        return True, ""

    @staticmethod
    def sanitize_content_for_html(content: str) -> str:
        """Escape HTML special characters in content.

        Args:
            content: Content to sanitize

        Returns:
            Sanitized content
        """
        import html
        return html.escape(content)

    @staticmethod
    def validate_content_size(content: str, max_kb: int = 2000) -> tuple[bool, str]:
        """Validate content size.

        Args:
            content: Content to validate
            max_kb: Maximum size in KB

        Returns:
            (is_valid, error_message)
        """
        size_kb = len(content.encode("utf-8")) / 1024
        if size_kb > max_kb:
            return False, f"Content exceeds maximum size of {max_kb}KB (got {size_kb:.1f}KB)"
        return True, ""
