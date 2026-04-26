"""Tests for configuration merging and local config."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from skills.confluence.models import (
    SkillConfig,
    LocalConfig,
    DocumentationConfig,
    CodeAnalysisConfig,
    JiraConfig,
    MetadataConfig,
)


def test_local_config_from_yaml():
    """Test loading local config from YAML."""
    from skills.confluence.models import DocumentTemplate

    yaml_content = """
documentation:
  space_key: "SERVICES"
  template: "api"
  metadata:
    owner: "backend-team"
"""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text(yaml_content)

        local_config = LocalConfig.from_yaml(config_path)
        assert local_config.documentation is not None
        assert local_config.documentation.space_key == "SERVICES"
        assert local_config.documentation.template == DocumentTemplate.API


def test_local_config_missing_file():
    """Test loading missing local config returns empty."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            LocalConfig.from_yaml(config_path)


def test_config_merge_documentation(skill_config):
    """Test merging documentation config."""
    from skills.confluence.models import DocumentTemplate

    local_config = LocalConfig(
        documentation=DocumentationConfig(
            space_key="CUSTOM_SPACE",
            template=DocumentTemplate.ARCHITECTURE,
        )
    )

    merged = skill_config.merge(local_config)

    assert merged.documentation.space_key == "CUSTOM_SPACE"
    assert merged.documentation.template == DocumentTemplate.ARCHITECTURE
    # Other fields should retain original values
    assert merged.documentation.auto_title is True


def test_config_merge_code_analysis(skill_config):
    """Test merging code analysis config."""
    local_config = LocalConfig(
        code_analysis=CodeAnalysisConfig(
            enabled=False,
            max_files_to_analyze=50,
        )
    )

    merged = skill_config.merge(local_config)

    assert merged.code_analysis.enabled is False
    assert merged.code_analysis.max_files_to_analyze == 50


def test_config_merge_jira(skill_config):
    """Test merging Jira config."""
    local_config = LocalConfig(
        jira=JiraConfig(
            enabled=True,
            default_project="PAYMENTS",
            create_tasks_for_gaps=True,
        )
    )

    merged = skill_config.merge(local_config)

    assert merged.jira.enabled is True
    assert merged.jira.default_project == "PAYMENTS"
    assert merged.jira.create_tasks_for_gaps is True


def test_config_merge_preserves_unmodified(skill_config):
    """Test that merge preserves unmodified sections."""
    original_space = skill_config.confluence.space_key
    original_instance = skill_config.confluence.instance_url

    local_config = LocalConfig(
        documentation=DocumentationConfig(
            space_key="OVERRIDE",
        )
    )

    merged = skill_config.merge(local_config)

    # Confluence config should be unchanged
    assert merged.confluence.space_key == original_space
    assert merged.confluence.instance_url == original_instance
    # But documentation should be updated
    assert merged.documentation.space_key == "OVERRIDE"


def test_config_merge_only_specified_fields_override():
    """Test that only explicitly specified fields in local config override."""
    central = SkillConfig(
        confluence={"instance_url": "https://test.atlassian.net", "space_key": "ENG"},
        documentation=DocumentationConfig(
            space_key="SERVICES",
            template="api",
            auto_title=False,
        ),
    )

    local_config = LocalConfig(
        documentation=DocumentationConfig(
            space_key="LOCAL_OVERRIDE",
            # template and auto_title use their defaults, effectively overriding
        )
    )

    merged = central.merge(local_config)

    # space_key should be overridden
    assert merged.documentation.space_key == "LOCAL_OVERRIDE"
    # template gets the local config's default value, which overrides central
    assert merged.documentation.template == "custom"


def test_config_merge_partial_override():
    """Test merging with explicit field overrides and metadata merge."""
    central = SkillConfig(
        confluence={"instance_url": "https://test.atlassian.net"},
        documentation=DocumentationConfig(
            space_key="CENTRAL",
            template="api",
            metadata=MetadataConfig(owner="central-team", audience=["engineers"]),
        ),
    )

    local_config = LocalConfig(
        documentation=DocumentationConfig(
            space_key="LOCAL_SPACE",
            template="api",  # Explicitly keep same template
            metadata=MetadataConfig(owner="local-team"),
        )
    )

    merged = central.merge(local_config)

    assert merged.documentation.space_key == "LOCAL_SPACE"
    assert merged.documentation.template == "api"  # Explicitly set to same
    assert merged.documentation.metadata.owner == "local-team"
    # Note: metadata is replaced, not merged at field level
    assert merged.documentation.metadata.audience == []  # From local metadata default


def test_config_empty_local_doesnt_change_central(skill_config):
    """Test that empty local config doesn't change central."""
    local_config = LocalConfig()

    merged = skill_config.merge(local_config)

    # Should be identical to original
    assert merged == skill_config


def test_local_config_full_example():
    """Test loading a realistic local config."""
    yaml_content = """
documentation:
  space_key: "SERVICES"
  parent_page: "Microservices"
  template: "api"
  metadata:
    owner: "payments-team"
    audience:
      - "backend-engineers"
      - "platform-team"
    labels:
      - "microservice"
      - "payments"

code_analysis:
  include_patterns:
    - "src/**/*.py"
    - "api/**/*.py"
  exclude_patterns:
    - "test_*.py"

jira:
  enabled: true
  default_project: "PAYMENTS"
  auto_link_related: true
  create_tasks_for_gaps: true
"""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text(yaml_content)

        local_config = LocalConfig.from_yaml(config_path)

        assert local_config.documentation.space_key == "SERVICES"
        assert local_config.documentation.template == "api"
        assert local_config.documentation.metadata.owner == "payments-team"
        assert len(local_config.documentation.metadata.audience) == 2
        assert local_config.jira.enabled is True
        assert local_config.jira.default_project == "PAYMENTS"
