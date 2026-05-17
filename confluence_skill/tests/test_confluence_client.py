"""Tests for ConfluenceClient."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from confluence_skill.confluence_client import ConfluenceClient, InputValidator
from confluence_skill.models import ConfluenceConfig


@pytest.fixture
def config():
    """Create test Confluence config."""
    return ConfluenceConfig(
        instance_url="https://test.atlassian.net",
        space_key="TEST",
        auth_token_env="TEST_TOKEN",
    )


@pytest.fixture
def client(config, monkeypatch):
    """Create ConfluenceClient with mocked _request."""
    monkeypatch.setenv("TEST_TOKEN", "test-token")
    return ConfluenceClient(config)


class TestConfluenceClientSearch:
    """Test search and find operations."""

    def test_search_pages_returns_list(self, client):
        """Test search_pages returns list of results."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {
                "results": [
                    {"id": "123", "title": "API Docs"},
                    {"id": "456", "title": "Architecture"},
                ]
            }

            results = client.search_pages("TEST", "API")

            assert isinstance(results, list)
            assert len(results) == 2
            assert results[0]["title"] == "API Docs"
            assert results[1]["title"] == "Architecture"
            mock_request.assert_called_once()

    def test_search_pages_empty_query(self, client):
        """Test search with empty query."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {"results": []}

            results = client.search_pages("TEST", "")

            assert results == []

    def test_search_pages_http_error_returns_empty(self, client):
        """Test search returns empty list on HTTP error."""
        with patch.object(client, "_request") as mock_request:
            mock_request.side_effect = requests.HTTPError("API error")

            results = client.search_pages("TEST", "query")

            assert results == []

    def test_find_page_by_title_found(self, client):
        """Test finding page by title when it exists."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {"results": [{"id": "789", "title": "Payment API"}]}

            result = client.find_page_by_title("TEST", "Payment API")

            assert result is not None
            assert result["id"] == "789"
            assert result["title"] == "Payment API"

    def test_find_page_by_title_not_found(self, client):
        """Test finding page when it doesn't exist."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {"results": []}

            result = client.find_page_by_title("TEST", "Nonexistent")

            assert result is None

    def test_find_page_by_title_uses_cache(self, client):
        """Test that find_page_by_title uses cache."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {"results": [{"id": "789", "title": "Payment API"}]}

            # First call
            client.find_page_by_title("TEST", "Payment API")

            # Reset mock to verify it's not called again
            mock_request.reset_mock()

            # Second call should use cache
            result = client.find_page_by_title("TEST", "Payment API")

            # _request should not be called again
            mock_request.assert_not_called()
            assert result["id"] == "789"

    def test_get_space(self, client):
        """Test getting space information."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {
                "id": "space-123",
                "key": "TEST",
                "name": "Test Space",
            }

            result = client.get_space("TEST")

            assert result["key"] == "TEST"
            assert result["name"] == "Test Space"


class TestConfluenceClientPageOperations:
    """Test page creation and modification."""

    def test_create_page_success(self, client):
        """Test creating a page."""
        with patch.object(client, "_request") as mock_request:
            with patch.object(client, "get_space") as mock_get_space:
                mock_get_space.return_value = {"id": "space-123"}
                mock_request.return_value = {
                    "id": "new-page-1",
                    "title": "New Documentation",
                    "version": {"number": 1},
                }

                result = client.create_page(
                    space_key="TEST",
                    title="New Documentation",
                    body="<p>Content</p>",
                )

                assert result["id"] == "new-page-1"
                assert result["title"] == "New Documentation"

    def test_create_page_invalid_title(self, client):
        """Test creating page with invalid title raises error."""
        with pytest.raises(ValueError, match="Invalid page title"):
            client.create_page(
                space_key="TEST",
                title="",  # Empty title
                body="<p>Content</p>",
            )

    def test_create_page_content_too_large(self, client):
        """Test creating page with oversized content."""
        large_content = "<p>" + "x" * (3000 * 1024) + "</p>"
        with pytest.raises(ValueError, match="Content too large"):
            client.create_page(
                space_key="TEST",
                title="Large Page",
                body=large_content,
            )

    def test_create_page_with_labels(self, client):
        """Test creating page with labels."""
        with patch.object(client, "_request") as mock_request:
            with patch.object(client, "get_space") as mock_get_space:
                with patch.object(client, "_add_labels") as mock_add_labels:
                    mock_get_space.return_value = {"id": "space-123"}
                    mock_request.return_value = {"id": "page-1", "title": "Test"}

                    client.create_page(
                        space_key="TEST",
                        title="Test Page",
                        body="<p>Content</p>",
                        labels=["api", "v2"],
                    )

                    mock_add_labels.assert_called_once_with("page-1", ["api", "v2"])

    def test_update_page_success(self, client):
        """Test updating a page."""
        with patch.object(client, "_request") as mock_request:
            with patch.object(client, "get_page") as mock_get_page:
                mock_get_page.return_value = {
                    "id": "page-1",
                    "version": {"number": 1},
                }
                mock_request.return_value = {
                    "id": "page-1",
                    "title": "Updated Doc",
                    "version": {"number": 2},
                }

                result = client.update_page(
                    page_id="page-1",
                    title="Updated Doc",
                    body="<p>New content</p>",
                )

                assert result["version"]["number"] == 2

    def test_update_page_invalid_title(self, client):
        """Test updating page with invalid title."""
        with pytest.raises(ValueError, match="Invalid page title"):
            client.update_page(
                page_id="page-1",
                title="",
                body="<p>Content</p>",
            )

    def test_get_page(self, client):
        """Test retrieving page by ID."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {
                "id": "page-1",
                "title": "Test Page",
                "version": {"number": 5},
            }

            result = client.get_page("page-1")

            assert result["title"] == "Test Page"
            assert result["version"]["number"] == 5

    def test_get_page_with_body(self, client):
        """Test retrieving page with body content."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {
                "id": "page-1",
                "body": {"storage": {"value": "<p>Page content</p>"}},
            }

            result = client.get_page("page-1", include_body=True)

            assert result["body"]["storage"]["value"] == "<p>Page content</p>"

    def test_get_page_content(self, client):
        """Test extracting page content."""
        with patch.object(client, "get_page") as mock_get_page:
            mock_get_page.return_value = {"body": {"storage": {"value": "<p>Page content</p>"}}}

            result = client.get_page_content("page-1")

            assert result == "<p>Page content</p>"

    def test_get_page_content_empty(self, client):
        """Test getting content from page without body."""
        with patch.object(client, "get_page") as mock_get_page:
            mock_get_page.return_value = {}

            result = client.get_page_content("page-1")

            assert result == ""

    def test_delete_page(self, client):
        """Test deleting page."""
        with patch.object(client, "_request") as mock_request:
            result = client.delete_page("page-1")

            assert result is True
            mock_request.assert_called_once()

    def test_add_page_comment(self, client):
        """Test adding comment to page."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {
                "id": "comment-1",
                "body": {"storage": {"value": "<p>Test comment</p>"}},
            }

            result = client.add_page_comment("page-1", "<p>Test comment</p>")

            assert result["id"] == "comment-1"


