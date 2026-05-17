"""Tests for CLI interface."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from confluence_skill.cli import main


@pytest.fixture
def mock_skill():
    """Create a mock ConfluenceSkill."""
    with patch("confluence_skill.cli.ConfluenceSkill") as mock:
        yield mock


@pytest.fixture
def mock_config():
    """Create a mock SkillConfig."""
    with patch("confluence_skill.cli.SkillConfig") as mock:
        yield mock


def test_cli_version(capsys):
    """Test version command."""
    import confluence_skill

    with patch.object(sys, "argv", ["confluence", "--version"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()
    assert confluence_skill.__version__ in captured.out or confluence_skill.__version__ in captured.err


def test_cli_help(capsys):
    """Test help command."""
    with patch.object(sys, "argv", ["confluence", "--help"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower() or "usage:" in captured.err.lower()


def test_cli_document_dry_run(mock_skill, mock_config):
    """Test document command with dry run."""
    mock_instance = MagicMock()
    mock_instance.document.return_value = MagicMock(summary="Generated documentation")
    mock_skill.return_value = mock_instance
    mock_config.from_yaml.return_value = MagicMock()

    with patch.object(sys, "argv", ["confluence", "document", "Test task", "--doc-type", "api", "--dry-run"]):
        try:
            main()
        except SystemExit:
            pass

    assert mock_instance.document.called


def test_cli_document_publish_requires_approval(mock_skill, mock_config, monkeypatch):
    """Test that publish requires dry-run approval first."""
    mock_instance = MagicMock()
    mock_instance.document.return_value = MagicMock(summary="Generated")
    mock_skill.return_value = mock_instance
    mock_config.from_yaml.return_value = MagicMock()

    # Simulate user input
    inputs = iter(["n"])  # User refuses
    monkeypatch.setattr("builtins.input", lambda _: next(inputs, ""))

    with patch.object(sys, "argv", ["confluence", "document", "Test task", "--doc-type", "api", "--publish"]):
        try:
            main()
        except (SystemExit, StopIteration):
            pass


def test_cli_search(mock_skill, mock_config):
    """Test search command."""
    mock_instance = MagicMock()
    mock_instance.search_pages.return_value = [{"id": "123", "title": "Test Page"}]
    mock_skill.return_value = mock_instance
    mock_config.from_yaml.return_value = MagicMock()

    with patch.object(sys, "argv", ["confluence", "search", "payment API"]):
        try:
            main()
        except SystemExit:
            pass

    assert mock_instance.search_pages.called


def test_cli_archive(mock_skill, mock_config):
    """Test archive command."""
    mock_instance = MagicMock()
    mock_instance.archive_page.return_value = True
    mock_skill.return_value = mock_instance
    mock_config.from_yaml.return_value = MagicMock()

    with patch.object(sys, "argv", ["confluence", "archive", "123456", "--reason", "Obsolete"]):
        try:
            main()
        except SystemExit:
            pass

    assert mock_instance.archive_page.called


def test_cli_error_handling(mock_skill, mock_config):
    """Test error handling in CLI."""
    mock_skill.side_effect = Exception("Connection error")

    with patch.object(sys, "argv", ["confluence", "document", "Test", "--doc-type", "api"]):
        try:
            main()
        except SystemExit:
            pass


def test_cli_invalid_command(capsys):
    """Test invalid command handling."""
    with patch.object(sys, "argv", ["confluence", "invalid-command"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()
    assert "invalid" in captured.err.lower() or "unrecognized" in captured.err.lower()


def test_cli_missing_required_args(capsys):
    """Test missing required arguments."""
    with patch.object(sys, "argv", ["confluence", "document"]):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()
    assert "required" in captured.err.lower() or "usage:" in captured.err.lower()


def test_cli_config_from_env(mock_skill):
    """Test loading config from environment."""
    with patch("confluence_skill.cli.SkillConfig.from_yaml", side_effect=FileNotFoundError):
        mock_instance = MagicMock()
        mock_skill.return_value = mock_instance
        mock_config = MagicMock()

        with patch("confluence_skill.cli.SkillConfig.from_env", return_value=mock_config):
            with patch.object(sys, "argv", ["confluence", "document", "Test", "--doc-type", "api", "--dry-run"]):
                try:
                    main()
                except SystemExit:
                    pass

            assert mock_skill.called


def test_cli_document_all_templates(mock_skill, mock_config):
    """Test document command with all template types."""
    templates = ["api", "architecture", "adr", "runbook", "feature", "infrastructure", "troubleshooting", "custom"]

    for template in templates:
        mock_instance = MagicMock()
        mock_instance.document.return_value = MagicMock(summary="Generated")
        mock_skill.return_value = mock_instance
        mock_config.from_yaml.return_value = MagicMock()

        with patch.object(sys, "argv", ["confluence", "document", "Test", "--doc-type", template, "--dry-run"]):
            try:
                main()
            except SystemExit:
                pass

        assert mock_instance.document.called


def test_cli_search_with_space_key(mock_skill, mock_config):
    """Test search with specific space key."""
    mock_instance = MagicMock()
    mock_instance.search_pages.return_value = []
    mock_skill.return_value = mock_instance
    mock_config.from_yaml.return_value = MagicMock()

    with patch.object(sys, "argv", ["confluence", "search", "test", "--space-key", "ENGINEERING"]):
        try:
            main()
        except SystemExit:
            pass

    assert mock_instance.search_pages.called
    call_kwargs = mock_instance.search_pages.call_args[1]
    assert call_kwargs.get("space_key") == "ENGINEERING"


def test_cli_archive_with_default_reason(mock_skill, mock_config):
    """Test archive without explicit reason."""
    mock_instance = MagicMock()
    mock_instance.archive_page.return_value = True
    mock_skill.return_value = mock_instance
    mock_config.from_yaml.return_value = MagicMock()

    with patch.object(sys, "argv", ["confluence", "archive", "123456"]):
        try:
            main()
        except SystemExit:
            pass

    assert mock_instance.archive_page.called


def test_cli_document_with_repo_path(mock_skill, mock_config):
    """Test document command with custom repo path."""
    mock_instance = MagicMock()
    mock_instance.document.return_value = MagicMock(summary="Generated")
    mock_skill.return_value = mock_instance
    mock_config.from_yaml.return_value = MagicMock()

    with patch.object(
        sys,
        "argv",
        ["confluence", "document", "Test", "--doc-type", "api", "--repo-path", "/path/to/repo", "--dry-run"],
    ):
        try:
            main()
        except SystemExit:
            pass

    assert mock_instance.document.called
    call_kwargs = mock_instance.document.call_args[1]
    assert call_kwargs.get("repo_path") == "/path/to/repo"
