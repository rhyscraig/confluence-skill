"""Pytest fixtures and configuration for Confluence skill tests."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

from skills.confluence.models import (
    SkillConfig,
    ConfluenceConfig,
    DocumentationConfig,
    CodeAnalysisConfig,
    GuardrailsConfig,
    DocumentMetadata,
)


@pytest.fixture
def mock_confluence_config():
    """Create mock Confluence configuration."""
    return ConfluenceConfig(
        instance_url="https://test.atlassian.net",
        space_key="TEST",
        auth_token_env="TEST_TOKEN",
    )


@pytest.fixture
def skill_config(mock_confluence_config):
    """Create skill configuration for testing."""
    return SkillConfig(
        confluence=mock_confluence_config,
        documentation=DocumentationConfig(
            template="api",
            space_key="ENG",
            metadata={"owner": "test-team", "audience": ["engineers"]},
        ),
        code_analysis=CodeAnalysisConfig(
            enabled=True,
            repos=[],
        ),
        guardrails=GuardrailsConfig(
            enabled=True,
            require_approval=False,
            dry_run_by_default=True,
        ),
    )


@pytest.fixture
def document_metadata():
    """Create sample document metadata."""
    return DocumentMetadata(
        title="Test API Documentation",
        space_key="ENG",
        version="1.0",
        owner="test-team",
        audience=["engineers", "oncall"],
        status="draft",
    )


@pytest.fixture
def mock_confluence_client():
    """Create mock Confluence API client."""
    client = MagicMock()
    client.find_page_by_title.return_value = None
    client.check_write_permission.return_value = True
    client.get_space.return_value = {"id": "123", "key": "TEST"}
    client.create_page.return_value = {
        "id": "page-123",
        "title": "Test Page",
        "status": "current",
    }
    client.update_page.return_value = {
        "id": "page-123",
        "title": "Test Page",
        "version": {"number": 2},
    }
    return client


@pytest.fixture
def extracted_info():
    """Create sample extracted code information."""
    return {
        "apis": [
            {"type": "endpoint", "method": "GET", "path": "/users", "file": "api.py"},
            {"type": "endpoint", "method": "POST", "path": "/users", "file": "api.py"},
        ],
        "architecture": [
            {
                "type": "file_structure",
                "summary": "Repository contains 5 file types",
                "details": {".py": 45, ".txt": 10},
            }
        ],
        "dependencies": [
            {"type": "python", "name": "requests", "spec": "requests>=2.0"},
            {"type": "python", "name": "pydantic", "spec": "pydantic>=1.0"},
        ],
        "classes": [
            {"type": "class", "name": "UserService", "file": "service.py", "methods": ["get_user"]},
        ],
        "functions": [
            {"type": "function", "name": "validate_email", "file": "utils.py"},
        ],
    }
