---
name: confluence
version: 1.2.0
description: Confluence (via Atlassian Connector) — Enterprise-grade Confluence Cloud documentation skill using the native Atlassian connector. Generates docs from code, manages pages at scale, links to Jira, and uses multiple templates. Always uses Atlassian connector authentication—never tokens or alternative setups. Use this skill whenever you need to: generate documentation from code repositories, create or update Confluence pages, search for documentation, archive pages, manage page hierarchies, or perform any Confluence Cloud operation.
author: Craig Hoad
---

# Confluence Skill

An enterprise-grade Confluence Cloud documentation skill that automatically generates and maintains documentation from your code repositories, manages pages at scale, links to Jira tickets, and supports multiple professional documentation templates.

## Quick Start

```bash
# Show help
confluence --help

# Generate API documentation (preview mode)
confluence document "Document the payment API" --doc-type api --dry-run

# Generate and publish documentation
confluence document "Document the payment API" --doc-type api --publish

# Search for existing documentation
confluence search "payment API" --space-key ENGINEERING --max-results 10

# Archive an outdated page
confluence archive 123456 --reason "Superseded by v2 API"
```

## Key Features

### 📝 Documentation Generation
- **8 Professional Templates**: API, Architecture, ADR, Runbook, Feature, Infrastructure, Troubleshooting, Custom
- **Code-to-Docs**: Automatically scan repositories and generate documentation
- **Jira Integration**: Link generated pages to Jira tickets automatically
- **Preview Mode**: Always preview with `--dry-run` before publishing
- **Bulk Operations**: Generate documentation for multiple services at once

### 🔗 Page Management
- **Search**: Find pages by title or content across spaces
- **Hierarchy**: Manage parent-child page relationships
- **Labeling**: Bulk label pages for organization
- **Archival**: Archive pages safely (preferred over deletion)
- **Version Control**: Track documentation versions alongside code

### 🛡️ Enterprise Features
- **Rate Limiting**: Automatic backoff respects Confluence's 60 req/min limit
- **Guardrails**: Safety confirmations for destructive operations
- **Configuration**: YAML-based configuration for spaces, audiences, metadata
- **Dry Run Mode**: Preview all changes before publishing
- **Error Handling**: Comprehensive error messages and recovery options

## Commands

### document
Generate documentation from code repositories and publish to Confluence.

```bash
confluence document "TASK_DESCRIPTION" --doc-type TYPE [--repo-path PATH] [--dry-run|--publish]
```

**Arguments:**
- `TASK_DESCRIPTION` - What to document (e.g., "Document the payment API")
- `--doc-type, -t` - Type of documentation (api, architecture, adr, runbook, feature, infrastructure, troubleshooting, custom)
- `--repo-path, -r` - Path to repository (default: .)
- `--dry-run` - Preview only (default), don't publish
- `--publish` - Publish to Confluence (requires --dry-run=false)

**Examples:**
```bash
# Preview API documentation
confluence document "Document payment service API" --doc-type api --dry-run

# Generate and publish architecture guide
confluence document "Architecture decision for caching layer" --doc-type adr --publish

# Generate troubleshooting guide
confluence document "Common issues and solutions" --doc-type troubleshooting --repo-path ./docs
```

### search
Search for pages in Confluence by title or content.

```bash
confluence search QUERY [--space-key SPACE] [--max-results N]
```

**Arguments:**
- `QUERY` - Search query (title or content)
- `--space-key, -s` - Confluence space key (optional)
- `--max-results, -m` - Maximum results (default: 10)

**Examples:**
```bash
confluence search "payment API"
confluence search "architecture" --space-key ENGINEERING --max-results 20
confluence search "v2" --space-key ENGINEERING
```

### archive
Archive a page safely (preferred over deletion).

```bash
confluence archive PAGE_ID [--reason REASON]
```

**Arguments:**
- `PAGE_ID` - Confluence page ID to archive
- `--reason` - Reason for archival (default: "Archived by automation")

**Examples:**
```bash
confluence archive 123456 --reason "Superseded by v2 API"
confluence archive 789012
```

## Configuration

### Environment Variables (Required)
- `CONFLUENCE_TOKEN` - API token from https://id.atlassian.com/manage-profile/security/api-tokens

