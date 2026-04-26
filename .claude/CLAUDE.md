# Confluence Skill for Claude

## What This Is

A production-grade Confluence Cloud documentation skill that enables Claude to:
- Generate documentation from code repositories
- Manage Confluence pages at scale
- Link to Jira issues
- Use multiple documentation templates
- Run as an MCP (Model Context Protocol) server for Claude Desktop

## Installation

### Option 1: From PyPI (When Published)

```bash
pip install confluence-skill
```

### Option 2: From GitHub (Development)

```bash
pip install git+https://github.com/rhyscraig/confluence-skill.git
# Or in editable mode:
git clone https://github.com/rhyscraig/confluence-skill.git
cd confluence-skill
pip install -e .
```

### Option 3: Local Development

```bash
git clone https://github.com/rhyscraig/confluence-skill.git
cd confluence-skill
pip install -e .
poetry install  # if using poetry
```

## Configuration

Create a `.confluence.yaml` file:

```yaml
confluence:
  instance_url: "https://your-org.atlassian.net"
  space_key: "ENGINEERING"
  auth_token_env: "CONFLUENCE_TOKEN"

jira:
  enabled: true
  instance_url: "https://your-org.atlassian.net"
  auth_token_env: "JIRA_TOKEN"
  default_project: "INFRA"

documentation:
  metadata:
    owner: "platform-team"
    audience: "engineers"
```

## Environment Variables

Required:
- `CONFLUENCE_TOKEN`: API token from https://id.atlassian.com/manage-profile/security/api-tokens

Optional:
- `JIRA_TOKEN`: API token (if Jira integration enabled)

## Usage with Claude

### As an MCP (Recommended)

1. **Add to `.claude/settings.json`:**

```json
{
  "mcpServers": {
    "confluence": {
      "command": "python3",
      "args": ["-m", "confluence_skill.mcp"]
    }
  }
}
```

2. **In Claude:** Use `/confluence` command
   - `/confluence document "Write API documentation" repo_path="." dry_run=true`
   - `/confluence search "payment API"`
   - `/confluence archive "Old Page Title"`

### Programmatically

```python
from confluence_skill import ConfluenceSkill
from confluence_skill.models import SkillConfig

# Load config
config = SkillConfig.from_yaml(".confluence.yaml")
skill = ConfluenceSkill(config)

# Generate documentation
result = skill.document(
    task="Document the payment API",
    repo_path=".",
    dry_run=True  # Preview first
)

print(result.summary)
```

## Documentation Templates

The skill supports:
- **api**: REST/GraphQL endpoint documentation
- **architecture**: System design and architecture
- **adr**: Architecture Decision Records
- **runbook**: Operational procedures
- **feature**: Feature specifications
- **infrastructure**: Infrastructure setup guides
- **troubleshooting**: Common issues and fixes
- **custom**: Your own template

## Core Methods

```python
# Generate documentation
skill.document(task="...", repo_path=".", dry_run=False)

# Search pages
pages = skill.search_pages(query="payment API")

# List page hierarchy
hierarchy = skill.list_page_hierarchy(parent_title="Backend APIs")

# Archive pages
skill.archive_page(page_id="123456")

# Bulk label pages
skill.bulk_label_pages(
    page_ids=["123", "456"],
    labels=["api", "v2"]
)
```

## Security & Best Practices

**IMPORTANT**: See [SECURITY.md](../SECURITY.md) for security guidelines:
- ✅ Store credentials in environment variables only
- ✅ Use `.confluence.example.yaml` as template, never commit `.confluence.yaml`
- ✅ Never hardcode API tokens in code
- ✅ Always use dry_run=True to preview changes first
- ✅ Review generated documentation before publishing

## Examples

See [examples/](../examples/) directory:
- `basic_usage.py`: Simple example
- `full_workflow.py`: Complete workflow
- `config_merging.py`: Configuration patterns

## Architecture & Development

- **Architecture Guide**: [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- **Skill Development**: [docs/SKILL_DEVELOPMENT.md](../docs/SKILL_DEVELOPMENT.md)
- **Contributing**: [CONTRIBUTING.md](../CONTRIBUTING.md)

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=confluence_skill --cov-report=html

# Specific category
pytest -m unit
pytest -m integration
```

## Troubleshooting

### "Module not found: confluence_skill"

```bash
# Install in development mode
pip install -e .
```

### "CONFLUENCE_TOKEN environment variable not found"

```bash
# Set the token
export CONFLUENCE_TOKEN="your_token_here"

# Or create .env.local (never commit)
echo "CONFLUENCE_TOKEN=your_token_here" > .env.local
```

### API rate limiting (429 errors)

The skill respects Confluence's 60 req/min limit with automatic backoff. To reduce:
- Use `dry_run=True` for testing
- Batch operations with `bulk_label_pages()`
- Cache results when possible

## Support & Resources

- 📖 [Full README](../README.md)
- 🔒 [Security Guidelines](../SECURITY.md)
- 🏗️ [Architecture Deep Dive](../docs/ARCHITECTURE.md)
- 🛠️ [Skill Development Guide](../docs/SKILL_DEVELOPMENT.md)
- 💡 [Usage Examples](../examples/)

## Status

**Version**: 1.2.0  
**Status**: Production Ready  
**License**: MIT

---

For security issues: craig@craighoad.com  
For feature requests: https://github.com/rhyscraig/confluence-skill/issues
