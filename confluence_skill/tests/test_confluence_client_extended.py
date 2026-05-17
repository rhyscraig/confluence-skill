"""Extended tests for ConfluenceClient covering error paths and edge cases."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from confluence_skill.confluence_client import ConfluenceClient, InputValidator, RateLimiter
from confluence_skill.models import ConfluenceConfig


@pytest.fixture
def confluence_config():
    """Create test Confluence config."""
    return ConfluenceConfig(
        instance_url="https://test.atlassian.net",
        space_key="TEST",
        auth_token_env="TEST_CONFLUENCE_TOKEN",
    )


@pytest.fixture
def client(confluence_config, monkeypatch):
    """Create ConfluenceClient."""
    monkeypatch.setenv("TEST_CONFLUENCE_TOKEN", "test-token")
    return ConfluenceClient(confluence_config)


class TestRateLimiter:
    """Test RateLimiter functionality."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(60)
        assert limiter.rate_per_minute == 60
        assert limiter.min_interval == 1.0

    def test_rate_limiter_wait_no_delay_on_first_call(self):
        """Test that first call doesn't wait."""
        limiter = RateLimiter(60)
        import time

        start = time.time()
        limiter.wait()
        elapsed = time.time() - start
        # Should be nearly instant (< 100ms)
        assert elapsed < 0.1

    def test_rate_limiter_enforces_minimum_interval(self):
        """Test that rate limiter enforces minimum interval."""
        limiter = RateLimiter(2)  # 2 per minute = 30 second interval
        import time

        limiter.wait()
        start = time.time()
        limiter.wait()
        elapsed = time.time() - start
        # Should wait at least 29 seconds (with some tolerance)
        assert elapsed >= 29


class TestConfluenceClientInitialization:
    """Test ConfluenceClient initialization."""

    def test_init_missing_auth_token(self, confluence_config):
        """Test that client raises when auth token missing."""
        with pytest.raises(ValueError, match="Set TEST_CONFLUENCE_TOKEN"):
            ConfluenceClient(confluence_config)

    def test_init_with_valid_token(self, client):
        """Test successful initialization with valid token."""
        assert client.config is not None
        assert client.auth_token == "test-token"
        assert client.session is not None
        assert client.rate_limiter is not None

    def test_session_has_auth_headers(self, client):
        """Test that session has proper auth headers."""
        assert "Authorization" in client.session.headers
        assert "Bearer test-token" in client.session.headers["Authorization"]
        assert "Content-Type" in client.session.headers
        assert "User-Agent" in client.session.headers