### Optional Environment Variables
- `JIRA_TOKEN` - Jira API token (for Jira integration)
- `CONFLUENCE_INSTANCE` - Confluence instance URL (e.g., https://org.atlassian.net)
- `CONFLUENCE_SPACE` - Default space key

### Configuration File: `.confluence.yaml`

Create `.confluence.yaml` in your repository:

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
    labels: ["auto-generated", "api"]
```

Never commit `.confluence.yaml` with real credentials. Use environment variables instead.

## Installation

### From pip (Development)
```bash
pip install -e git+https://github.com/rhyscraig/confluence-skill.git#egg=confluence-skill
```

### From Local Repository
```bash
cd /path/to/confluence-skill
pip install -e .
```

### Verify Installation
```bash
confluence --version
confluence --help
which confluence
```

## Usage with Claude

### As an MCP Server (Recommended)

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "confluence": {
      "command": "python3",
      "args": ["-m", "confluence_skill.mcp"],
      "cwd": "/Users/craighoad/Repos/confluence-skill"
    }
  }
}
```

In Claude:
- `/confluence document "Write API documentation" doc_type=api dry_run=true`
- `/confluence search "payment API"`
- `/confluence archive page_id=123456`

### In Python

```python
from confluence_skill import ConfluenceSkill
from confluence_skill.models import SkillConfig

# Load configuration
config = SkillConfig.from_yaml(".confluence.yaml")
skill = ConfluenceSkill(config)

# Generate documentation
result = skill.document(
    task="Document the payment API",
    repo_path=".",
    dry_run=True  # Always preview first
)

print(result.summary)
```

## Documentation Templates

Each template provides a professional structure for different documentation types:

### API
REST/GraphQL endpoint documentation with parameters, responses, and examples.

### Architecture
System design, architecture diagrams, and technical decisions.

### ADR (Architecture Decision Record)
Lightweight decision documentation with context, decision, and consequences.

### Runbook
Step-by-step operational procedures for common tasks.

### Feature
Feature specifications including requirements, acceptance criteria, and examples.

### Infrastructure
Infrastructure setup guides, deployment instructions, and configuration.

### Troubleshooting
Common issues, solutions, and debug strategies.

### Custom
Use your own template or structure.

## Security & Best Practices

⚠️ **IMPORTANT**: Never store credentials in `.confluence.yaml` or code.

✅ **Do:**
- Store `CONFLUENCE_TOKEN` in environment variables
- Use `.confluence.example.yaml` as a template
- Always use `--dry-run` to preview changes
- Review generated documentation before publishing
- Keep credentials in `.env` (never commit)

❌ **Don't:**
- Hardcode API tokens in YAML files
- Publish without previewing (`--dry-run`)
- Commit configuration files with credentials
- Share tokens in pull requests or issues

## Troubleshooting

### "confluence: command not found"
```bash
# Reinstall
pip install -e /Users/craighoad/Repos/confluence-skill

# Verify PATH
which confluence

# Check Python environment
python3 -m confluence_skill.cli --version
```

### "CONFLUENCE_TOKEN environment variable not found"
```bash
# Set the token
export CONFLUENCE_TOKEN="your_token_here"

# Or create .env file (never commit)
echo "CONFLUENCE_TOKEN=your_token_here" > .env
source .env
```

### API Rate Limiting (429 errors)
The skill respects Confluence's 60 req/min limit with automatic backoff. To reduce:
- Use `--dry-run` for testing
- Batch operations when possible
- Cache results when appropriate

### "Invalid space key"
Verify your space key:
- Check Confluence instance for correct space key
- Update `.confluence.yaml` or use `--space-key` argument
- Ensure `CONFLUENCE_TOKEN` has access to the space

## Status

**Version**: 1.2.0  
**Status**: Production Ready  
**License**: MIT  
**Author**: Craig Hoad

## Support & Resources

- 📖 [Full README](README.md)
- 🔒 [Security Guidelines](SECURITY.md)
- 🏗️ [Architecture Guide](docs/ARCHITECTURE.md)
- 💡 [Usage Examples](examples/)
- 🐛 [Report Issues](https://github.com/rhyscraig/confluence-skill/issues)

---

**For security issues**: craig@craighoad.com  
**For feature requests**: https://github.com/rhyscraig/confluence-skill/issues  
**Source**: https://github.com/rhyscraig/confluence-skill
