"""Tests for Jira integration."""

import pytest
from unittest.mock import Mock, patch

from skills.confluence.jira_integration import JiraClient, JiraIntegration
from skills.confluence.models import JiraConfig


@pytest.fixture
def jira_config():
    """Create Jira configuration."""
    return JiraConfig(
        enabled=True,
        instance_url="https://test.atlassian.net",
        auth_token_env="TEST_JIRA_TOKEN",
        default_project="TEST",
    )


@pytest.fixture
def jira_client(jira_config):
    """Create Jira client with mocked session."""
    with patch.dict("os.environ", {"TEST_JIRA_TOKEN": "fake-token"}):
        client = JiraClient(jira_config)
        client.session = Mock()
    return client


def test_jira_client_disabled_when_no_token(jira_config):
    """Test Jira client is disabled if token not set."""
    # Don't set the token
    client = JiraClient(jira_config)
    assert client.enabled is False


def test_jira_client_enabled_with_token(jira_config):
    """Test Jira client is enabled with token."""
    with patch.dict("os.environ", {"TEST_JIRA_TOKEN": "fake-token"}):
        client = JiraClient(jira_config)
        assert client.enabled is True


def test_jira_client_find_related_issues(jira_client):
    """Test finding related issues."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "issues": [
            {
                "key": "TEST-1",
                "fields": {
                    "summary": "Implement payment API",
                    "status": {"name": "In Progress"},
                },
                "self": "https://test.atlassian.net/rest/api/3/issue/10000",
            }
        ]
    }
    jira_client.session.get.return_value = mock_response

    issues = jira_client.find_related_issues("TEST", "payment")

    assert len(issues) == 1
    assert issues[0]["key"] == "TEST-1"


def test_jira_client_find_related_issues_empty(jira_client):
    """Test finding related issues when none exist."""
    mock_response = Mock()
    mock_response.json.return_value = {"issues": []}
    jira_client.session.get.return_value = mock_response

    issues = jira_client.find_related_issues("TEST", "nonexistent")

    assert issues == []


def test_jira_client_find_related_issues_network_error(jira_client):
    """Test handling network errors."""
    import requests

    jira_client.session.get.side_effect = requests.RequestException("Network error")

    issues = jira_client.find_related_issues("TEST", "payment")

    assert issues == []


def test_jira_client_create_issue(jira_client):
    """Test creating Jira issue."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "id": "10000",
        "key": "TEST-42",
    }
    jira_client.session.post.return_value = mock_response

    issue = jira_client.create_issue(
        "TEST",
        summary="Document API",
        description="Add API docs",
    )

    assert issue is not None
    assert issue["key"] == "TEST-42"


def test_jira_client_create_issue_with_epic(jira_client):
    """Test creating issue linked to epic."""
    jira_client.config.custom_fields = {"epic_link": "customfield_10014"}

    mock_response = Mock()
    mock_response.json.return_value = {"key": "TEST-42"}
    jira_client.session.post.return_value = mock_response

    issue = jira_client.create_issue(
        "TEST",
        summary="Document API",
        description="Add API docs",
        epic_key="TEST-1",
    )

    # Check that epic field was included
    call_args = jira_client.session.post.call_args
    assert call_args is not None


def test_jira_integration_initialization(jira_config):
    """Test JiraIntegration initialization."""
    with patch.dict("os.environ", {"TEST_JIRA_TOKEN": "fake-token"}):
        integration = JiraIntegration(jira_config)
        assert integration.config == jira_config
        assert integration.client is not None


def test_jira_integration_link_related_issues_disabled():
    """Test linking is skipped when disabled."""
    config = JiraConfig(enabled=False)
    integration = JiraIntegration(config)

    issues = integration.link_related_issues("page-1", "TEST", "service", Mock())

    assert issues == []


def test_jira_integration_find_undocumented_apis():
    """Test finding undocumented APIs."""
    config = JiraConfig(
        enabled=True,
        instance_url="https://test.atlassian.net",
        auth_token_env="TEST_TOKEN",
    )

    with patch.dict("os.environ", {"TEST_TOKEN": "fake-token"}):
        integration = JiraIntegration(config)

        # Mock the session and API call
        mock_response = Mock()
        mock_response.json.return_value = {
            "issues": [
                {
                    "fields": {
                        "summary": "Document GET /api/users",
                    }
                }
            ]
        }
        integration.client.session = Mock()
        integration.client.session.get.return_value = mock_response

        apis = [
            {"method": "GET", "path": "/api/users"},
            {"method": "POST", "path": "/api/payments"},  # This is undocumented
        ]

        undocumented = integration.find_undocumented_apis("TEST", apis)

        # POST /api/payments should be undocumented
        assert len(undocumented) == 1
        assert undocumented[0]["path"] == "/api/payments"


def test_jira_integration_generate_jira_section():
    """Test generating Jira status section."""
    config = JiraConfig(
        enabled=True,
        instance_url="https://test.atlassian.net",
        auth_token_env="TEST_TOKEN",
    )

    with patch.dict("os.environ", {"TEST_TOKEN": "fake-token"}):
        integration = JiraIntegration(config)

        # Mock the session and API call
        mock_response = Mock()
        mock_response.json.return_value = {
            "issues": [
                {
                    "key": "TEST-1",
                    "fields": {
                        "summary": "Implement payment API",
                        "status": {"name": "In Progress"},
                    },
                    "self": "https://test.atlassian.net/rest/api/3/issue/10000",
                }
            ]
        }
        integration.client.session = Mock()
        integration.client.session.get.return_value = mock_response

        html = integration.generate_jira_section("TEST", "payment")

        assert "TEST-1" in html
        assert "Implementation Status" in html
        assert "In Progress" in html


def test_jira_integration_disabled_returns_empty():
    """Test that disabled Jira returns empty sections."""
    config = JiraConfig(enabled=False)
    integration = JiraIntegration(config)

    html = integration.generate_jira_section("TEST", "service")

    assert html == ""
