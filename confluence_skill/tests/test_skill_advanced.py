"""Advanced integration tests for Confluence Skill."""

from unittest.mock import patch

import pytest

from confluence_skill.models import (
    SkillConfig,
    ValidationError,
)
from confluence_skill.skill import ConfluenceSkill


@pytest.fixture
def config():
    """Create test skill config."""
    return SkillConfig(
        confluence={
            "instance_url": "https://test.atlassian.net",
            "space_key": "TEST",
            "auth_token_env": "TEST_TOKEN",
        },
        documentation={
            "template": "api",
            "space_key": "TEST",
            "metadata": {
                "owner": "test-team",
                "audience": ["engineers"],
            },
        },
    )


@pytest.fixture
def skill(config, monkeypatch):
    """Create ConfluenceSkill."""
    monkeypatch.setenv("TEST_TOKEN", "test-token")
    return ConfluenceSkill(config)


class TestDocumentGenerationComplete:
    """Test complete document generation workflow."""

    def test_document_full_success_flow(self, skill):
        """Test complete successful document generation flow."""
        with patch.object(skill, "client") as mock_client:
            with patch.object(skill, "scanner") as mock_scanner:
                with patch.object(skill, "validator") as mock_validator:
                    mock_scanner.scan_repos.return_value = {
                        "apis": [{"name": "GET /users", "description": "List users"}],
                        "dependencies": ["requests", "flask"],
                    }
                    mock_client.validate_space.return_value = True
                    mock_client.check_write_permission.return_value = True
                    mock_client.find_page_by_title.return_value = None
                    mock_client.create_page.return_value = {
                        "id": "new-page",
                        "title": "API Docs",
                        "version": {"number": 1},
                    }
                    mock_validator.validate.return_value = []

                    result = skill.document(
                        task="Generate API documentation for users endpoint",
                        repo_path=".",
                        dry_run=False,
                    )

                    assert isinstance(result, DocumentGenerationResult)
                    assert result.duration_seconds >= 0

    def test_document_with_existing_page_replace_strategy(self, skill):
        """Test document generation with existing page and replace strategy."""
        skill.config.documentation.merge_strategy = "replace"

        with patch.object(skill, "client") as mock_client:
            with patch.object(skill, "scanner") as mock_scanner:
                mock_scanner.scan_repos.return_value = {"apis": []}
                mock_client.validate_space.return_value = True
                mock_client.check_write_permission.return_value = True
                mock_client.find_page_by_title.return_value = {
                    "id": "existing-page",
                    "title": "Old API Docs",
                }
                mock_client.update_page.return_value = {
                    "id": "existing-page",
                    "title": "Updated API Docs",
                }

                result = skill.document(
                    task="Update API documentation",
                    repo_path=".",
                    dry_run=False,
                )

                assert isinstance(result, DocumentGenerationResult)

    def test_document_with_parent_page_creation(self, skill):
        """Test document generation with parent page."""
        with patch.object(skill, "client") as mock_client:
            with patch.object(skill, "scanner") as mock_scanner:
                mock_scanner.scan_repos.return_value = {"apis": []}
                mock_client.validate_space.return_value = True
                mock_client.check_write_permission.return_value = True
                mock_client.find_page_by_title.side_effect = [
                    None,  # First call for main page
                    {"id": "parent-123"},  # Second call for parent page
                ]
                mock_client.create_page.return_value = {
                    "id": "new-child",
                    "title": "Child Page",
                }

                result = skill.document(
                    task="Generate API docs",
                    parent_page_title="Architecture",
                    repo_path=".",
                    dry_run=False,
                )

                assert isinstance(result, DocumentGenerationResult)