class TestConfluenceClientPermissions:
    """Test permission checking."""

    def test_check_write_permission_granted(self, client):
        """Test when user has write permission."""
        with patch.object(client, "get_space") as mock_get_space:
            mock_get_space.return_value = {"id": "space-123"}

            result = client.check_write_permission("TEST")

            assert result is True

    def test_check_write_permission_denied(self, client):
        """Test when user lacks write permission."""
        with patch.object(client, "get_space") as mock_get_space:
            error = requests.HTTPError("403 Forbidden")
            error.response = MagicMock()
            error.response.status_code = 403
            mock_get_space.side_effect = error

            result = client.check_write_permission("TEST")

            assert result is False

    def test_check_write_permission_uses_cache(self, client):
        """Test that write permission check uses cache."""
        with patch.object(client, "get_space") as mock_get_space:
            mock_get_space.return_value = {"id": "space-123"}

            # First call
            client.check_write_permission("TEST")

            # Reset to verify cache is used
            mock_get_space.reset_mock()

            # Second call should use cache
            result = client.check_write_permission("TEST")

            mock_get_space.assert_not_called()
            assert result is True

    def test_validate_space(self, client):
        """Test validating space exists."""
        with patch.object(client, "get_space") as mock_get_space:
            mock_get_space.return_value = {"id": "space-123"}

            result = client.validate_space("TEST")

            assert result is True

    def test_validate_space_not_found(self, client):
        """Test space validation when space doesn't exist."""
        with patch.object(client, "get_space") as mock_get_space:
            error = requests.HTTPError("404")
            error.response = MagicMock()
            error.response.status_code = 404
            mock_get_space.side_effect = error

            result = client.validate_space("TEST")

            assert result is False

    def test_is_page_accessible(self, client):
        """Test checking page accessibility."""
        with patch.object(client, "get_page") as mock_get_page:
            mock_get_page.return_value = {"id": "page-1"}

            result = client.is_page_accessible("page-1")

            assert result is True

    def test_is_page_not_accessible(self, client):
        """Test page accessibility when page not found."""
        with patch.object(client, "get_page") as mock_get_page:
            error = requests.HTTPError("404")
            error.response = MagicMock()
            error.response.status_code = 404
            mock_get_page.side_effect = error

            result = client.is_page_accessible("page-1")

            assert result is False


