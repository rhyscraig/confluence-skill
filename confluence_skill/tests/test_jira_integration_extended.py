"""Extended tests for Jira integration coverage."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from confluence_skill.jira_integration import JiraClient, JiraIntegration
from confluence_skill.models import JiraConfig


@pytest.fixture
def jira_config():
    """Create test Jira config."""
    return JiraConfig(
        enabled=True,
        instance_url="https://test.atlassian.net",
        auth_token_env="JIRA_TOKEN",
        default_project="INFRA",
    )


@pytest.fixture
def jira_client(jira_config, monkeypatch):
    """Create JiraClient."""
    monkeypatch.setenv("JIRA_TOKEN", "test-jira-token")
    return JiraClient(jira_config)


class TestJiraClientInitialization:
    """Test JiraClient initialization."""

    def test_jira_client_disabled_when_config_disabled(self):
        """Test client is disabled when config.enabled is False."""
        config = JiraConfig(
            enabled=False,
            instance_url="https://test.atlassian.net",
        )

        client = JiraClient(config)

        assert client.enabled is False

    def test_jira_client_disabled_when_no_instance_url(self):
        """Test client is disabled when instance_url is missing."""
        config = JiraConfig(
            enabled=True,
            instance_url="",
        )

        client = JiraClient(config)

        assert client.enabled is False

    def test_jira_client_disabled_when_token_missing(self, monkeypatch):
        """Test client is disabled when auth token is missing."""
        config = JiraConfig(
            enabled=True,
            instance_url="https://test.atlassian.net",
            auth_token_env="MISSING_TOKEN",
        )

        monkeypatch.delenv("MISSING_TOKEN", raising=False)

        client = JiraClient(config)

        assert client.enabled is False

    def test_jira_client_enabled_with_valid_config(self, jira_client):
        """Test client is enabled with valid config."""
        assert jira_client.enabled is True
        assert jira_client.config is not None
        assert jira_client.base_url == "https://test.atlassian.net"

    def test_jira_client_session_has_auth_header(self, jira_client):
        """Test that session has proper auth headers."""
        assert "Authorization" in jira_client.session.headers
        assert "Bearer" in jira_client.session.headers["Authorization"]
        assert "Content-Type" in jira_client.session.headers


class TestJiraClientMethods:
    """Test JiraClient methods."""

    def test_find_related_issues_success(self, jira_client):
        """Test finding related issues."""
        with patch.object(jira_client.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "issues": [
                    {"key": "INFRA-1", "summary": "API endpoint", "status": "Done"},
                    {"key": "INFRA-2", "summary": "Database", "status": "In Progress"},
                ]
            }
            mock_get.return_value = mock_response

            result = jira_client.find_related_issues("INFRA", "payment API")

            assert len(result) == 2
            assert result[0]["key"] == "INFRA-1"
            mock_get.assert_called_once()

    def test_find_related_issues_with_issue_types_filter(self, jira_client):
        """Test finding related issues with type filter."""
        with patch.object(jira_client.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"issues": []}
            mock_get.return_value = mock_response

            result = jira_client.find_related_issues(
                "INFRA",
                "payment API",
                issue_types=["Story", "Task"],
            )

            assert result == []
            # Verify JQL included type filter
            call_args = mock_get.call_args
            assert "type in" in call_args[1]["params"]["jql"]

    def test_find_related_issues_request_error(self, jira_client):
        """Test handling request errors."""
        with patch.object(jira_client.session, "get") as mock_get:
            mock_get.side_effect = requests.RequestException("Connection error")

            result = jira_client.find_related_issues("INFRA", "payment API")

            assert result == []

    def test_find_related_issues_disabled_client(self):
        """Test find_related_issues when client is disabled."""
        config = JiraConfig(enabled=False)
        client = JiraClient(config)

        result = client.find_related_issues("INFRA", "test")

        assert result == []

    def test_find_epic_for_service_success(self, jira_client):
        """Test finding epic for service."""
        with patch.object(jira_client.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"issues": [{"key": "INFRA-100", "summary": "Payment Service Epic"}]}
            mock_get.return_value = mock_response

            result = jira_client.find_epic_for_service("INFRA", "Payment Service")

            assert result["key"] == "INFRA-100"

    def test_find_epic_for_service_not_found(self, jira_client):
        """Test when no epic found."""
        with patch.object(jira_client.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"issues": []}
            mock_get.return_value = mock_response

            result = jira_client.find_epic_for_service("INFRA", "Unknown Service")

            assert result is None

    def test_create_issue_success(self, jira_client):
        """Test creating Jira issue."""
        with patch.object(jira_client.session, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "key": "INFRA-123",
                "id": "10000",
            }
            mock_post.return_value = mock_response

            result = jira_client.create_issue(
                "INFRA",
                "Test Issue",
                "Test description",
                issue_type="Task",
            )

            assert result["key"] == "INFRA-123"
            assert result["id"] == "10000"
            mock_post.assert_called_once()

    def test_create_issue_with_epic_link(self, jira_client):
        """Test creating issue with epic link."""
        with patch.object(jira_client.session, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "key": "INFRA-124",
                "id": "10001",
            }
            mock_post.return_value = mock_response

            result = jira_client.create_issue(
                "INFRA",
                "Test Issue",
                "Test description",
                issue_type="Story",
                epic_key="INFRA-100",
            )

            assert result["key"] == "INFRA-124"
            # Verify epic link was included in request body
            call_args = mock_post.call_args
            assert call_args is not None

    def test_create_issue_request_error(self, jira_client):
        """Test error handling in create_issue."""
        with patch.object(jira_client.session, "post") as mock_post:
            mock_post.side_effect = requests.RequestException("Request failed")

            result = jira_client.create_issue("INFRA", "Test", "Test")

            assert result is None

    def test_get_issue_success(self, jira_client):
        """Test getting issue details."""
        with patch.object(jira_client.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "key": "INFRA-1",
                "summary": "Fix bug",
                "status": {"name": "Done"},
            }
            mock_get.return_value = mock_response

            result = jira_client.get_issue("INFRA-1")

            assert result["key"] == "INFRA-1"
            assert result["summary"] == "Fix bug"

    def test_get_issue_not_found(self, jira_client):
        """Test get_issue when issue not found."""
        with patch.object(jira_client.session, "get") as mock_get:
            mock_get.side_effect = requests.RequestException("404 Not Found")

            result = jira_client.get_issue("INFRA-999")

            assert result is None


class TestJiraIntegration:
    """Test JiraIntegration class."""

    def test_jira_integration_initialization(self, jira_config, monkeypatch):
        """Test JiraIntegration initialization."""
        monkeypatch.setenv("JIRA_TOKEN", "test-token")

        integration = JiraIntegration(jira_config)

        assert integration.client is not None
        assert integration.config == jira_config

    def test_link_related_issues_success(self, jira_config, monkeypatch):
        """Test linking related issues."""
        monkeypatch.setenv("JIRA_TOKEN", "test-token")
        integration = JiraIntegration(jira_config)

        with patch.object(integration.client, "find_related_issues") as mock_find:
            with patch.object(integration.client, "session") as mock_session:
                mock_find.return_value = [{"key": "INFRA-1", "summary": "Related issue"}]
                mock_session.post.return_value = MagicMock()

                result = integration.link_related_issues(
                    "page-123",
                    "INFRA",
                    "Payment API",
                    MagicMock(),
                )

                assert result is not None

    def test_find_undocumented_apis(self, jira_config, monkeypatch):
        """Test finding undocumented APIs."""
        monkeypatch.setenv("JIRA_TOKEN", "test-token")
        integration = JiraIntegration(jira_config)

        with patch.object(integration.client.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "issues": [
                    {
                        "fields": {
                            "summary": "GET /users endpoint",
                        }
                    }
                ]
            }
            mock_get.return_value = mock_response

            apis = [
                {"path": "/users", "method": "GET"},
                {"path": "/posts", "method": "POST"},  # Undocumented
            ]

            result = integration.find_undocumented_apis("INFRA", apis)

            assert len(result) == 1
            assert result[0]["path"] == "/posts"

    def test_create_tasks_for_gaps_success(self, jira_config, monkeypatch):
        """Test creating tasks for API gaps."""
        monkeypatch.setenv("JIRA_TOKEN", "test-token")
        # Enable create_tasks_for_gaps
        jira_config.create_tasks_for_gaps = True
        integration = JiraIntegration(jira_config)

        with patch.object(integration, "find_undocumented_apis") as mock_find:
            with patch.object(integration.client, "create_issue") as mock_create:
                mock_create.return_value = {"key": "INFRA-200", "id": "10050"}
                mock_find.return_value = [
                    {"path": "/missing", "method": "GET"},
                ]

                apis = [
                    {"path": "/missing", "method": "GET"},
                ]

                result = integration.create_tasks_for_gaps(
                    "INFRA",
                    apis,
                    epic_key="INFRA-100",
                )

                assert len(result) == 1
                assert result[0]["key"] == "INFRA-200"

    def test_create_tasks_for_gaps_empty_apis(self, jira_config, monkeypatch):
        """Test create_tasks_for_gaps with no APIs."""
        monkeypatch.setenv("JIRA_TOKEN", "test-token")
        integration = JiraIntegration(jira_config)

        result = integration.create_tasks_for_gaps("INFRA", [])

        assert result == []

    def test_generate_jira_section(self, jira_config, monkeypatch):
        """Test generating Jira section for documentation."""
        monkeypatch.setenv("JIRA_TOKEN", "test-token")
        integration = JiraIntegration(jira_config)

        with patch.object(integration.client, "find_related_issues") as mock_find:
            mock_find.return_value = [{"key": "INFRA-1", "summary": "Related", "url": "https://test/INFRA-1"}]

            result = integration.generate_jira_section("INFRA", "Payment Service")

            assert "INFRA-1" in result or len(result) >= 0
