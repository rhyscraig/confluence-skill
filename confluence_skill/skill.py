"""Main Confluence documentation skill."""

import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from .code_scanner import CodeScanner
from .confluence_client import ConfluenceClient, InputValidator
from .doc_generators import create_generator, DocumentTemplate
from .guardrails import GuardailValidator, ApprovalGate
from .jira_integration import JiraIntegration
from .models import (
    SkillConfig,
    LocalConfig,
    DocumentMetadata,
    DocumentChange,
    DocumentGenerationResult,
    ValidationError,
)

# Configure logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class ConfluenceSkill:
    """Center-of-excellence Confluence documentation skill."""

    def __init__(self, config: SkillConfig):
        """Initialize skill with configuration.

        Args:
            config: Skill configuration

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate required configuration
        config_errors = config.validate_required_fields()
        if config_errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in config_errors))

        self.config = config
        self.console = Console()
        self.client = ConfluenceClient(config.confluence)
        self.scanner = CodeScanner(config.code_analysis)
        self.validator = GuardailValidator(config.guardrails)
        self.approval_gate = ApprovalGate(
            require_approval=config.guardrails.require_approval,
            interactive=False,  # Can be set to True for interactive mode
        )
        self._operation_log: list[DocumentChange] = []

    def document(
        self,
        task: str,
        repos: Optional[list[str]] = None,
        doc_type: Optional[str] = None,
        space_key: Optional[str] = None,
        parent_page_title: Optional[str] = None,
        repo_path: Optional[str] = None,
        dry_run: Optional[bool] = None,
        interactive: bool = False,
    ) -> DocumentGenerationResult:
        """Generate documentation from task description and code.

        Args:
            task: Task description for documentation
            repos: List of repos to analyze (overrides config)
            doc_type: Document template type
            space_key: Target space key (overrides config)
            parent_page_title: Parent page title
            repo_path: Path to repository (loads .confluence.yaml for local config)
            dry_run: Run in dry-run mode (overrides config default)
            interactive: Interactive mode for approvals

        Returns:
            DocumentGenerationResult with outcome
        """
        start_time = time.time()
        result = DocumentGenerationResult(
            success=False,
            dry_run=dry_run if dry_run is not None else self.config.guardrails.dry_run_by_default,
        )

        self.approval_gate.interactive = interactive
        working_config = self.config

        try:
            self.console.print(f"\n[bold blue]Confluence Documentation Skill[/bold blue]")
            self.console.print(f"Task: {task}\n")

            # 0. Load and merge local config if provided
            if repo_path:
                self.console.print("[cyan]0. Loading local configuration...[/cyan]")
                working_config = self._load_and_merge_config(repo_path)
                if working_config != self.config:
                    self.console.print("[green]   ✅ Merged local .confluence.yaml[/green]")

            # 1. Prepare configuration
            self.console.print("[cyan]1. Preparing configuration...[/cyan]")
            doc_config = self._prepare_config(doc_type, space_key, parent_page_title, repos, working_config)

            # 2. Scan code repositories
            self.console.print("[cyan]2. Analyzing code repositories...[/cyan]")
            extracted_info = self.scanner.scan_repos()
            self.console.print(f"   Found {len(extracted_info.get('apis', []))} APIs")
            self.console.print(f"   Found {len(extracted_info.get('dependencies', []))} dependencies")

            # 3. Generate metadata
            self.console.print("[cyan]3. Generating document metadata...[/cyan]")
            metadata = self._generate_metadata(task, doc_config)
            result.title = metadata.title

            # 4. Check for existing documents
            self.console.print("[cyan]4. Checking for existing documentation...[/cyan]")
            existing_page = self.client.find_page_by_title(doc_config.space_key, metadata.title)

            if existing_page:
                self.console.print(f"   Found existing page: {existing_page.get('id')}")
                result.document_id = existing_page.get("id")

                # Handle merge strategy
                merge_strategy = self._handle_existing_page(existing_page, metadata, doc_config)
                if merge_strategy == "skip":
                    result.success = True
                    result.errors.append(
                        ValidationError(
                            level="info",
                            field="merge",
                            message="Document exists and merge strategy is 'skip'",
                        )
                    )
                    return result

            # 5. Validate space exists and has permissions
            self.console.print("[cyan]5. Validating space and permissions...[/cyan]")
            if not self.client.validate_space(doc_config.space_key):
                result.errors.append(
                    ValidationError(
                        level="error",
                        field="space",
                        message=f"Space '{doc_config.space_key}' does not exist or is not accessible",
                    )
                )
                return result

            if not self.client.check_write_permission(doc_config.space_key):
                result.errors.append(
                    ValidationError(
                        level="error",
                        field="permissions",
                        message=f"No write permission for space '{doc_config.space_key}'",
                    )
                )
                return result

            # 5b. Initialize Jira integration if enabled
            jira_integration = None
            if working_config.jira.enabled:
                self.console.print("[cyan]5b. Initializing Jira integration...[/cyan]")
                jira_integration = JiraIntegration(working_config.jira)
                if not jira_integration.client.enabled:
                    self.console.print("[yellow]   ⚠️  Jira integration disabled (check credentials)[/yellow]")

            # 6. Generate document content
            self.console.print("[cyan]6. Generating document content...[/cyan]")
            generator = create_generator(doc_config.template, metadata, extracted_info)
            content = generator.generate()

            # 7. Validate content
            self.console.print("[cyan]7. Validating document...[/cyan]")
            self.validator.validate_metadata(metadata)
            self.validator.validate_content(content, metadata)

            if self.validator.errors:
                for error in self.validator.errors:
                    result.errors.append(error)
                self.console.print(f"[red]{self.validator.get_summary()}[/red]")

            if self.validator.warnings:
                for warning in self.validator.warnings:
                    result.warnings.append(warning)
                self.console.print(f"[yellow]{self.validator.get_summary()}[/yellow]")

            # Preview content
            result.content_preview = content[:500] + "..." if len(content) > 500 else content

            # 8. Request approval if needed
            if self.approval_gate.require_approval and not result.dry_run:
                approved = self.approval_gate.request_approval(
                    metadata.title,
                    "CREATE" if not existing_page else "UPDATE",
                    f"Document: {metadata.title}",
                )
                if not approved:
                    result.errors.append(
                        ValidationError(
                            level="warning",
                            field="approval",
                            message="User declined to approve changes",
                        )
                    )
                    return result

            # 9. Write or preview
            if result.dry_run:
                self.console.print("[yellow]DRY RUN MODE - No changes written[/yellow]")
                result.success = len(result.errors) == 0
            else:
                self.console.print("[cyan]8. Writing to Confluence...[/cyan]")

                if existing_page:
                    page = self.client.update_page(
                        existing_page["id"],
                        metadata.title,
                        content,
                        labels=metadata.labels,
                    )
                    result.document_id = page["id"]
                    result.document_url = f"{self.config.confluence.instance_url}/wiki/spaces/{doc_config.space_key}/pages/{page['id']}"
                    self.console.print(f"[green]✅ Updated page: {page['id']}[/green]")

                    # Add audit comment
                    if self.config.output.create_audit_trail:
                        comment = f"Updated by Confluence Skill on {datetime.utcnow().isoformat()}"
                        self.client.add_page_comment(page["id"], f"<p>{comment}</p>")
                else:
                    page = self.client.create_page(
                        doc_config.space_key,
                        metadata.title,
                        content,
                        parent_page_id=self._get_parent_page_id(doc_config),
                        labels=metadata.labels,
                    )
                    result.document_id = page["id"]
                    result.document_url = f"{self.config.confluence.instance_url}/wiki/spaces/{doc_config.space_key}/pages/{page['id']}"
                    self.console.print(f"[green]✅ Created page: {page['id']}[/green]")

                result.success = True

                # 10. Integrate with Jira if enabled
                if jira_integration and jira_integration.config.enabled:
                    self.console.print("[cyan]9. Integrating with Jira...[/cyan]")
                    project = jira_integration.config.default_project
                    if project:
                        # Link related issues
                        issues = jira_integration.link_related_issues(
                            result.document_id,
                            project,
                            metadata.title,
                            self.client,
                        )

                        # Create tasks for undocumented APIs
                        if jira_integration.config.create_tasks_for_gaps:
                            apis = extracted_info.get("apis", [])
                            if apis:
                                created = jira_integration.create_tasks_for_gaps(
                                    project,
                                    apis,
                                    epic_key=jira_integration.client.find_epic_for_service(project, metadata.title) if jira_integration.config.epic_link_pattern else None,
                                )
                                if created:
                                    self.console.print(
                                        f"[green]✅ Created {len(created)} tasks for undocumented APIs[/green]"
                                    )

        except Exception as e:
            self.console.print(f"[red]❌ Error: {str(e)}[/red]")
            result.errors.append(
                ValidationError(
                    level="error",
                    field="exception",
                    message=str(e),
                )
            )
            result.success = False

        finally:
            result.duration_seconds = time.time() - start_time
            self._print_result_summary(result)

        return result

    def _load_and_merge_config(self, repo_path: str) -> SkillConfig:
        """Load and merge local config from repository.

        Args:
            repo_path: Path to repository

        Returns:
            Merged configuration
        """
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.is_absolute():
            repo_path_obj = Path("/Users/craighoad/Repos") / repo_path_obj

        local_config_path = repo_path_obj / ".confluence.yaml"

        if not local_config_path.exists():
            logger.debug(f"No .confluence.yaml found in {repo_path}")
            return self.config

        try:
            local_config = LocalConfig.from_yaml(local_config_path)
            merged = self.config.merge(local_config)
            logger.info(f"Merged config from {local_config_path}")
            return merged
        except Exception as e:
            self.console.print(f"[yellow]Warning: Failed to load local config: {e}[/yellow]")
            logger.warning(f"Failed to load local config from {local_config_path}: {e}")
            return self.config

    def _prepare_config(self, doc_type, space_key, parent_page_title, repos, working_config=None):
        """Prepare documentation configuration.

        Args:
            doc_type: Document type override
            space_key: Space key override
            parent_page_title: Parent page title override
            repos: Repos override
            working_config: Configuration to use (defaults to self.config)

        Returns:
            Prepared configuration object

        Raises:
            ValueError: If configuration is invalid
        """
        if working_config is None:
            working_config = self.config

        config = working_config.documentation

        # Override template
        if doc_type:
            try:
                config.template = DocumentTemplate(doc_type)
            except ValueError:
                self.console.print(f"[yellow]Unknown doc type: {doc_type}[/yellow]")

        # Override space and repos
        if space_key:
            config.space_key = space_key
        if not config.space_key:
            config.space_key = working_config.confluence.space_key

        # Validate space_key
        valid, error = InputValidator.validate_space_key(config.space_key)
        if not valid:
            raise ValueError(f"Invalid space key '{config.space_key}': {error}")

        if parent_page_title:
            config.parent_page = parent_page_title

        if repos:
            working_config.code_analysis.repos = [{"path": r} for r in repos]

        return config

    def _generate_metadata(self, task: str, doc_config) -> DocumentMetadata:
        """Generate document metadata.

        Args:
            task: Task description
            doc_config: Documentation configuration

        Returns:
            DocumentMetadata

        Raises:
            ValueError: If title or labels are invalid
        """
        # Auto-generate title from task if needed
        title = task if doc_config.auto_title else doc_config.parent_page

        # Validate title
        valid, error = InputValidator.validate_page_title(title)
        if not valid:
            raise ValueError(f"Invalid document title: {error}")

        # Validate labels
        labels = doc_config.metadata.labels or []
        if labels:
            valid, error = InputValidator.validate_labels(labels)
            if not valid:
                raise ValueError(f"Invalid document labels: {error}")

        metadata = DocumentMetadata(
            title=title,
            space_key=doc_config.space_key,
            version=doc_config.metadata.version or "1.0",
            owner=doc_config.metadata.owner,
            audience=doc_config.metadata.audience,
            status=doc_config.metadata.status.value if hasattr(doc_config.metadata.status, "value") else doc_config.metadata.status,
            labels=labels,
            created_at=datetime.utcnow(),
        )

        return metadata

    def _handle_existing_page(self, existing_page: dict, metadata: DocumentMetadata, doc_config) -> Optional[str]:
        """Handle strategy for existing pages.

        Args:
            existing_page: Existing page data
            metadata: New metadata
            doc_config: Documentation configuration

        Returns:
            Merge strategy (append, replace, skip) or None
        """
        strategy = doc_config.merge_strategy.value if hasattr(doc_config.merge_strategy, "value") else doc_config.merge_strategy

        if strategy == "interactive":
            # Ask user
            result = self.approval_gate.request_merge_strategy(metadata.title)
            return result if result else "skip"

        self.console.print(f"   Using merge strategy: {strategy}")
        return strategy

    def _get_parent_page_id(self, doc_config) -> Optional[str]:
        """Get parent page ID.

        Args:
            doc_config: Documentation configuration

        Returns:
            Parent page ID or None
        """
        if doc_config.parent_page_id:
            return doc_config.parent_page_id

        if doc_config.parent_page:
            parent = self.client.find_page_by_title(doc_config.space_key, doc_config.parent_page)
            if parent:
                return parent.get("id")
            self.console.print(f"[yellow]Parent page not found: {doc_config.parent_page}[/yellow]")

        return None

    def list_page_hierarchy(self, page_id: str, include_content: bool = False) -> dict:
        """Get page with all child pages in hierarchy.

        Args:
            page_id: Page ID to get hierarchy for
            include_content: Include page content in result

        Returns:
            Page object with 'children' array
        """
        page = self.client.get_page(page_id, include_body=include_content)
        children = self.client.list_child_pages(page_id)
        page["children"] = children
        return page

    def archive_page(self, page_id: str) -> bool:
        """Archive a page (safe alternative to deletion).

        Args:
            page_id: Page ID to archive

        Returns:
            True if archived successfully
        """
        return self.client.archive_page(page_id)

    def search_pages(self, space_key: str, query: str = "", limit: int = 50) -> list[dict]:
        """Search for pages in a space.

        Args:
            space_key: Space key
            query: Search query (title or content)
            limit: Max results

        Returns:
            List of matching pages
        """
        return self.client.search_pages(space_key, query, limit)

    def bulk_label_pages(self, space_key: str, query: str, labels: list[str]) -> dict:
        """Search and label multiple pages at once.

        Args:
            space_key: Space key
            query: Search query to find pages
            labels: Labels to add to all matching pages

        Returns:
            Results with success/failure counts
        """
        pages = self.search_pages(space_key, query)
        page_ids = [p.get("id") for p in pages if p.get("id")]
        if not page_ids:
            return {"success": 0, "failed": 0, "errors": []}
        return self.client.bulk_add_labels(page_ids, labels)

    def _print_result_summary(self, result: DocumentGenerationResult) -> None:
        """Print result summary to console.

        Args:
            result: DocumentGenerationResult
        """
        summary = result.summary()
        color = "green" if result.success else "red"
        self.console.print(f"\n[{color}]{summary}[/{color}]")

        if result.content_preview:
            self.console.print("\n[bold]Content Preview:[/bold]")
            panel = Panel(result.content_preview[:300], expand=False)
            self.console.print(panel)