class TestInputValidator:
    """Test InputValidator static methods."""

    def test_validate_space_key_valid(self):
        """Test valid space key."""
        valid, _ = InputValidator.validate_space_key("ENGINEERING")
        assert valid is True

    def test_validate_space_key_empty(self):
        """Test empty space key."""
        valid, msg = InputValidator.validate_space_key("")
        assert valid is False
        assert "empty" in msg.lower()

    def test_validate_space_key_too_long(self):
        """Test space key exceeding limit."""
        valid, _ = InputValidator.validate_space_key("x" * 300)
        assert valid is False

    def test_validate_space_key_invalid_chars(self):
        """Test space key with invalid characters."""
        valid, _ = InputValidator.validate_space_key("INVALID@KEY!")
        assert valid is False

    def test_validate_page_title_valid(self):
        """Test valid page title."""
        valid, _ = InputValidator.validate_page_title("API Documentation")
        assert valid is True

    def test_validate_page_title_empty(self):
        """Test empty page title."""
        valid, _ = InputValidator.validate_page_title("")
        assert valid is False

    def test_validate_page_title_too_short(self):
        """Test title too short."""
        valid, _ = InputValidator.validate_page_title("AB")
        assert valid is False

    def test_validate_page_title_too_long(self):
        """Test title exceeding limit."""
        valid, _ = InputValidator.validate_page_title("x" * 300)
        assert valid is False

    def test_validate_labels_valid(self):
        """Test valid labels."""
        valid, _ = InputValidator.validate_labels(["api", "documentation"])
        assert valid is True

    def test_validate_labels_empty_list(self):
        """Test empty labels list."""
        valid, _ = InputValidator.validate_labels([])
        assert valid is True

    def test_validate_labels_too_many(self):
        """Test too many labels."""
        labels = [f"label{i}" for i in range(1000)]
        valid, _ = InputValidator.validate_labels(labels)
        assert valid is False

    def test_sanitize_content_for_html(self):
        """Test HTML content sanitization."""
        content = "<script>alert('xss')</script><p>Safe</p>"
        result = InputValidator.sanitize_content_for_html(content)
        assert isinstance(result, str)
        # Should remove script tags
        assert "<script>" not in result

    def test_validate_content_size_within_limit(self):
        """Test content within size limit."""
        content = "<p>" + "x" * 1000 + "</p>"
        valid, _ = InputValidator.validate_content_size(content, max_kb=2000)
        assert valid is True

    def test_validate_content_size_exceeds_limit(self):
        """Test content exceeding size limit."""
        content = "<p>" + "x" * (3000 * 1024) + "</p>"
        valid, msg = InputValidator.validate_content_size(content, max_kb=100)
        assert valid is False
        assert "size" in msg.lower()
