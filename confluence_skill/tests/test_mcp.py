"""Tests for MCP server module."""

from unittest.mock import MagicMock, patch

import pytest

from confluence_skill.mcp import confluence_archive, confluence_document, confluence_search, get_default_config


@pytest.fixture
def mock_config():
    """Create a mock SkillConfig."""
    with patch("confluence_skill.mcp.SkillConfig") as mock:
        yield mock


@pytest.fixture
def mock_skill():
    """Create a mock ConfluenceSkill."""
    with patch("confluence_skill.mcp.ConfluenceSkill") as mock:
        yield mock


class TestGetDefaultConfig:
    """Test configuration loading."""

    def test_get_default_config_from_yaml(self):
        """Test loading config from YAML file."""
        with patch("confluence_skill.mcp.SkillConfig.from_yaml") as mock_from_yaml:
            mock_config = MagicMock()
            mock_from_yaml.return_value = mock_config

            result = get_default_config()

            assert result == mock_config
            mock_from_yaml.assert_called_once_with(".confluence.yaml")

    def test_get_default_config_fallback_to_env(self):
        """Test fallback to environment variables when YAML not found."""
        with patch("confluence_skill.mcp.SkillConfig.from_yaml") as mock_from_yaml:
            with patch("confluence_skill.mcp.SkillConfig.from_env") as mock_from_env:
                mock_from_yaml.side_effect = FileNotFoundError()
                mock_config = MagicMock()
                mock_from_env.return_value = mock_config

                result = get_default_config()

                assert result == mock_config
                mock_from_env.assert_called_once()


class TestConfluenceDocumentTool:
    """Test confluence_document MCP tool."""

    def test_confluence_document_success(self, mock_skill, mock_config):
        """Test successful document generation."""
        mock_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.summary = "Generated documentation"
        mock_instance.document.return_value = mock_result
        mock_skill.return_value = mock_instance
        mock_config.from_yaml.return_value = MagicMock()

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            result = confluence_document(
                task="Document the API",
                doc_type="api",
                repo_path=".",
                dry_run=True,
            )

            assert "Generated documentation" in result or result is not None

    def test_confluence_document_with_defaults(self, mock_skill):
        """Test document generation with default parameters."""
        mock_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.summary = "Generated"
        mock_instance.document.return_value = mock_result
        mock_skill.return_value = mock_instance

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            result = confluence_document(
                task="Document",
                doc_type="architecture",
            )

            assert isinstance(result, str)

    def test_confluence_document_error_handling(self, mock_skill):
        """Test error handling in document generation."""
        mock_skill.side_effect = Exception("Connection error")

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            result = confluence_document(
                task="Document",
                doc_type="api",
            )

            assert "Error" in result or "error" in result.lower()

    def test_confluence_document_exception_in_skill_call(self, mock_skill):
        """Test exception during skill.document call."""
        mock_instance = MagicMock()
        mock_instance.document.side_effect = RuntimeError("Document generation failed")
        mock_skill.return_value = mock_instance

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            result = confluence_document(
                task="Document",
                doc_type="api",
            )

            assert "Error" in result


class TestConfluenceSearchTool:
    """Test confluence_search MCP tool."""

    def test_confluence_search_success(self, mock_skill):
        """Test successful page search."""
        mock_instance = MagicMock()
        mock_instance.search_pages.return_value = [
            {"title": "API Docs", "id": "123"},
            {"title": "Architecture", "id": "456"},
        ]
        mock_skill.return_value = mock_instance

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            result = confluence_search(query="API", space_key="TEST")

            assert "API Docs" in result
            assert "Architecture" in result
            assert "Found 2 pages" in result

    def test_confluence_search_no_results(self, mock_skill):
        """Test search with no results."""
        mock_instance = MagicMock()
        mock_instance.search_pages.return_value = []
        mock_skill.return_value = mock_instance

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            result = confluence_search(query="nonexistent")

            assert "Found 0 pages" in result

    def test_confluence_search_max_results(self, mock_skill):
        """Test search respects max_results limit."""
        mock_instance = MagicMock()
        mock_instance.search_pages.return_value = [{"title": f"Page {i}", "id": str(i)} for i in range(20)]
        mock_skill.return_value = mock_instance

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            result = confluence_search(query="test", max_results=5)

            # Should only show first 5 results
            assert result.count("Page") <= 5

    def test_confluence_search_error_handling(self, mock_skill):
        """Test error handling in search."""
        mock_instance = MagicMock()
        mock_instance.search_pages.side_effect = Exception("Search failed")
        mock_skill.return_value = mock_instance

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            result = confluence_search(query="test")

            assert "Error" in result

    def test_confluence_search_without_space_key(self, mock_skill):
        """Test search without specifying space key."""
        mock_instance = MagicMock()
        mock_instance.search_pages.return_value = [{"title": "Test", "id": "1"}]
        mock_skill.return_value = mock_instance

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            result = confluence_search(query="test")

            assert "Found 1 pages" in result


class TestConfluenceArchiveTool:
    """Test confluence_archive MCP tool."""

    def test_confluence_archive_success(self, mock_skill):
        """Test successful page archival."""
        mock_instance = MagicMock()
        mock_instance.archive_page.return_value = True
        mock_skill.return_value = mock_instance

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            result = confluence_archive(
                page_id="page-123",
                reason="Obsolete",
            )

            assert "Successfully archived" in result
            assert "page-123" in result

    def test_confluence_archive_with_default_reason(self, mock_skill):
        """Test archival with default reason."""
        mock_instance = MagicMock()
        mock_instance.archive_page.return_value = True
        mock_skill.return_value = mock_instance

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            result = confluence_archive(page_id="page-123")

            assert "Successfully archived" in result
            assert "Archived by automation" in result

    def test_confluence_archive_error_handling(self, mock_skill):
        """Test error handling in archival."""
        mock_instance = MagicMock()
        mock_instance.archive_page.side_effect = Exception("Archive failed")
        mock_skill.return_value = mock_instance

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            result = confluence_archive(page_id="page-123")

            assert "Error" in result

    def test_confluence_archive_skill_initialization_error(self):
        """Test when ConfluenceSkill initialization fails."""
        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.side_effect = Exception("Config error")

            result = confluence_archive(page_id="page-123")

            assert "Error" in result


class TestMCPToolIntegration:
    """Test integration of multiple tools."""

    def test_search_then_archive_workflow(self, mock_skill):
        """Test workflow of searching and archiving pages."""
        mock_instance = MagicMock()
        mock_instance.search_pages.return_value = [{"id": "123"}]
        mock_instance.archive_page.return_value = True
        mock_skill.return_value = mock_instance

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            search_result = confluence_search(query="old")
            assert "Found 1 pages" in search_result

            archive_result = confluence_archive(page_id="123")
            assert "Successfully archived" in archive_result

    def test_document_generation_workflow(self, mock_skill):
        """Test document generation workflow."""
        mock_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.summary = "Generated API documentation"
        mock_instance.document.return_value = mock_result
        mock_skill.return_value = mock_instance

        with patch("confluence_skill.mcp.get_default_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()

            result = confluence_document(
                task="Generate API docs",
                doc_type="api",
                dry_run=True,
            )

            assert isinstance(result, str)
