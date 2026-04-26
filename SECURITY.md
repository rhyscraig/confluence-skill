# Security Policy

## Security Principles

This project follows defense-in-depth security practices:

1. **No Secrets in Code**: All credentials use environment variables only
2. **No Secrets in Config**: Configuration files are examples only
3. **Input Validation**: All external inputs validated immediately
4. **Type Safety**: Full type hints prevent injection attacks
5. **Rate Limiting**: Protection against API abuse
6. **Minimal Permissions**: Only request necessary Atlassian scopes

## Sensitive Information Protection

### What NEVER Goes in the Repository

❌ **Absolutely Never:**
- Confluence API tokens (use `CONFLUENCE_TOKEN` env var)
- Jira API tokens (use `JIRA_TOKEN` env var)
- AWS credentials or keys
- GitHub tokens
- Private keys (.pem, .key, .pfx files)
- Database passwords
- SSL certificates (private)
- Hardcoded URLs with authentication

❌ **Configuration Files:**
- `.confluence.yaml` - use `.confluence.example.yaml` instead
- `.jira.yaml` - use `.jira.example.yaml` instead
- `.env` files with real values - use `.env.example` instead

### What IS Safe

✅ **Safe to Commit:**
- `.confluence.example.yaml` - example with placeholder URLs
- `.jira.example.yaml` - example with generic project keys
- Environment variable NAMES (not values): `CONFLUENCE_TOKEN`, `JIRA_TOKEN`
- Example/test data marked as "fake", "test", or "example"
- Configuration schema and structure (no real values)
- Instructions on where to generate real tokens

## Git Protection

### .gitignore Rules

The `.gitignore` file prevents accidental commits of:
- All hidden config files (`.confluence.yaml`, `.jira.yaml`, etc.)
- All token/credential files (`*token*`, `*secret*`, `*credential*`)
- Environment files (`.env*` except `.env.example`)
- Private keys and certificates (`*.key`, `*.pem`, `*.pfx`, etc.)
- Cloud credentials (AWS, GCP, Azure files)
- SSH keys and configurations

### Pre-commit Checks

Before pushing, verify:
```bash
# Check for secrets patterns
git log --patch --all -S "token" -S "secret" -S "password"

# List files about to be committed
git diff --cached --name-only

# See staged content for sensitive files
git diff --cached | grep -i "token\|secret\|password\|api.key"
```

## Environment Variables (Correct Usage)

### Configuration

```python
# ✅ CORRECT: Use env var name in config
config = {
    "confluence": {
        "auth_token_env": "CONFLUENCE_TOKEN"  # Just the name
    }
}

# ✅ CORRECT: Code loads from environment at runtime
token = os.environ.get("CONFLUENCE_TOKEN")
```

### Setting Up Locally

```bash
# ✅ CORRECT: Set in shell before running
export CONFLUENCE_TOKEN="your_real_token_here"
python -m confluence_skill.mcp

# ✅ CORRECT: Set in .env.local (never committed)
# .env.local:
# CONFLUENCE_TOKEN=your_real_token_here
```

## Credential Types & How to Generate

### Confluence Cloud API Token

1. Visit: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Save the token (only shown once)
4. Set environment variable:
   ```bash
   export CONFLUENCE_TOKEN="your_token_here"
   ```

### Jira Cloud API Token

1. Visit: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Save the token (only shown once)
4. Set environment variable:
   ```bash
   export JIRA_TOKEN="your_token_here"
   ```

## Testing with Secrets

### Correct Test Pattern

```python
# ✅ CORRECT: Use mocking
from unittest.mock import patch

def test_api_call():
    with patch.dict("os.environ", {"CONFLUENCE_TOKEN": "fake-token"}):
        # Code that reads CONFLUENCE_TOKEN
        result = get_api_client()
        assert result is not None
```

❌ **Never hardcode real tokens in tests**

## Reporting Security Issues

If you find a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. **Do NOT** commit credentials or details
3. **Email** security concerns to: craig@craighoad.com
4. Include:
   - What the vulnerability is
   - How to reproduce it
   - Potential impact
   - Suggested fix (if any)

## Automated Security Checks

This project runs automated security audits:

```bash
# Type checking (prevents many injection attacks)
mypy . --strict

# Security audit
bandit -r confluence_skill/

# Dependency vulnerability scanning
pip-audit

# Git secret scanning (if configured)
# Scans for common secret patterns
```

## Deployment Security

### In Production

✅ **Do:**
- Use environment variables for all credentials
- Rotate API tokens regularly
- Use minimal-permission API tokens
- Log audit trails (not secrets)
- Monitor API rate limits
- Use HTTPS only

❌ **Don't:**
- Store credentials in config files
- Commit `.env` files
- Log API tokens
- Use generic/shared tokens
- Disable rate limiting
- Run with unnecessary permissions

## Scope & Permissions

This skill requests only necessary permissions:

**Confluence:**
- Read access to spaces
- Create/update pages
- Add labels
- Manage child pages

**Jira:**
- Read access to issues
- Create issues (if enabled)
- Link issues to pages

Never request unnecessary scopes.

## Updates & Patches

Security updates are released immediately when vulnerabilities are found.

To stay secure:
1. Run `pip install --upgrade confluence-skill`
2. Review [CHANGELOG.md](CHANGELOG.md) for security notes
3. Follow best practices in [CONTRIBUTING.md](CONTRIBUTING.md)

## Compliance

This project follows:
- OWASP Top 10 practices
- Secure coding guidelines
- Atlassian API security recommendations
- Python security best practices (PEP 8, type hints)

---

**Last Updated**: April 2026  
**Version**: 1.2.0

If you have security questions or concerns, contact craig@craighoad.com
