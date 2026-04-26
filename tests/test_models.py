"""Tests for Confluence skill models."""

import pytest
from datetime import datetime

from skills.confluence.models import (
    SkillConfig,
    ConfluenceConfig,
    DocumentMetadata,
    DocumentChange,
    DocumentGenerationResult,
    MergeStrategy,
    DocumentStatus,
)


def test_confluence_config_valid():
    """Test creating valid Confluence configuration."""
    config = ConfluenceConfig(
        instance_url="https://test.atlassian.net",
        space_key="ENG",
    )
    assert config.instance_url == "https://test.atlassian.net"
    assert config.space_key == "ENG"


def test_confluence_config_invalid_url():
    """Test Confluence config rejects invalid URLs."""
    with pytest.raises(ValueError):
        ConfluenceConfig(instance_url="http://test.atlassian.net")  # Not HTTPS

    with pytest.raises(ValueError):
        ConfluenceConfig(instance_url="https://test.example.com")  # Not .atlassian.net


def test_confluence_config_url_normalization():
    """Test Confluence config normalizes URLs."""
    config = ConfluenceConfig(instance_url="https://test.atlassian.net/")
    assert config.instance_url == "https://test.atlassian.net"


def test_document_metadata_creation():
    """Test creating document metadata."""
    metadata = DocumentMetadata(
        title="API Documentation",
        space_key="ENG",
        owner="platform-team",
        audience=["engineers", "oncall"],
    )
    assert metadata.title == "API Documentation"
    assert metadata.owner == "platform-team"
    assert len(metadata.audience) == 2


def test_document_metadata_hash():
    """Test document metadata content hash."""
    metadata1 = DocumentMetadata(
        title="API Docs",
        version="1.0",
        status="draft",
        labels=["api", "v1"],
    )

    metadata2 = DocumentMetadata(
        title="API Docs",
        version="1.0",
        status="draft",
        labels=["api", "v1"],
    )

    # Same metadata should produce same hash
    assert metadata1.content_hash() == metadata2.content_hash()

    # Different metadata should produce different hash
    metadata3 = DocumentMetadata(
        title="API Docs",
        version="2.0",
        status="published",
        labels=["api", "v2"],
    )
    assert metadata1.content_hash() != metadata3.content_hash()


def test_document_change_summary():
    """Test document change summary generation."""
    change = DocumentChange(
        document_id="123",
        title="Test Doc",
        action="create",
        changes_made=["Added API section", "Updated examples"],
        dry_run=False,
    )

    summary = change.summary()
    assert "CREATE" in summary
    assert "Test Doc" in summary
    assert "Added API section" in summary


def test_document_change_dry_run_flag():
    """Test document change shows dry run flag."""
    change = DocumentChange(
        document_id="123",
        title="Test Doc",
        action="update",
        dry_run=True,
    )

    summary = change.summary()
    assert "DRY RUN" in summary


def test_document_generation_result_success():
    """Test successful document generation result."""
    result = DocumentGenerationResult(
        success=True,
        document_id="123",
        document_url="https://confluence.example.com/page/123",
        title="Test Doc",
        dry_run=False,
    )

    assert result.success
    assert result.has_errors() is False
    summary = result.summary()
    assert "✅" in summary


def test_document_generation_result_with_errors():
    """Test generation result with validation errors."""
    from skills.confluence.models import ValidationError

    result = DocumentGenerationResult(
        success=False,
        title="Test Doc",
        errors=[
            ValidationError("error", "metadata", "Missing owner field"),
        ],
    )

    assert not result.success
    assert result.has_errors()
    summary = result.summary()
    assert "❌" in summary
    assert "Missing owner" in summary


def test_merge_strategy_enum():
    """Test MergeStrategy enum values."""
    assert MergeStrategy.APPEND.value == "append"
    assert MergeStrategy.REPLACE.value == "replace"
    assert MergeStrategy.INTERACTIVE.value == "interactive"
    assert MergeStrategy.SKIP.value == "skip"


def test_document_status_enum():
    """Test DocumentStatus enum values."""
    assert DocumentStatus.DRAFT.value == "draft"
    assert DocumentStatus.REVIEW.value == "review"
    assert DocumentStatus.PUBLISHED.value == "published"
    assert DocumentStatus.ARCHIVED.value == "archived"
