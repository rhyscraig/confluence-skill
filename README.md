# Confluence Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/Coverage->85%25-brightgreen.svg)](#testing)
[![Code Style: Black](https://img.shields.io/badge/Code%20Style-Black-000000.svg)](https://github.com/psf/black)

Enterprise-grade Confluence Cloud documentation skill for Claude with optional Jira integration. Generate, manage, and maintain documentation at scale with full type safety, input validation, and MCP support.

## Features

- **Document Generation**: Auto-generate documentation from code repositories using multiple templates
- **Multiple Templates**: API, Architecture, ADR, Runbook, Feature, Infrastructure, Troubleshooting, and Custom templates
- **Confluence Cloud API v2**: Full support for modern Confluence Cloud with HTML storage format
- **Jira Integration**: Optional issue linking and task creation for documentation gaps
- **Configuration Merging**: Hierarchical config (default → central → local) for flexible deployment
- **Input Validation**: Comprehensive validation at all API boundaries
- **Rate Limiting**: Token bucket algorithm (60 req/min) with automatic backoff
- **Caching**: Smart caching with invalidation for pages and permissions
- **MCP Support**: Model Context Protocol integration for Claude Desktop (`/confluence` command)
- **Production Ready**: >85% test coverage, full type hints, comprehensive error handling

## Quick Start

### Installation

```bash
pip install confluence-skill
# or with poetry:
poetry add confluence-skill
```

### Basic Usage

```python
from confluence_skill import ConfluenceSkill
from confluence_skill.models import SkillConfig

# Load configuration from .confluence.yaml
config = SkillConfig.from_yaml(".confluence.yaml")
skill = ConfluenceSkill(config)

# Generate documentation (dry-run mode)
result = skill.document(
    task="Document the payment API",
    repo_path=".",
    dry_run=True  # Preview changes
)

print(result.summary)
```

### Configuration

Create a `.confluence.yaml` file in your repository:

```yaml
documentation:
  space_key: "ENGINEERING"
  auto_title: true
  metadata:
    owner: "platform-team"
    audience: "developers"

jira:
  enabled: true
  instance_url: "https://your-org.atlassian.net"
  auth_token_env: "JIRA_TOKEN"
  default_project: "INFRA"
  auto_link_related: true
  create_tasks_for_gaps: true
```

### Environment Variables

Required:
- `CONFLUENCE_TOKEN`: Confluence Cloud API token

Optional:
- `JIRA_TOKEN`: Jira Cloud API token (if Jira integration enabled)

## Documentation Templates

The skill supports multiple documentation templates:

| Template | Use Case |
|----------|----------|
| **api** | REST/GraphQL endpoint documentation |
| **architecture** | System design and architecture diagrams |
| **adr** | Architecture Decision Records |
| **runbook** | Operational procedures and troubleshooting |
| **feature** | Feature specifications and requirements |
| **infrastructure** | Infrastructure setup and deployment guides |
| **troubleshooting** | Common issues and resolutions |
| **custom** | Custom template (provide your own) |

## Core Capabilities

### Document Generation
Analyze code repositories and automatically generate comprehensive documentation:

```python
result = skill.document(
    task="Document all payment processing APIs",
    repo_path="./backend",
    template="api",
    dry_run=False  # Commit changes to Confluence
)
```

### Page Management
Search, list, and manage documentation pages:

```python
# Search pages
pages = skill.search_pages(query="payment API")

# List page hierarchy
hierarchy = skill.list_page_hierarchy(parent_title="Backend APIs")

# Archive deprecated pages
skill.archive_page(page_id="123456")
```

### Bulk Operations
Efficiently manage multiple pages:

```python
# Bulk label pages
skill.bulk_label_pages(
    page_ids=["123", "456", "789"],
    labels=["api", "v2", "production"]
)
```

## Architecture

The skill is built with clean separation of concerns:

- **ConfluenceClient**: Low-level API interaction with rate limiting and caching
- **ConfluenceSkill**: High-level workflow orchestration
- **CodeScanner**: Repository analysis and code extraction
- **DocumentGenerators**: Template-based document generation
- **Guardrails**: Safety validation and content checks
- **JiraIntegration**: Optional Jira integration layer
- **MCP Server**: Model Context Protocol integration for Claude

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Development Guide

To extend this skill or use it as a template for new skills, see [docs/SKILL_DEVELOPMENT.md](docs/SKILL_DEVELOPMENT.md).

Key principles:
1. Clear separation of concerns
2. Input validation at boundaries
3. Configuration merging
4. Graceful degradation
5. Fail-fast pattern

## Testing

Run the comprehensive test suite:

```bash
# All tests
pytest

# With coverage report
pytest --cov=. --cov-report=html

# Specific test category
pytest -m unit
pytest -m integration
```

Test coverage: **>85%** across 71 tests

## Error Handling

The skill provides clear, actionable error messages:

```python
try:
    result = skill.document(task="...", repo_path=".", dry_run=False)
except ValueError as e:
    print(f"Validation error: {e}")
except RuntimeError as e:
    print(f"API error: {e}")
```

All errors include:
- **What went wrong**: Clear description
- **Why it happened**: Root cause
- **How to fix it**: Actionable guidance

## Performance

- **Rate Limiting**: 60 requests/minute (Confluence Cloud limit)
- **Caching**: Smart caching reduces repeated API calls by 80%+
- **Batch Operations**: Bulk actions reduce API overhead
- **Timeouts**: Configurable per operation with sensible defaults

## MCP Integration

Use with Claude Desktop for seamless integration:

1. Install `confluence-skill` via pip
2. Add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "confluence": {
      "command": "python",
      "args": ["-m", "confluence_skill.mcp"]
    }
  }
}
```

3. Use in Claude: `/confluence`

## Security

- ✅ All secrets stored in environment variables
- ✅ No credentials in code or config files
- ✅ Input validation on all API boundaries
- ✅ Type hints throughout (mypy strict mode)
- ✅ Security audit via `bandit` and `pip-audit`

## Contributing

This is a production-exemplar skill. To contribute:

1. Follow the architecture patterns in [docs/SKILL_DEVELOPMENT.md](docs/SKILL_DEVELOPMENT.md)
2. Maintain >85% test coverage
3. Keep type hints and docstrings up-to-date
4. Run quality checks: `ruff check`, `mypy`, `black`

## License

MIT License - see [LICENSE](LICENSE) for details

## Support

- 📖 [Architecture Guide](docs/ARCHITECTURE.md)
- 🛠️ [Skill Development Guide](docs/SKILL_DEVELOPMENT.md)
- 💡 [Examples](examples/)
- ⚙️ [Configuration Schema](config.schema.json)

## Status

**Version**: 1.2.0  
**Status**: Production Ready  
**Maintained**: Yes  
**Last Updated**: April 2026

---

Built with ❤️ for enterprise documentation at scale.
