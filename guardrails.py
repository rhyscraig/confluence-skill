"""Safety guardrails and validation for Confluence skill."""

import re
from typing import Optional
from urllib.parse import urlparse

from rich.console import Console

from .models import GuardrailsConfig, ValidationError, DocumentMetadata


class GuardailValidator:
    """Validates documents against safety guardrails."""

    def __init__(self, config: GuardrailsConfig):
        """Initialize validator.

        Args:
            config: Guardrails configuration
        """
        self.config = config
        self.console = Console()
        self.errors: list[ValidationError] = []
        self.warnings: list[ValidationError] = []

    def reset(self) -> None:
        """Clear validation errors and warnings."""
        self.errors = []
        self.warnings = []

    def validate_metadata(self, metadata: DocumentMetadata) -> bool:
        """Validate document metadata.

        Args:
            metadata: Document metadata

        Returns:
            True if metadata is valid
        """
        self.reset()

        if not self.config.enabled:
            return True

        if not self.config.validate_metadata:
            return True

        # Check required fields
        for field in self.config.required_metadata_fields:
            value = getattr(metadata, field, None)
            if not value:
                error = ValidationError(
                    level="error",
                    field=field,
                    message=f"Required field '{field}' is missing",
                    suggestion=f"Ensure {field} is set in metadata",
                )
                self.errors.append(error)

        # Check for deprecated terms
        if self.config.deprecated_terms:
            title_lower = metadata.title.lower()
            for term in self.config.deprecated_terms:
                if term.lower() in title_lower:
                    warning = ValidationError(
                        level="warning",
                        field="title",
                        message=f"Title contains deprecated term: '{term}'",
                        suggestion="Consider updating the title to reflect current terminology",
                    )
                    self.warnings.append(warning)

        return len(self.errors) == 0

    def validate_content(self, content: str, metadata: DocumentMetadata) -> bool:
        """Validate document content.

        Args:
            content: Document content (HTML/storage format)
            metadata: Document metadata

        Returns:
            True if content is valid
        """
        self.reset()

        if not self.config.enabled:
            return True

        # Check content length
        content_kb = len(content.encode()) / 1024
        if content_kb > self.config.max_document_size_kb:
            warning = ValidationError(
                level="warning",
                field="content",
                message=f"Document size is {content_kb:.1f}KB (limit: {self.config.max_document_size_kb}KB)",
                suggestion="Consider splitting into multiple pages or removing large sections",
            )
            self.warnings.append(warning)

        # Validate links if enabled
        if self.config.validate_links:
            self._validate_links(content)

        # Check for deprecated terms in content
        if self.config.deprecated_terms:
            for term in self.config.deprecated_terms:
                if term.lower() in content.lower():
                    warning = ValidationError(
                        level="warning",
                        field="content",
                        message=f"Content contains deprecated term: '{term}'",
                        suggestion="Consider updating content to reflect current terminology",
                    )
                    self.warnings.append(warning)

        return len(self.errors) == 0

    def _validate_links(self, content: str) -> None:
        """Validate links in content.

        Args:
            content: Document content
        """
        # Extract links from HTML/storage format
        link_pattern = r'href="([^"]+)"'
        links = re.findall(link_pattern, content)

        for link in links:
            # Check for broken internal references
            if link.startswith("#"):
                # Anchor link - check if anchor exists
                anchor = link[1:]
                if not self._anchor_exists(content, anchor):
                    error = ValidationError(
                        level="error",
                        field="links",
                        message=f"Anchor link not found: {link}",
                        suggestion=f"Ensure anchor #{anchor} exists or update the link",
                    )
                    self.errors.append(error)

            # Check for obviously broken links
            elif link.startswith("/"):
                if not self._is_valid_path(link):
                    error = ValidationError(
                        level="warning",
                        field="links",
                        message=f"Relative link may be broken: {link}",
                        suggestion="Use absolute Confluence URLs or internal page links",
                    )
                    self.warnings.append(error)

    def _anchor_exists(self, content: str, anchor: str) -> bool:
        """Check if anchor exists in content.

        Args:
            content: Document content
            anchor: Anchor name

        Returns:
            True if anchor exists
        """
        # Look for id="anchor" or <a id="anchor">
        pattern = f'id="{re.escape(anchor)}"'
        return bool(re.search(pattern, content))

    def _is_valid_path(self, path: str) -> bool:
        """Check if path looks valid.

        Args:
            path: URL path

        Returns:
            True if path looks valid
        """
        # This is a simple heuristic - just check it's not obviously wrong
        if path.count("/") < 2:
            return False
        if ".." in path:
            return False
        return True

    def get_summary(self) -> str:
        """Get validation summary.

        Returns:
            Summary of errors and warnings
        """
        if not self.errors and not self.warnings:
            return "✅ All validations passed"

        lines = []
        if self.errors:
            lines.append(f"❌ Errors ({len(self.errors)}):")
            for error in self.errors[:5]:
                lines.append(f"  - {error.field}: {error.message}")
                if error.suggestion:
                    lines.append(f"    💡 {error.suggestion}")

        if self.warnings:
            lines.append(f"⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings[:5]:
                lines.append(f"  - {warning.field}: {warning.message}")
                if warning.suggestion:
                    lines.append(f"    💡 {warning.suggestion}")

        return "\n".join(lines)


class ApprovalGate:
    """Manages user approval for document changes."""

    def __init__(self, require_approval: bool = True, interactive: bool = False):
        """Initialize approval gate.

        Args:
            require_approval: Whether approval is required
            interactive: Whether to prompt user
        """
        self.require_approval = require_approval
        self.interactive = interactive
        self.console = Console()
        self._approved: set[str] = set()

    def request_approval(
        self,
        document_id: str,
        action: str,
        summary: str,
    ) -> bool:
        """Request approval for an action.

        Args:
            document_id: Document identifier
            action: Action being performed (create, update, merge)
            summary: Human-readable summary

        Returns:
            True if action is approved
        """
        if not self.require_approval:
            return True

        if document_id in self._approved:
            return True

        if not self.interactive:
            self.console.print(f"[yellow]Skipping approval (not interactive): {action} {document_id}[/yellow]")
            return False

        self.console.print(f"\n[bold]{action.upper()}: {summary}[/bold]")
        response = self.console.input("Continue? [y/N]: ").lower().strip()

        if response == "y":
            self._approved.add(document_id)
            return True

        return False

    def request_merge_strategy(self, document_title: str) -> Optional[str]:
        """Ask user how to handle existing document.

        Args:
            document_title: Title of existing document

        Returns:
            Merge strategy (append, replace, skip) or None
        """
        if not self.interactive:
            return None

        self.console.print(f"\nDocument '{document_title}' already exists.")
        self.console.print("How would you like to proceed?")
        self.console.print("  1. append  - Add new content after existing")
        self.console.print("  2. replace - Replace entire document")
        self.console.print("  3. skip    - Don't update")

        choice = self.console.input("Choice [1-3]: ").strip()
        mapping = {"1": "append", "2": "replace", "3": "skip"}
        return mapping.get(choice)