class TestBulkOperations:
    """Test bulk operations."""

    def test_bulk_label_pages_with_results(self, skill):
        """Test bulk label pages with successful results."""
        with patch.object(skill, "search_pages") as mock_search:
            with patch.object(skill.client, "bulk_add_labels") as mock_label:
                mock_search.return_value = [
                    {"id": "page1", "title": "Page 1"},
                    {"id": "page2", "title": "Page 2"},
                ]
                mock_label.return_value = {"success": 2, "failed": 0}

                result = skill.bulk_label_pages("TEST", "API", ["v2", "api"])

                assert result["success"] == 2
                assert result["failed"] == 0

    def test_bulk_label_pages_no_results(self, skill):
        """Test bulk label pages when search returns no results."""
        with patch.object(skill, "search_pages") as mock_search:
            with patch.object(skill.client, "bulk_add_labels") as mock_label:
                mock_search.return_value = []

                result = skill.bulk_label_pages("TEST", "nonexistent", ["label"])

                assert result["success"] == 0
                assert result["failed"] == 0
                mock_label.assert_not_called()


class TestDocumentGenerationResult:
    """Test DocumentGenerationResult usage."""

    def test_result_with_content_preview(self):
        """Test result with content preview."""
        from confluence_skill.models import DocumentGenerationResult

        result = DocumentGenerationResult(
            success=True,
            title="Test Doc",
            content_preview="<p>Sample content</p>",
            dry_run=True,
            duration_seconds=0.75,
        )

        assert result.content_preview == "<p>Sample content</p>"
        assert "Test Doc" in result.summary()

    def test_result_with_multiple_errors_and_warnings(self):
        """Test result with multiple errors and warnings."""
        from confluence_skill.models import DocumentGenerationResult

        result = DocumentGenerationResult(
            success=False,
            errors=[
                ValidationError(
                    level="error",
                    field="space",
                    message="Space not accessible",
                    suggestion="Check space permissions",
                ),
                ValidationError(
                    level="error",
                    field="title",
                    message="Title too long",
                ),
            ],
            warnings=[
                ValidationError(
                    level="warning",
                    field="metadata",
                    message="Missing owner field",
                ),
            ],
        )

        summary = result.summary()
        assert "error" in summary.lower() or "failed" in summary.lower()
        assert result.has_errors()


class TestSkillInitialization:
    """Test SkillConfig initialization and validation."""

    def test_skill_initialization_logs_validation(self, config, monkeypatch):
        """Test that skill logs during initialization."""
        monkeypatch.setenv("TEST_TOKEN", "test-token")

        skill = ConfluenceSkill(config)

        assert skill.config is not None
        assert skill.client is not None
        assert skill.scanner is not None
        assert skill.validator is not None

    def test_skill_with_all_features_enabled(self, config, monkeypatch):
        """Test skill with all optional features enabled."""
        config.jira.enabled = True
        config.guardrails.require_approval = True
        config.output.verbose = True

        monkeypatch.setenv("TEST_TOKEN", "test-token")

        skill = ConfluenceSkill(config)

        assert skill.config.jira.enabled
        assert skill.config.guardrails.require_approval
        assert skill.config.output.verbose


class TestErrorMessages:
    """Test error message generation."""

    def test_print_result_summary_success(self, skill, capsys):
        """Test printing successful result summary."""
        from confluence_skill.models import DocumentGenerationResult

        result = DocumentGenerationResult(
            success=True,
            title="Success Doc",
            document_id="doc-123",
            duration_seconds=1.5,
        )

        skill._print_result_summary(result)
        captured = capsys.readouterr()

        assert "Success Doc" in captured.out or "Success Doc" in captured.err

    def test_print_result_summary_failure(self, skill, capsys):
        """Test printing failed result summary."""
        from confluence_skill.models import DocumentGenerationResult

        result = DocumentGenerationResult(
            success=False,
            errors=[ValidationError(level="error", field="space", message="Space not found")],
            duration_seconds=0.2,
        )

        skill._print_result_summary(result)
        captured = capsys.readouterr()

        # Should print something about the failure
        assert len(captured.out) > 0 or len(captured.err) > 0


# Import at end to avoid circular imports
from confluence_skill.models import DocumentGenerationResult  # noqa: E402
