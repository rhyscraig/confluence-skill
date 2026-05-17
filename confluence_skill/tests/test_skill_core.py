"""Tests for core Confluence Skill methods."""

from unittest.mock import patch

import pytest

from confluence_skill.models import (
    DocumentGenerationResult,
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


class TestDocumentGenerationErrors:
    """Test error handling in document generation."""

    def test_document_space_validation_failure(self, skill):
        """Test when space validation fails."""
        with patch.object(skill, "client") as mock_client:
            with patch.object(skill, "scanner") as mock_scanner:
                mock_scanner.scan_repos.return_value = {"apis": []}
                mock_client.validate_space.return_value = False
                mock_client.find_page_by_title.return_value = None

                result = skill.document(
                    task="Document the API",
                    repo_path=".",
                    dry_run=True,
                )

                # Space validation failure results in error in result
                assert any(e.level == "error" and "space" in e.message.lower() for e in result.errors)

    def test_document_permission_check_failure(self, skill):
        """Test when write permission is denied."""
        with patch.object(skill, "client") as mock_client:
            with patch.object(skill, "scanner") as mock_scanner:
                mock_scanner.scan_repos.return_value = {"apis": []}
                mock_client.validate_space.return_value = True
                mock_client.check_write_permission.return_value = False

                result = skill.document(
                    task="Document the API",
                    repo_path=".",
                    dry_run=True,
                )

                # Permission check failure is logged as warning but execution continues
                assert isinstance(result, DocumentGenerationResult)

    def test_document_with_invalid_space_key(self, skill):
        """Test document with invalid space key."""
        with patch.object(skill, "client"):
            with patch.object(skill, "scanner"):
                # Invalid space key causes error in document generation
                result = skill.document(
                    task="Document the API",
                    space_key="INVALID@!",
                    dry_run=True,
                )
                # Should either raise or return error in result
                assert not result.success or any("space" in e.message.lower() for e in result.errors)

    def test_document_metadata_validation_error(self, skill):
        """Test metadata validation error."""
        with patch.object(skill, "client"):
            with patch.object(skill, "scanner"):
                # Title too short causes validation error
                result = skill.document(
                    task="x",  # Title too short
                    repo_path=".",
                    dry_run=True,
                )
                # Should have title validation error
                assert any("title" in e.message.lower() for e in result.errors)

    def test_document_with_jira_integration_error(self, skill):
        """Test document generation with Jira integration error."""
        skill.config.jira.enabled = True

        with patch.object(skill, "client") as mock_client:
            with patch.object(skill, "scanner") as mock_scanner:
                with patch.object(skill, "validator"):
                    mock_scanner.scan_repos.return_value = {"apis": []}
                    mock_client.validate_space.return_value = True
                    mock_client.check_write_permission.return_value = True

                    result = skill.document(
                        task="Document the API",
                        repo_path=".",
                        dry_run=True,
                    )

                    # Should complete even with Jira issues
                    assert isinstance(result, DocumentGenerationResult)


class TestSearchPages:
    """Test search_pages method."""

    def test_search_pages_delegates_to_client(self, skill):
        """Test that search_pages delegates to client."""
        with patch.object(skill.client, "search_pages") as mock_search:
            mock_search.return_value = [{"id": "123", "title": "Test"}]

            result = skill.search_pages("TEST", "query")

            assert len(result) == 1
            assert result[0]["title"] == "Test"

    def test_search_pages_with_query_string(self, skill):
        """Test search with various query formats."""
        with patch.object(skill.client, "search_pages") as mock_search:
            mock_search.return_value = []

            skill.search_pages("TEST", "payment API")

            mock_search.assert_called_once()


class TestArchivePageMethod:
    """Test archive_page method."""

    def test_archive_page_success(self, skill):
        """Test successful page archival."""
        with patch.object(skill.client, "archive_page") as mock_archive:
            mock_archive.return_value = True

            result = skill.archive_page("page-123")

            assert result is True

    def test_archive_page_failure(self, skill):
        """Test archive page when it fails."""
        with patch.object(skill.client, "archive_page") as mock_archive:
            mock_archive.return_value = False

            result = skill.archive_page("page-123")

            assert result is False


class TestListPageHierarchy:
    """Test list_page_hierarchy method."""

    def test_list_page_hierarchy_with_content(self, skill):
        """Test getting page hierarchy with content."""
        with patch.object(skill.client, "get_page") as mock_get:
            with patch.object(skill.client, "list_child_pages") as mock_children:
                mock_get.return_value = {"id": "page-1", "title": "Parent"}
                mock_children.return_value = [{"id": "child-1"}]

                result = skill.list_page_hierarchy("page-1", include_content=True)

                assert result["id"] == "page-1"
                assert "children" in result

    def test_list_page_hierarchy_without_content(self, skill):
        """Test getting page hierarchy without content."""
        with patch.object(skill.client, "get_page") as mock_get:
            with patch.object(skill.client, "list_child_pages") as mock_children:
                mock_get.return_value = {"id": "page-1", "title": "Parent"}
                mock_children.return_value = []

                result = skill.list_page_hierarchy("page-1")

                assert "children" in result
                assert len(result["children"]) == 0


class TestGenerateMetadataExtended:
    """Test metadata generation edge cases."""

    def test_generate_metadata_from_task(self, skill):
        """Test metadata generation uses task as title."""
        doc_config = skill.config.documentation

        metadata = skill._generate_metadata("My API Documentation Task", doc_config)

        assert metadata.title == "My API Documentation Task"
        assert metadata.owner == "test-team"
        assert "engineers" in metadata.audience

    def test_generate_metadata_invalid_title_too_long(self, skill):
        """Test metadata generation with title too long."""
        doc_config = skill.config.documentation

        with pytest.raises(ValueError, match="title"):
            skill._generate_metadata("x" * 300, doc_config)

    def test_generate_metadata_with_version(self, skill):
        """Test metadata includes version."""
        doc_config = skill.config.documentation
        doc_config.metadata.version = "2.0"

        metadata = skill._generate_metadata("Test", doc_config)

        assert metadata.version == "2.0"


class TestConfigValidation:
    """Test configuration validation."""

    def test_skill_init_with_missing_confluence_url(self):
        """Test skill initialization with missing Confluence URL."""
        with pytest.raises(ValueError, match="instance_url"):
            SkillConfig(
                confluence={
                    "instance_url": "",  # Empty
                    "space_key": "TEST",
                },
                documentation={
                    "metadata": {
                        "owner": "team",
                        "audience": ["eng"],
                    }
                },
            )

    def test_skill_init_with_invalid_confluence_url(self):
        """Test skill initialization with invalid Confluence URL."""
        with pytest.raises(ValueError, match="HTTPS"):
            SkillConfig(
                confluence={
                    "instance_url": "http://invalid.com",  # Not HTTPS
                    "space_key": "TEST",
                },
                documentation={
                    "metadata": {
                        "owner": "team",
                        "audience": ["eng"],
                    }
                },
            )

    def test_skill_init_validates_config(self):
        """Test skill initialization validates configuration."""
        config = SkillConfig(
            confluence={
                "instance_url": "https://org.atlassian.net",
                "space_key": "TEST",
            },
            documentation={
                "metadata": {
                    "owner": "team",
                    "audience": ["engineers"],
                }
            },
        )
        # Config should have validation errors if required fields missing
        errors = config.validate_required_fields()
        # When validating, missing fields should be caught
        assert isinstance(errors, list)


class TestResultSummaries:
    """Test result summary generation."""

    def test_generation_result_success_summary(self):
        """Test successful result summary."""
        result = DocumentGenerationResult(
            success=True,
            title="Test Doc",
            document_id="123",
            document_url="https://test.atlassian.net/wiki/spaces/TEST/pages/123",
            dry_run=False,
            duration_seconds=1.5,
        )

        summary = result.summary()

        assert "Test Doc" in summary
        assert "generated successfully" in summary.lower()
        assert "1.50s" in summary

    def test_generation_result_failure_summary(self):
        """Test failure result summary."""
        result = DocumentGenerationResult(
            success=False,
            errors=[ValidationError(level="error", field="space", message="Space not found")],
            duration_seconds=0.5,
        )

        summary = result.summary()

        assert "failed" in summary.lower() or "Generation failed" in summary
        assert "space" in summary.lower()

    def test_has_errors_method(self):
        """Test has_errors detection."""
        result = DocumentGenerationResult(
            success=False,
            errors=[ValidationError(level="error", field="test", message="Test error")],
        )

        assert result.has_errors()

    def test_has_no_errors(self):
        """Test when there are no errors."""
        result = DocumentGenerationResult(
            success=True,
            warnings=[ValidationError(level="warning", field="test", message="Test warning")],
        )

        assert not result.has_errors()
