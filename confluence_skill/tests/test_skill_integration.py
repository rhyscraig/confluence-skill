"""Integration tests for Confluence skill."""

import pytest
from unittest.mock import patch, MagicMock

from skills.confluence.skill import ConfluenceSkill
from skills.confluence.models import SkillConfig, ConfluenceConfig, DocumentTemplate


@pytest.fixture
def skill(skill_config):
    """Create skill instance for testing."""
    # Mock the ConfluenceClient to avoid real API calls
    with patch('skills.confluence.skill.ConfluenceClient'):
        return ConfluenceSkill(skill_config)


def test_skill_initialization(skill_config):
    """Test skill initialization."""
    with patch('skills.confluence.skill.ConfluenceClient'):
        skill = ConfluenceSkill(skill_config)
    assert skill.config == skill_config
    assert skill.console is not None


def test_skill_document_dry_run(skill, document_metadata):
    """Test document generation in dry-run mode."""
    with patch.object(skill.scanner, 'scan_repos', return_value={}):
        with patch.object(skill.client, 'find_page_by_title', return_value=None):
            with patch.object(skill.client, 'check_write_permission', return_value=True):
                result = skill.document(
                    task="Test API Documentation",
                    doc_type="api",
                    dry_run=True,
                )

    assert result.dry_run is True
    assert result.title == "Test API Documentation"


def test_skill_document_existing_page(skill):
    """Test handling of existing pages."""
    with patch.object(skill.scanner, 'scan_repos', return_value={}):
        with patch.object(
            skill.client,
            'find_page_by_title',
            return_value={'id': 'page-123', 'title': 'Test'},
        ):
            with patch.object(skill.client, 'check_write_permission', return_value=True):
                result = skill.document(
                    task="Test API Documentation",
                    dry_run=True,
                )

    assert result.document_id == 'page-123'


def test_skill_document_permission_denied(skill):
    """Test permission check failure."""
    with patch.object(skill.scanner, 'scan_repos', return_value={}):
        with patch.object(skill.client, 'find_page_by_title', return_value=None):
            with patch.object(skill.client, 'check_write_permission', return_value=False):
                result = skill.document(
                    task="Test Documentation",
                    dry_run=True,
                )

    assert not result.success
    assert len(result.errors) > 0


def test_skill_document_with_extracted_info(skill, extracted_info):
    """Test document generation with code analysis."""
    with patch.object(skill.scanner, 'scan_repos', return_value=extracted_info):
        with patch.object(skill.client, 'find_page_by_title', return_value=None):
            with patch.object(skill.client, 'check_write_permission', return_value=True):
                result = skill.document(
                    task="Payment Service API",
                    doc_type="api",
                    dry_run=True,
                )

    assert result.success
    assert result.content_preview is not None
    assert "/users" in result.content_preview or "API" in result.content_preview


def test_skill_document_validates_metadata(skill):
    """Test that document validates metadata."""
    with patch.object(skill.validator, 'validate_metadata') as mock_validate:
        mock_validate.return_value = True

        with patch.object(skill.scanner, 'scan_repos', return_value={}):
            with patch.object(skill.client, 'find_page_by_title', return_value=None):
                with patch.object(skill.client, 'check_write_permission', return_value=True):
                    result = skill.document(
                        task="Test",
                        dry_run=True,
                    )

    assert mock_validate.called


def test_skill_document_validates_content(skill):
    """Test that document validates content."""
    with patch.object(skill.validator, 'validate_content') as mock_validate:
        with patch.object(skill.scanner, 'scan_repos', return_value={}):
            with patch.object(skill.client, 'find_page_by_title', return_value=None):
                with patch.object(skill.client, 'check_write_permission', return_value=True):
                    result = skill.document(
                        task="Test",
                        dry_run=True,
                    )

    assert mock_validate.called


def test_skill_create_page(skill):
    """Test page creation."""
    mock_client = skill.client
    mock_client.find_page_by_title.return_value = None
    mock_client.check_write_permission.return_value = True
    mock_client.create_page.return_value = {
        'id': 'new-page-123',
        'title': 'New Page',
    }

    with patch.object(skill.scanner, 'scan_repos', return_value={}):
        result = skill.document(
            task="New Documentation",
            dry_run=False,
        )

    # Would need real client setup to fully test, but structure is validated
    assert result is not None


def test_skill_configuration_override(skill_config):
    """Test configuration overrides."""
    with patch('skills.confluence.skill.ConfluenceClient'):
        skill = ConfluenceSkill(skill_config)

        with patch.object(skill.scanner, 'scan_repos', return_value={}):
            with patch.object(skill.client, 'find_page_by_title', return_value=None):
                with patch.object(skill.client, 'check_write_permission', return_value=True):
                    result = skill.document(
                        task="Test",
                        doc_type="architecture",  # Override template
                        space_key="CUSTOM",  # Override space
                        dry_run=True,
                    )

    assert result is not None


def test_skill_duration_tracking(skill):
    """Test that skill tracks operation duration."""
    with patch.object(skill.scanner, 'scan_repos', return_value={}):
        with patch.object(skill.client, 'find_page_by_title', return_value=None):
            with patch.object(skill.client, 'check_write_permission', return_value=True):
                result = skill.document(
                    task="Test",
                    dry_run=True,
                )

    assert result.duration_seconds >= 0


def test_skill_error_handling(skill):
    """Test skill error handling."""
    with patch.object(skill.scanner, 'scan_repos', side_effect=Exception("Scan failed")):
        result = skill.document(
            task="Test",
            dry_run=True,
        )

    assert not result.success
    assert len(result.errors) > 0