class TestAPIRequestHandling:
    """Test API request method and error handling."""

    def test_request_success(self, client):
        """Test successful API request."""
        with patch.object(client.session, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.json.return_value = {"id": "123", "title": "Test"}
            mock_request.return_value = mock_response

            result = client._request("GET", "pages/123")

            assert result == {"id": "123", "title": "Test"}
            mock_request.assert_called_once()

    def test_request_empty_response(self, client):
        """Test API request with empty response."""
        with patch.object(client.session, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.content = b""
            mock_response.json.return_value = {}
            mock_request.return_value = mock_response

            result = client._request("GET", "pages/123")

            assert result == {}

    def test_request_http_error_with_status_and_reason(self, client):
        """Test API request with HTTP error."""
        with patch.object(client.session, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.reason = "Not Found"
            mock_response.text = "Resource not found"
            error = requests.HTTPError()
            error.response = mock_response
            mock_request.side_effect = error

            with pytest.raises(requests.HTTPError):
                client._request("GET", "pages/nonexistent")

    def test_request_http_error_without_text(self, client):
        """Test API request with HTTP error but no response text."""
        with patch.object(client.session, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.reason = "Internal Server Error"
            mock_response.text = ""
            error = requests.HTTPError()
            error.response = mock_response
            mock_request.side_effect = error

            with pytest.raises(requests.HTTPError):
                client._request("GET", "pages/123")

    def test_request_respects_timeout(self, client):
        """Test that requests respect configured timeout."""
        with patch.object(client.session, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.json.return_value = {}
            mock_request.return_value = mock_response

            client._request("GET", "pages/123", params={"limit": 10})

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["timeout"] == client.config.api_timeout_seconds


class TestCreatePageValidation:
    """Test page creation with validation."""

    def test_create_page_invalid_space_key(self, client):
        """Test create_page with invalid space key."""
        with pytest.raises(ValueError, match="Invalid space key"):
            client.create_page(
                space_key="INVALID@KEY",
                title="Test Page",
                body="Test content",
            )

    def test_create_page_invalid_title_empty(self, client):
        """Test create_page with empty title."""
        with pytest.raises(ValueError, match="Invalid page title"):
            client.create_page(
                space_key="TEST",
                title="",
                body="Test content",
            )

    def test_create_page_invalid_title_too_short(self, client):
        """Test create_page with title too short."""
        with pytest.raises(ValueError, match="Invalid page title"):
            client.create_page(
                space_key="TEST",
                title="ab",
                body="Test content",
            )

    def test_create_page_invalid_content_size(self, client):
        """Test create_page with content exceeding max size."""
        with pytest.raises(ValueError, match="Content too large"):
            large_content = "x" * (2001 * 1024)  # 2001 KB
            client.create_page(
                space_key="TEST",
                title="Test Page",
                body=large_content,
            )

    def test_create_page_invalid_labels(self, client):
        """Test create_page with invalid labels."""
        with pytest.raises(ValueError, match="Invalid labels"):
            client.create_page(
                space_key="TEST",
                title="Test Page",
                body="Test content",
                labels="not_a_list",
            )

    def test_create_page_success_with_labels(self, client):
        """Test successful page creation with labels."""
        with patch.object(client, "get_space") as mock_get_space:
            with patch.object(client, "_request") as mock_request:
                with patch.object(client, "_add_labels") as mock_add_labels:
                    mock_get_space.return_value = {"id": "space-123"}
                    mock_request.return_value = {"id": "page-123", "title": "Test"}

                    result = client.create_page(
                        space_key="TEST",
                        title="Test Page",
                        body="Test content",
                        labels=["api", "v1"],
                    )

                    assert result["id"] == "page-123"
                    mock_add_labels.assert_called_once_with("page-123", ["api", "v1"])

    def test_create_page_with_parent_id(self, client):
        """Test page creation with parent page."""
        with patch.object(client, "get_space") as mock_get_space:
            with patch.object(client, "_request") as mock_request:
                mock_get_space.return_value = {"id": "space-123"}
                mock_request.return_value = {"id": "page-123", "title": "Test"}

                client.create_page(
                    space_key="TEST",
                    title="Test Page",
                    body="Test content",
                    parent_page_id="parent-456",
                )

                # Verify parent ID was included in request
                call_args = mock_request.call_args
                assert call_args[1]["data"]["parentId"] == "parent-456"


class TestUpdatePageValidation:
    """Test page update with validation."""

    def test_update_page_invalid_title(self, client):
        """Test update_page with invalid title."""
        with pytest.raises(ValueError, match="Invalid page title"):
            client.update_page(
                page_id="page-123",
                title="ab",  # Too short
                body="Test content",
            )

    def test_update_page_invalid_content_size(self, client):
        """Test update_page with oversized content."""
        with pytest.raises(ValueError, match="Content too large"):
            large_content = "x" * (2001 * 1024)
            client.update_page(
                page_id="page-123",
                title="Test Page",
                body=large_content,
            )

    def test_update_page_invalid_labels(self, client):
        """Test update_page with invalid labels."""
        with pytest.raises(ValueError, match="Invalid labels"):
            client.update_page(
                page_id="page-123",
                title="Test Page",
                body="Test content",
                labels=["valid", "x" * 101],  # One label too long
            )

    def test_update_page_success_with_labels(self, client):
        """Test successful page update with labels."""
        with patch.object(client, "get_page") as mock_get:
            with patch.object(client, "_request") as mock_request:
                with patch.object(client, "_add_labels") as mock_add_labels:
                    mock_get.return_value = {"version": {"number": 1}}
                    mock_request.return_value = {"id": "page-123", "title": "Updated"}

                    result = client.update_page(
                        page_id="page-123",
                        title="Updated Page",
                        body="New content",
                        labels=["updated"],
                    )

                    assert result["id"] == "page-123"
                    mock_add_labels.assert_called_once_with("page-123", ["updated"])


class TestAddLabelsEdgeCases:
    """Test _add_labels error handling."""

    def test_add_labels_empty_list(self, client):
        """Test _add_labels with empty label list."""
        with patch.object(client, "_request") as mock_request:
            client._add_labels("page-123", [])

            # Should return early without calling _request
            mock_request.assert_not_called()

    def test_add_labels_invalid_labels(self, client):
        """Test _add_labels with invalid labels."""
        with pytest.raises(ValueError, match="Invalid labels"):
            client._add_labels("page-123", ["valid", "x" * 101])

    def test_add_labels_request_error(self, client):
        """Test _add_labels when label request fails."""
        with patch.object(client, "_request") as mock_request:
            mock_request.side_effect = requests.HTTPError()

            # Should not raise, but print warning
            client._add_labels("page-123", ["api"])

            mock_request.assert_called_once()


class TestBulkAddLabels:
    """Test bulk label operations."""

    def test_bulk_add_labels_invalid_labels(self, client):
        """Test bulk_add_labels with invalid labels."""
        with pytest.raises(ValueError, match="Invalid labels"):
            client.bulk_add_labels(
                page_ids=["page-1", "page-2"],
                labels=["x" * 101],  # Too long
            )

    def test_bulk_add_labels_success(self, client):
        """Test successful bulk label addition."""
        with patch.object(client, "_add_labels") as mock_add:
            mock_add.return_value = None

            result = client.bulk_add_labels(
                page_ids=["page-1", "page-2"],
                labels=["api", "v1"],
            )

            # 2 pages x 2 labels = 4 operations
            assert result["success"] == 4
            assert result["failed"] == 0

    def test_bulk_add_labels_with_errors(self, client):
        """Test bulk_add_labels with some failures."""
        with patch.object(client, "_add_labels") as mock_add:
            call_count = 0

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise ValueError("Label add failed")

            mock_add.side_effect = side_effect

            result = client.bulk_add_labels(
                page_ids=["page-1"],
                labels=["api", "v1"],
            )

            assert result["success"] == 1
            assert result["failed"] == 1
            assert len(result["errors"]) == 1


class TestSetPageProperties:
    """Test page property operations."""

    def test_set_page_properties_success(self, client):
        """Test successful property setting."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {}

            result = client.set_page_properties(
                page_id="page-123",
                properties={"key": "value"},
            )

            assert result is True

    def test_set_page_properties_error(self, client):
        """Test property setting with error."""
        with patch.object(client, "_request") as mock_request:
            mock_request.side_effect = requests.HTTPError()

            result = client.set_page_properties(
                page_id="page-123",
                properties={"key": "value"},
            )

            assert result is False


class TestPageHash:
    """Test page hash generation."""

    def test_get_page_hash(self, client):
        """Test page hash generation."""
        with patch.object(client, "get_page_content") as mock_get:
            mock_get.return_value = "Test content"

            hash_val = client.get_page_hash("page-123")

            assert isinstance(hash_val, str)
            assert len(hash_val) == 32  # MD5 hash length


class TestValidateSpace:
    """Test space validation."""

    def test_validate_space_exists(self, client):
        """Test space validation when space exists."""
        with patch.object(client, "get_space") as mock_get:
            mock_get.return_value = {"id": "space-123"}

            result = client.validate_space("TEST")

            assert result is True

    def test_validate_space_not_found(self, client):
        """Test space validation when space doesn't exist."""
        with patch.object(client, "get_space") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            error = requests.HTTPError()
            error.response = mock_response
            mock_get.side_effect = error

            result = client.validate_space("NONEXISTENT")

            assert result is False

    def test_validate_space_permission_denied(self, client):
        """Test space validation when permission denied."""
        with patch.object(client, "get_space") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 403
            error = requests.HTTPError()
            error.response = mock_response
            mock_get.side_effect = error

            result = client.validate_space("TEST")

            assert result is False

    def test_validate_space_other_error(self, client):
        """Test space validation with unexpected error."""
        with patch.object(client, "get_space") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            error = requests.HTTPError()
            error.response = mock_response
            mock_get.side_effect = error

            with pytest.raises(requests.HTTPError):
                client.validate_space("TEST")


class TestListChildPages:
    """Test child page listing."""

    def test_list_child_pages_success(self, client):
        """Test successful child page listing."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {
                "results": [
                    {"id": "child-1", "title": "Child 1"},
                    {"id": "child-2", "title": "Child 2"},
                ]
            }

            result = client.list_child_pages("parent-123")

            assert len(result) == 2
            assert result[0]["id"] == "child-1"

    def test_list_child_pages_empty(self, client):
        """Test child page listing with no children."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {"results": []}

            result = client.list_child_pages("parent-123")

            assert result == []

    def test_list_child_pages_list_response(self, client):
        """Test child page listing when response is a list."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = [{"id": "child-1", "title": "Child 1"}]

            result = client.list_child_pages("parent-123")

            assert len(result) == 1

    def test_list_child_pages_not_found(self, client):
        """Test child page listing when parent not found."""
        with patch.object(client, "_request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 404
            error = requests.HTTPError()
            error.response = mock_response
            mock_request.side_effect = error

            result = client.list_child_pages("nonexistent-parent")

            assert result == []

    def test_list_child_pages_other_error(self, client):
        """Test child page listing with unexpected error."""
        with patch.object(client, "_request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 500
            error = requests.HTTPError()
            error.response = mock_response
            mock_request.side_effect = error

            with pytest.raises(requests.HTTPError):
                client.list_child_pages("parent-123")


class TestArchivePage:
    """Test page archival."""

    def test_archive_page_success(self, client):
        """Test successful page archival."""
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = {}

            result = client.archive_page("page-123")

            assert result is True

    def test_archive_page_error(self, client):
        """Test page archival with error."""
        with patch.object(client, "_request") as mock_request:
            mock_request.side_effect = requests.HTTPError()

            result = client.archive_page("page-123")

            assert result is False


class TestIsPageAccessible:
    """Test page accessibility check."""

    def test_is_page_accessible_true(self, client):
        """Test page accessibility when accessible."""
        with patch.object(client, "get_page") as mock_get:
            mock_get.return_value = {"id": "page-123"}

            result = client.is_page_accessible("page-123")

            assert result is True

    def test_is_page_accessible_not_found(self, client):
        """Test page accessibility when page not found."""
        with patch.object(client, "get_page") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            error = requests.HTTPError()
            error.response = mock_response
            mock_get.side_effect = error

            result = client.is_page_accessible("nonexistent")

            assert result is False

    def test_is_page_accessible_forbidden(self, client):
        """Test page accessibility when forbidden."""
        with patch.object(client, "get_page") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 403
            error = requests.HTTPError()
            error.response = mock_response
            mock_get.side_effect = error

            result = client.is_page_accessible("page-123")

            assert result is False

    def test_is_page_accessible_other_error(self, client):
        """Test page accessibility with unexpected error."""
        with patch.object(client, "get_page") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            error = requests.HTTPError()
            error.response = mock_response
            mock_get.side_effect = error

            with pytest.raises(requests.HTTPError):
                client.is_page_accessible("page-123")


class TestCheckWritePermission:
    """Test write permission checking."""

    def test_check_write_permission_allowed(self, client):
        """Test write permission when allowed."""
        with patch.object(client, "get_space") as mock_get:
            mock_get.return_value = {"id": "space-123"}

            result = client.check_write_permission("TEST")

            assert result is True
            # Cache should be populated
            assert "TEST" in client._permission_cache

    def test_check_write_permission_denied(self, client):
        """Test write permission when denied."""
        with patch.object(client, "get_space") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 403
            error = requests.HTTPError()
            error.response = mock_response
            mock_get.side_effect = error

            result = client.check_write_permission("TEST")

            assert result is False
            assert client._permission_cache["TEST"] is False

    def test_check_write_permission_cached(self, client):
        """Test write permission from cache."""
        client._permission_cache["TEST"] = True

        with patch.object(client, "get_space") as mock_get:
            result = client.check_write_permission("TEST")

            assert result is True
            # Should not call get_space due to cache
            mock_get.assert_not_called()

    def test_check_write_permission_other_error(self, client):
        """Test write permission with unexpected error."""
        with patch.object(client, "get_space") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            error = requests.HTTPError()
            error.response = mock_response
            mock_get.side_effect = error

            with pytest.raises(requests.HTTPError):
                client.check_write_permission("TEST")


class TestInputValidator:
    """Test InputValidator edge cases."""

    def test_validate_space_key_empty(self):
        """Test space key validation with empty string."""
        valid, error = InputValidator.validate_space_key("")
        assert valid is False
        assert "empty" in error.lower()

    def test_validate_space_key_too_long(self):
        """Test space key validation with too long key."""
        valid, error = InputValidator.validate_space_key("X" * 256)
        assert valid is False
        assert "exceed" in error.lower()

    def test_validate_space_key_invalid_chars(self):
        """Test space key validation with invalid characters."""
        valid, error = InputValidator.validate_space_key("TEST@KEY")
        assert valid is False
        assert "alphanumeric" in error.lower()

    def test_validate_space_key_valid(self):
        """Test space key validation with valid key."""
        valid, error = InputValidator.validate_space_key("TEST-KEY_123")
        assert valid is True
        assert error == ""

    def test_validate_page_title_empty(self):
        """Test page title validation with empty string."""
        valid, _error = InputValidator.validate_page_title("")
        assert valid is False

    def test_validate_page_title_whitespace_only(self):
        """Test page title validation with whitespace only."""
        valid, _error = InputValidator.validate_page_title("   ")
        assert valid is False

    def test_validate_page_title_too_long(self):
        """Test page title validation with too long title."""
        valid, error = InputValidator.validate_page_title("X" * 256)
        assert valid is False
        assert "exceed" in error.lower()

    def test_validate_page_title_too_short(self):
        """Test page title validation with too short title."""
        valid, error = InputValidator.validate_page_title("ab")
        assert valid is False
        assert "3 characters" in error

    def test_validate_page_title_valid(self):
        """Test page title validation with valid title."""
        valid, _error = InputValidator.validate_page_title("Valid Title")
        assert valid is True

    def test_validate_labels_not_list(self):
        """Test labels validation with non-list value."""
        valid, error = InputValidator.validate_labels("not_a_list")
        assert valid is False
        assert "list" in error.lower()

    def test_validate_labels_too_many(self):
        """Test labels validation with too many labels."""
        labels = [f"label-{i}" for i in range(51)]
        valid, error = InputValidator.validate_labels(labels)
        assert valid is False
        assert "50" in error

    def test_validate_labels_empty_label(self):
        """Test labels validation with empty label."""
        valid, error = InputValidator.validate_labels(["valid", ""])
        assert valid is False
        assert "empty" in error.lower()

    def test_validate_labels_label_too_long(self):
        """Test labels validation with label too long."""
        valid, error = InputValidator.validate_labels(["valid", "x" * 101])
        assert valid is False
        assert "100" in error

    def test_validate_labels_valid(self):
        """Test labels validation with valid labels."""
        valid, _error = InputValidator.validate_labels(["api", "v1", "backend"])
        assert valid is True

    def test_validate_content_size_valid(self):
        """Test content size validation with valid size."""
        content = "x" * 1000
        valid, _error = InputValidator.validate_content_size(content)
        assert valid is True

    def test_validate_content_size_exceeds_limit(self):
        """Test content size validation exceeding limit."""
        content = "x" * (2001 * 1024)
        valid, error = InputValidator.validate_content_size(content)
        assert valid is False
        assert "exceed" in error.lower()

    def test_sanitize_content_for_html(self):
        """Test HTML content sanitization."""
        content = "<script>alert('xss')</script>"
        sanitized = InputValidator.sanitize_content_for_html(content)
        assert "<" not in sanitized
        assert "&lt;" in sanitized
