"""DevArmor integration tests for Confluence Skill.

Tests the lifecycle hooks, event publishing, and DevArmor compliance.
"""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from devarmor import DevArmorAPI

from confluence_skill.skill import ConfluenceSkill

logger = logging.getLogger(__name__)


class TestConfluenceSkillDevArmorIntegration:
    """Test DevArmor lifecycle integration."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = MagicMock()
        config.confluence = MagicMock()
        config.confluence.instance_url = "https://test.atlassian.net"
        config.confluence.space_key = "TEST"
        config.validate_required_fields.return_value = []
        config.guardrails = MagicMock()
        config.guardrails.enforce_page_nesting = True
        config.guardrails.max_page_depth = 5
        config.guardrails.parent_page_only_for_roots = True
        config.guardrails.aws_documentation_style = False
        config.guardrails.require_approval = False
        config.code_analysis = MagicMock()
        return config

    @pytest.fixture
    def mock_devarmor_api(self):
        """Create mock DevArmorAPI."""
        api = AsyncMock(spec=DevArmorAPI)
        api.event_bus = AsyncMock()
        api.event_bus.publish_skill_installed = AsyncMock()
        api.event_bus.publish_skill_upgraded = AsyncMock()
        api.event_bus.publish_skill_removed = AsyncMock()
        api.event_bus.publish = AsyncMock()
        api.event_bus.unsubscribe = MagicMock(return_value=True)
        return api

    @pytest.fixture
    def skill(self, mock_config, mock_devarmor_api):
        """Create Confluence skill with mocked DevArmor."""

        # Create a test subclass that doesn't require full initialization
        class TestConfluenceSkill(ConfluenceSkill):
            def __init__(self, config, devarmor_api):
                # Skip parent __init__ to avoid expensive initialization
                self.name = "confluence-skill"
                self.version = "2.0.0"
                self.config = config
                self.devarmor_api = devarmor_api
                self.client = AsyncMock()
                self.event_subscriptions = {}
                self._operation_log = []
                self.console = MagicMock()
                # Add logger
                import logging

                self.logger = logging.getLogger(__name__)

        return TestConfluenceSkill(mock_config, mock_devarmor_api)

    @pytest.mark.asyncio
    async def test_on_install_hook(self, skill, mock_devarmor_api):
        """Test on_install lifecycle hook."""
        skill.client.get_spaces = MagicMock(return_value=[{"key": "TEST", "name": "Test"}])

        await skill.on_install(mock_devarmor_api)

        # Verify Confluence connection checked
        skill.client.get_spaces.assert_called_once()

        # Verify event published
        mock_devarmor_api.event_bus.publish_skill_installed.assert_called_once()
        call_args = mock_devarmor_api.event_bus.publish_skill_installed.call_args
        assert call_args[1]["skill_name"] == "confluence-skill"
        assert call_args[1]["version"] == "2.0.0"
        assert call_args[1]["actor"] == "claude"

    @pytest.mark.asyncio
    async def test_on_install_connection_failure(self, skill, mock_devarmor_api):
        """Test on_install fails when Confluence connection fails."""
        skill.client.get_spaces = MagicMock(side_effect=Exception("Connection failed"))

        with pytest.raises(Exception, match="Connection failed"):
            await skill.on_install(mock_devarmor_api)

    @pytest.mark.asyncio
    async def test_on_upgrade_hook(self, skill, mock_devarmor_api):
        """Test on_upgrade lifecycle hook."""
        old_version = "1.4.0"

        await skill.on_upgrade(old_version, mock_devarmor_api)

        # Verify event published
        mock_devarmor_api.event_bus.publish_skill_upgraded.assert_called_once()
        call_args = mock_devarmor_api.event_bus.publish_skill_upgraded.call_args
        assert call_args[1]["skill_name"] == "confluence-skill"
        assert call_args[1]["old_version"] == "1.4.0"
        assert call_args[1]["new_version"] == "2.0.0"
        assert call_args[1]["actor"] == "claude"

    @pytest.mark.asyncio
    async def test_on_remove_hook(self, skill, mock_devarmor_api):
        """Test on_remove lifecycle hook."""
        skill.event_subscriptions = {
            "sub1": "event_type_1",
            "sub2": "event_type_2",
        }

        await skill.on_remove(mock_devarmor_api)

        # Verify subscriptions unsubscribed
        assert mock_devarmor_api.event_bus.unsubscribe.call_count == 2
        mock_devarmor_api.event_bus.unsubscribe.assert_any_call("sub1")
        mock_devarmor_api.event_bus.unsubscribe.assert_any_call("sub2")

        # Verify event published
        mock_devarmor_api.event_bus.publish_skill_removed.assert_called_once()
        call_args = mock_devarmor_api.event_bus.publish_skill_removed.call_args
        assert call_args[1]["skill_name"] == "confluence-skill"
        assert call_args[1]["actor"] == "claude"

    @pytest.mark.asyncio
    async def test_publish_document_created(self, skill, mock_devarmor_api):
        """Test publish_document_created event."""
        page_id = "12345"
        title = "New Documentation"

        await skill.publish_document_created(page_id, title, custom_field="value")

        mock_devarmor_api.event_bus.publish.assert_called_once()
        call_args = mock_devarmor_api.event_bus.publish.call_args
        event = call_args[0][0]
        assert event.skill_name == "confluence-skill"
        assert event.action == "create_page"
        assert event.details["page_id"] == "12345"
        assert event.details["title"] == title
        assert event.details["event_type"] == "document_created"
        assert event.details["custom_field"] == "value"

    @pytest.mark.asyncio
    async def test_publish_document_updated(self, skill, mock_devarmor_api):
        """Test publish_document_updated event."""
        page_id = "12345"
        title = "Updated Documentation"
        changes = {"title": "Updated", "content": "New content"}

        await skill.publish_document_updated(page_id, title, changes)

        mock_devarmor_api.event_bus.publish.assert_called_once()
        call_args = mock_devarmor_api.event_bus.publish.call_args
        event = call_args[0][0]
        assert event.skill_name == "confluence-skill"
        assert event.action == "update_page"
        assert event.details["page_id"] == "12345"
        assert event.details["title"] == title
        assert event.details["changes"] == changes
        assert event.details["event_type"] == "document_updated"

    @pytest.mark.asyncio
    async def test_devarmor_api_initialization(self, mock_config):
        """Test that DevArmorAPI is created if not provided."""

        # Create a test subclass
        class TestConfluenceSkill(ConfluenceSkill):
            def __init__(self, config, devarmor_api):
                self.name = "confluence-skill"
                self.version = "2.0.0"
                self.config = config
                self.devarmor_api = devarmor_api
                self.event_subscriptions = {}
                self.console = MagicMock()

        skill = TestConfluenceSkill(mock_config, None)
        assert skill.devarmor_api is None

    def test_skill_class_attributes(self):
        """Test skill class has required attributes."""
        assert ConfluenceSkill.name == "confluence-skill"
        assert ConfluenceSkill.version == "2.0.0"
        assert ConfluenceSkill.description == "Enterprise-grade Confluence Cloud documentation skill"
        assert ConfluenceSkill.author == "Craig Hoad"

    @pytest.mark.asyncio
    async def test_event_subscriptions_tracking(self, skill, mock_devarmor_api):
        """Test event subscription tracking."""
        skill.event_subscriptions = {"sub1": "policy_violated", "sub2": "ticket_created"}

        await skill.on_remove(mock_devarmor_api)

        # Verify all subscriptions are tracked and cleaned up
        assert len(skill.event_subscriptions) == 2
        assert mock_devarmor_api.event_bus.unsubscribe.call_count == 2

    @pytest.mark.asyncio
    async def test_confluence_connection_details_in_event(self, skill, mock_devarmor_api):
        """Test that Confluence connection details are included in install event."""
        skill.client.get_spaces = MagicMock(return_value=[])
        skill.config.confluence.instance_url = "https://myorg.atlassian.net"
        skill.config.confluence.space_key = "DOCS"

        await skill.on_install(mock_devarmor_api)

        call_args = mock_devarmor_api.event_bus.publish_skill_installed.call_args
        details = call_args[1]["details"]
        assert details["confluence_instance"] == "https://myorg.atlassian.net"
        assert details["space_key"] == "DOCS"

    @pytest.mark.asyncio
    async def test_event_actor_defaults_to_claude(self, skill, mock_devarmor_api):
        """Test that event actor defaults to 'claude'."""
        await skill.publish_document_created("123", "Test")

        call_args = mock_devarmor_api.event_bus.publish.call_args
        event = call_args[0][0]
        assert event.actor == "claude"

    @pytest.mark.asyncio
    async def test_event_actor_custom(self, skill, mock_devarmor_api):
        """Test that custom event actor is respected."""
        await skill.publish_document_created("123", "Test", actor="test_user")

        call_args = mock_devarmor_api.event_bus.publish.call_args
        event = call_args[0][0]
        assert event.actor == "test_user"

    @pytest.mark.asyncio
    async def test_multiple_remove_cleanup(self, skill, mock_devarmor_api):
        """Test cleanup handles empty subscriptions gracefully."""
        skill.event_subscriptions = {}

        await skill.on_remove(mock_devarmor_api)

        # Should not error on empty subscriptions
        assert mock_devarmor_api.event_bus.unsubscribe.call_count == 0
        mock_devarmor_api.event_bus.publish_skill_removed.assert_called_once()

    def test_operation_log_initialized(self, skill):
        """Test operation log is initialized."""
        assert isinstance(skill._operation_log, list)
        assert len(skill._operation_log) == 0

    def test_event_subscriptions_initialized(self, skill):
        """Test event subscriptions dict is initialized."""
        assert isinstance(skill.event_subscriptions, dict)
        assert len(skill.event_subscriptions) == 0


class TestDevArmorEventPublishing:
    """Test event publishing through DevArmor."""

    @pytest.fixture
    def skill_with_mock_devarmor(self):
        """Create skill with comprehensive DevArmor mocking."""
        config = MagicMock()
        config.confluence = MagicMock()
        config.confluence.instance_url = "https://test.atlassian.net"
        config.confluence.space_key = "TEST"
        config.validate_required_fields.return_value = []
        config.guardrails = MagicMock()
        config.guardrails.enforce_page_nesting = True
        config.guardrails.max_page_depth = 5
        config.guardrails.parent_page_only_for_roots = True
        config.guardrails.aws_documentation_style = False
        config.guardrails.require_approval = False
        config.code_analysis = MagicMock()

        devarmor = AsyncMock()
        devarmor.event_bus = AsyncMock()

        # Create a test subclass
        class TestConfluenceSkill(ConfluenceSkill):
            def __init__(self, cfg, dapi):
                self.name = "confluence-skill"
                self.version = "2.0.0"
                self.config = cfg
                self.devarmor_api = dapi
                self.event_subscriptions = {}
                self._operation_log = []
                self.console = MagicMock()
                import logging

                self.logger = logging.getLogger(__name__)

        return TestConfluenceSkill(config, devarmor)

    @pytest.mark.asyncio
    async def test_event_includes_metadata(self, skill_with_mock_devarmor):
        """Test events include full metadata."""
        skill = skill_with_mock_devarmor
        await skill.publish_document_created(
            page_id="456",
            title="API Docs",
            actor="api_user",
            version="1.0",
            tags=["api", "docs"],
        )

        call_args = skill.devarmor_api.event_bus.publish.call_args
        event = call_args[0][0]
        assert event.details["version"] == "1.0"
        assert event.details["tags"] == ["api", "docs"]

    @pytest.mark.asyncio
    async def test_event_publishing_error_handling(self, skill_with_mock_devarmor):
        """Test event publishing handles errors gracefully."""
        skill = skill_with_mock_devarmor
        skill.devarmor_api.event_bus.publish = AsyncMock(side_effect=Exception("Publish failed"))

        with pytest.raises(Exception, match="Publish failed"):
            await skill.publish_document_created("123", "Test")
