"""Confluence documentation skill.

Enterprise-grade documentation generation, management, and Jira integration for Confluence Cloud.

Quick Start:
    from skills.confluence import ConfluenceSkill
    from skills.confluence.models import SkillConfig

    config = SkillConfig.from_yaml(".confluence.yaml")
    skill = ConfluenceSkill(config)

    result = skill.document(
        task="Document the payment API",
        repo_path=".",
        dry_run=False
    )

Features:
    - Document generation from code repositories
    - Multiple documentation templates (API, Architecture, Runbook, ADR, etc.)
    - Confluence Cloud API integration with rate limiting
    - Optional Jira Cloud integration
    - Configuration merging (central + local)
    - Comprehensive input validation
    - MCP (Model Context Protocol) support for Claude

For detailed documentation, see:
    - README.md: User guide and examples
    - docs/ARCHITECTURE.md: Design and architecture
    - docs/SKILL_DEVELOPMENT.md: Development guide for extending skills
"""

from . import mcp
from .confluence_client import ConfluenceClient, InputValidator
from .jira_integration import JiraIntegration
from .models import (
    DocumentGenerationResult,
    DocumentMetadata,
    JiraConfig,
    LocalConfig,
    SkillConfig,
)
from .skill import ConfluenceSkill

__version__ = "1.2.0"

__all__ = [
    # Main skill
    "ConfluenceSkill",
    # Configuration
    "SkillConfig",
    "LocalConfig",
    "JiraConfig",
    # Results and metadata
    "DocumentGenerationResult",
    "DocumentMetadata",
    # API client
    "ConfluenceClient",
    "InputValidator",
    # Jira integration
    "JiraIntegration",
    # MCP server
    "mcp",
]
