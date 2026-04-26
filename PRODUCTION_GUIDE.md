# Production Guide: Confluence Skill

**This guide ensures the confluence-skill repository maintains enterprise-grade quality, security, and architecture standards.**

Table of Contents:
1. [Security & Secrets Management](#security--secrets-management)
2. [Modern Architecture](#modern-architecture)
3. [Testing Strategy](#testing-strategy)
4. [Code Quality](#code-quality)
5. [Documentation Standards](#documentation-standards)
6. [CI/CD & Pre-Release](#cicd--pre-release)

---

## Security & Secrets Management

### Zero-Tolerance Secrets Policy

**RULE: No credentials, API keys, tokens, or sensitive data EVER committed.**

#### Layer 1: Automated .gitignore Protection

The `.gitignore` uses **pattern-based blocking** to catch secrets automatically:

```
# Catch by name
*token*
*secret*
*password*
*credential*
*api_key*
*apikey*

# Catch by file type
*.key
*.pem
*.pfx
*.p12
.env*
.aws/
.ssh/

# Catch by file path
.confluence.yaml
.jira.yaml
credentials/
secrets/
```

**Test it works:**
```bash
# Create a test file with "token" in it
echo "test_token=abc123" > test-token.txt

# Stage it
git add test-token.txt

# Git will accept it (staging doesn't check .gitignore)
# But push will fail if we add proper pre-commit hook

# Verify .gitignore would block it
git check-ignore -v test-token.txt
# Output: .gitignore:XX:*token* test-token.txt

# Clean up
rm test-token.txt
```

#### Layer 2: Configuration Pattern

**Configuration files follow strict patterns:**

```
✅ SAFE TO COMMIT:
- .confluence.example.yaml       (Example with placeholders)
- config.example.yaml            (Reference configuration)
- .env.example                   (Env var names only, no values)

❌ NEVER COMMIT:
- .confluence.yaml               (Blocked by .gitignore)
- .jira.yaml                     (Blocked by .gitignore)
- .env                           (Blocked by .gitignore)
- .env.local                     (Blocked by .gitignore)
- Any file with real credentials
```

#### Layer 3: Code Review Checklist

Every PR must pass this security review:

```python
# ❌ WRONG: Hardcoded token
api_token = "atcXXXXXXXXXXXXXXXXXXXX"
client = ConfluenceClient(token=api_token)

# ✅ RIGHT: Environment variable
api_token = os.environ["CONFLUENCE_TOKEN"]
client = ConfluenceClient(token=api_token)

# ❌ WRONG: Token in config
confluence:
  token: "atcXXXXXXXXXXXXXXXXXXXX"

# ✅ RIGHT: Env var name in config
confluence:
  auth_token_env: "CONFLUENCE_TOKEN"
```

#### Layer 4: Test Patterns

**Never use real tokens in tests:**

```python
# ❌ WRONG: Real token in test
def test_api():
    client = ConfluenceClient(token="atcXXXXXXXXXXXXXXXXXXXX")
    result = client.get_page("123")

# ✅ RIGHT: Mocked/fake token
def test_api():
    with patch.dict("os.environ", {"CONFLUENCE_TOKEN": "fake-token-for-testing"}):
        client = ConfluenceClient()
        result = client.get_page("123")

# ✅ ALSO RIGHT: Mock the API
def test_api():
    with patch("confluence_skill.confluence_client.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"id": "123", "title": "Test"}
        client = ConfluenceClient()
        result = client.get_page("123")
        assert result.title == "Test"
```

#### Layer 5: Documentation Guidance

Every security-relevant doc points to `.env` setup:

- **README.md**: Links to SECURITY.md for env var setup
- **SECURITY.md**: Complete guide on token generation & env setup
- **.claude/CLAUDE.md**: Installation includes env var instructions
- **CONTRIBUTING.md**: Contributors must read SECURITY.md

#### Pre-Commit Hook (Optional)

To prevent accidental commits, add this to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Prevent committing files matching secret patterns

PATTERNS=(
    "CONFLUENCE_TOKEN="
    "JIRA_TOKEN="
    "api_token="
    "secret="
    "password="
)

for pattern in "${PATTERNS[@]}"; do
    if git diff --cached | grep -q "$pattern"; then
        echo "ERROR: Detected potential secret in staged changes: $pattern"
        echo "See SECURITY.md for proper credential handling"
        exit 1
    fi
done
```

### Secret Detection Tools

#### GitHub's Built-in Protection

Enable in repository settings:
- **Settings → Security & analysis → Secret scanning** ✅
- **Settings → Security & analysis → Push protection** ✅

#### Local Scanning

```bash
# Scan commits for secrets
git log --patch --all -S "CONFLUENCE_TOKEN" -S "atc" -S "api_token"

# Scan staged changes
git diff --cached | grep -i "token\|secret\|password"

# Scan entire repo (one-time)
grep -r "token.*=" . --include="*.py" --exclude-dir=.git | grep -v "auth_token_env\|fake\|test"
```

---

## Modern Architecture

### Design Principles

The confluence-skill follows **5 core architecture principles**:

#### 1. Separation of Concerns

**8 distinct modules with single responsibility:**

```
confluence_skill/
├── skill.py                 # Orchestration & workflows
├── confluence_client.py      # API interaction & rate limiting
├── models.py                # Data structures & validation
├── code_scanner.py          # Code analysis
├── doc_generators.py        # Template rendering
├── guardrails.py            # Safety checks
├── jira_integration.py       # External integration
└── mcp.py                   # Protocol interface
```

**Why it matters:**
- Each module has ONE reason to change
- Easy to test in isolation
- Easy to extend or replace
- Clear dependency graph

#### 2. Fail-Fast Pattern

**Validate immediately, fail loudly:**

```python
# ✅ Good: Validate in __init__
class ConfluenceSkill:
    def __init__(self, config: SkillConfig):
        # Validate immediately
        errors = config.validate_required_fields()
        if errors:
            raise ValueError(f"Invalid config: {errors}")
        
        # Only safe to proceed if validation passed
        self.config = config
        self.client = ConfluenceClient(config.confluence)

# ❌ Bad: Defer validation to first use
class ConfluenceSkill:
    def __init__(self, config: SkillConfig):
        self.config = config  # Might be invalid!
    
    def document(self, ...):
        # Validation happens here (too late!)
        if not self.config.space_key:
            raise ValueError("space_key required")
```

#### 3. Input Validation at Boundaries

**Validate all external input immediately:**

```python
class InputValidator:
    @staticmethod
    def validate_space_key(space_key: str) -> tuple[bool, str]:
        """Validate Confluence space key format."""
        if not space_key:
            return False, "space_key cannot be empty"
        if not re.match(r"^[A-Z0-9]+$", space_key):
            return False, "space_key must be uppercase alphanumeric"
        if len(space_key) > 255:
            return False, "space_key must be < 255 chars"
        return True, ""

# Usage
def create_page(self, space_key: str, title: str) -> Page:
    is_valid, error = InputValidator.validate_space_key(space_key)
    if not is_valid:
        raise ValueError(f"Invalid space_key: {error}")
    
    # Safe to use space_key here
    return self._api_create_page(space_key, title)
```

#### 4. Graceful Degradation

**Optional features don't break core functionality:**

```python
# Jira integration is optional
class ConfluenceSkill:
    def __init__(self, config: SkillConfig):
        self.jira = None
        
        if config.jira.enabled:
            try:
                self.jira = JiraIntegration(config.jira)
            except Exception as e:
                logger.warning(f"Jira integration disabled: {e}")
                # Continue without Jira
    
    def document(self, task: str) -> Result:
        # Document works with or without Jira
        result = self._generate_documentation(task)
        
        # Optionally link to Jira
        if self.jira:
            try:
                self.jira.link_issues(result)
            except Exception as e:
                logger.warning(f"Failed to link Jira issues: {e}")
                # Continue, documentation is still valid
        
        return result
```

#### 5. Configuration Merging

**Three-level hierarchy for flexibility:**

```
┌─────────────────────────────────────┐
│  Default (hardcoded in code)        │  Base defaults
├─────────────────────────────────────┤
│  Central (config.yaml in repo)      │  Override defaults
├─────────────────────────────────────┤
│  Local (.confluence.yaml in repo)   │  Final overrides
└─────────────────────────────────────┘
```

```python
def load_config(central_path: str = None, local_path: str = None) -> SkillConfig:
    """Load config with three-level merging."""
    # Start with defaults
    config = SkillConfig()
    
    # Merge central config (optional)
    if central_path and os.path.exists(central_path):
        central = SkillConfig.from_yaml(central_path)
        config = config.merge(central)
    
    # Merge local config (optional)
    if local_path and os.path.exists(local_path):
        local = SkillConfig.from_yaml(local_path)
        config = config.merge(local)
    
    return config
```

### Type Safety

**Full type hints throughout (mypy strict mode):**

```python
from typing import Optional, List, Dict, Tuple
from confluence_skill.models import Page, Result

def search_pages(
    self,
    query: str,
    space_key: Optional[str] = None,
    limit: int = 50
) -> List[Page]:
    """Search Confluence pages.
    
    Args:
        query: Search query string
        space_key: Restrict to space (optional)
        limit: Max results (default 50)
    
    Returns:
        List of matching pages
    
    Raises:
        ValueError: If query is empty
        RuntimeError: If API call fails
    """
    if not query:
        raise ValueError("query cannot be empty")
    
    # Type checker knows these are str/int/Optional[str]
    # IDE autocomplete works perfectly
    result = self.client.search(query, space_key, limit)
    return result.pages
```

---

## Testing Strategy

### Pragmatic Testing Philosophy

**Test behavior, not implementation. Balance coverage with pragmatism.**

```
        Coverage Target: >85%
         /       |       \
    Unit Tests  Integration  E2E
      (60%)        (20%)     (5%)
    (Fast)      (Medium)    (Slow)
  (Many cases)  (Key flows) (Real APIs)
```

### Test Categories

#### 1. Unit Tests (60% of tests)

**Fast, isolated, no external dependencies:**

```python
# tests/test_models.py
def test_validate_space_key_rejects_lowercase():
    """Space keys must be uppercase."""
    is_valid, error = InputValidator.validate_space_key("eng")
    assert not is_valid
    assert "uppercase" in error

def test_validate_space_key_accepts_valid():
    """Valid space keys are accepted."""
    is_valid, error = InputValidator.validate_space_key("ENG")
    assert is_valid
    assert error == ""

def test_skill_config_merging():
    """Configuration merging combines sources."""
    config1 = SkillConfig(space_key="ENG")
    config2 = SkillConfig(space_key="PLATFORM", owner="team1")
    
    merged = config1.merge(config2)
    assert merged.space_key == "PLATFORM"  # Overridden
    assert merged.owner == "team1"         # Added
```

#### 2. Integration Tests (20% of tests)

**Test subsystem interactions, mock external APIs:**

```python
# tests/test_skill_integration.py
@patch.dict("os.environ", {"CONFLUENCE_TOKEN": "fake-token"})
@patch("confluence_skill.confluence_client.requests.get")
def test_skill_generates_documentation(mock_get):
    """ConfluenceSkill generates documentation end-to-end."""
    # Mock API responses
    mock_get.return_value.json.return_value = {
        "page": {"id": "123", "title": "Test"}
    }
    
    config = SkillConfig(
        confluence=ConfluenceConfig(
            instance_url="https://test.atlassian.net",
            space_key="ENG"
        )
    )
    skill = ConfluenceSkill(config)
    
    result = skill.document(
        task="Document the API",
        repo_path=".",
        dry_run=True
    )
    
    assert result.success
    assert "API" in result.content_preview
```

#### 3. E2E Tests (5% of tests)

**Real APIs, real data, real scenarios:**

```python
# tests/test_e2e.py
@pytest.mark.integration
@pytest.mark.slow
def test_real_confluence_api():
    """Test with real Confluence instance (requires CONFLUENCE_TOKEN)."""
    # Skip if no token
    if not os.environ.get("CONFLUENCE_TOKEN"):
        pytest.skip("CONFLUENCE_TOKEN not set")
    
    config = SkillConfig.from_yaml(".confluence.yaml")
    skill = ConfluenceSkill(config)
    
    # Test with real API (dry-run safe)
    result = skill.document(
        task="Document this repository",
        repo_path=".",
        dry_run=True  # Don't actually write
    )
    
    assert result.success
    assert len(result.pages) > 0
```

### Testing Patterns

#### Pattern 1: Mocking External Dependencies

```python
from unittest.mock import patch, MagicMock

def test_api_call_with_mock():
    """Mock requests library."""
    with patch("confluence_skill.confluence_client.requests.post") as mock_post:
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            "id": "123",
            "title": "New Page"
        }
        
        client = ConfluenceClient(token="fake-token")
        result = client.create_page("ENG", "New Page", "<p>Content</p>")
        
        assert result.id == "123"
        mock_post.assert_called_once()
```

#### Pattern 2: Environment Variable Testing

```python
def test_config_loads_from_env():
    """Configuration reads from environment."""
    with patch.dict("os.environ", {
        "CONFLUENCE_TOKEN": "test-token",
        "JIRA_TOKEN": "jira-token"
    }):
        config = SkillConfig()
        client = ConfluenceClient(
            token=os.environ["CONFLUENCE_TOKEN"]
        )
        
        assert client is not None
```

#### Pattern 3: Error Path Testing

```python
def test_error_handling():
    """Test error cases."""
    with patch("confluence_skill.confluence_client.requests.get") as mock_get:
        # Simulate API error
        mock_get.side_effect = requests.ConnectionError("Network error")
        
        client = ConfluenceClient(token="fake-token")
        
        with pytest.raises(RuntimeError) as exc_info:
            client.get_page("123")
        
        assert "Network error" in str(exc_info.value)
```

### Coverage Requirements

```bash
# Run tests with coverage
pytest --cov=confluence_skill --cov-report=html

# Check coverage per module
pytest --cov=confluence_skill --cov-report=term-missing

# Enforce minimum coverage
pytest --cov=confluence_skill --cov-fail-under=85
```

**Coverage targets by module:**

| Module | Target | Why |
|--------|--------|-----|
| models.py | 95% | Core data structures |
| confluence_client.py | 90% | API interaction critical |
| skill.py | 85% | Workflow orchestration |
| code_scanner.py | 80% | Complex logic, integration |
| doc_generators.py | 85% | Template rendering |
| guardrails.py | 90% | Safety-critical |
| jira_integration.py | 75% | Optional feature |
| mcp.py | 80% | Protocol wrapper |

---

## Code Quality

### Type Hints & Static Analysis

**100% type coverage with mypy strict mode:**

```bash
# Check type coverage
mypy confluence_skill --strict

# Enforce in CI
mypy confluence_skill --strict --fail-fast
```

### Style & Formatting

**Consistent style with automatic formatting:**

```bash
# Format code
black confluence_skill/

# Check style
ruff check confluence_skill/

# Type check
mypy confluence_skill/ --strict
```

**Configuration in pyproject.toml:**

```toml
[tool.black]
line-length = 120
target-version = ["py312"]

[tool.ruff]
line-length = 120
select = ["E", "F", "W", "I", "UP", "B", "C4", "ARG", "RUF"]
```

### Documentation & Docstrings

**All public APIs must have docstrings:**

```python
def document(
    self,
    task: str,
    repo_path: str = ".",
    template: str = "api",
    dry_run: bool = True
) -> DocumentGenerationResult:
    """Generate documentation from code repository.
    
    This is the primary method for creating documentation. It analyzes
    the repository, extracts relevant code, and generates formatted
    documentation using the specified template.
    
    Args:
        task: Description of what to document (e.g., "Document the payment API")
        repo_path: Path to repository root (default current directory)
        template: Documentation template type - one of:
            - "api": REST/GraphQL endpoint documentation
            - "architecture": System design and architecture
            - "adr": Architecture Decision Record
            - "runbook": Operational procedures
            - "feature": Feature specification
            - "infrastructure": Infrastructure setup
            - "troubleshooting": Common issues and fixes
            - "custom": Custom template (user-provided)
        dry_run: If True (default), preview changes without writing.
                 Set to False only after reviewing preview.
    
    Returns:
        DocumentGenerationResult containing:
        - success: Whether generation succeeded
        - summary: Human-readable summary
        - pages: Generated page objects
        - content_preview: Preview of generated content
        - errors: List of errors if generation failed
    
    Raises:
        ValueError: If task is empty or template unknown
        RuntimeError: If repository analysis fails
        PermissionError: If lacking write permissions to space
    
    Example:
        >>> config = SkillConfig.from_yaml(".confluence.yaml")
        >>> skill = ConfluenceSkill(config)
        >>> result = skill.document(
        ...     task="Document the payment API",
        ...     repo_path=".",
        ...     dry_run=True
        ... )
        >>> if result.success:
        ...     print(result.summary)
        ...     # Review preview before committing
        ...     skill.document(..., dry_run=False)
    """
```

---

## Documentation Standards

### README Excellence

**README serves three audiences:**

1. **New Users** → Installation & quick start
2. **Experienced Users** → Feature reference
3. **Developers** → Architecture & contribution

**Structure:**
- Badge row (license, version, coverage, style)
- One-liner description
- Feature highlights
- Quick start (5 min)
- Core concepts
- API reference
- Examples
- Support links

### Architecture Documentation

**docs/ARCHITECTURE.md should include:**

```markdown
# Architecture

## Components
1. **ConfluenceClient** - API layer, rate limiting, caching
2. **ConfluenceSkill** - Orchestration, workflows
3. **Configuration** - Pydantic models, validation, merging
4. ... (8 total)

## Data Flow
[Diagram showing document generation flow]

## Configuration Hierarchy
[Diagram showing default → central → local merging]

## Error Handling Strategy
- Fail-fast validation on __init__
- Clear error messages with context
- Graceful degradation of optional features
- Structured result objects with error details

## Performance Considerations
- Rate limiting: 60 req/min (Confluence API limit)
- Caching: Smart invalidation for pages & permissions
- Batch operations: Reduce API calls
- Timeouts: Configurable, sensible defaults

## Extension Points
How to add new templates, new generators, custom validators
```

### Skill Development Guide

**docs/SKILL_DEVELOPMENT.md guides new skill creators:**

```markdown
# Creating New Skills

This skill is an exemplar. Use it as a template.

## Core Principles
1. Clear separation of concerns
2. Input validation at boundaries
3. Configuration merging
4. Graceful degradation
5. Fail-fast pattern

## Project Structure
[Complete file tree]

## Development Workflow
1. Design with principles in mind
2. Implement core logic
3. Add integration layer
4. Write comprehensive tests
5. Document everything
6. Pre-release checklist

## Common Patterns
[6 ready-to-copy patterns for common scenarios]

## Anti-Patterns
[8 patterns to avoid]
```

---

## CI/CD & Pre-Release

### Automated Quality Gates

**Every commit must pass:**

```yaml
# .github/workflows/quality.yml
name: Quality Gates

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.12"
      
      # Security scanning
      - name: Secret detection
        run: |
          pip install detect-secrets
          detect-secrets scan --baseline .secrets.baseline
      
      # Type checking
      - name: Type checking
        run: pip install mypy && mypy confluence_skill --strict
      
      # Linting
      - name: Linting
        run: pip install ruff && ruff check confluence_skill
      
      # Formatting
      - name: Format check
        run: pip install black && black --check confluence_skill
      
      # Tests
      - name: Unit tests
        run: |
          pip install -e . pytest pytest-cov pytest-mock
          pytest --cov=confluence_skill --cov-fail-under=85
      
      # Security audit
      - name: Security audit
        run: |
          pip install bandit pip-audit
          bandit -r confluence_skill
          pip-audit
```

### Pre-Release Checklist

**Before any release:**

```markdown
# Pre-Release Checklist v1.2.0

## Security ✓
- [ ] No .gitignore violations (git check-ignore)
- [ ] No hardcoded tokens/keys (grep -r patterns)
- [ ] All config examples only
- [ ] SECURITY.md up-to-date
- [ ] Test tokens are fake/mocked

## Code Quality ✓
- [ ] mypy passes (strict mode)
- [ ] ruff passes
- [ ] black passes
- [ ] Coverage >85% (pytest --cov)
- [ ] All docstrings present

## Testing ✓
- [ ] Unit tests pass (pytest -m unit)
- [ ] Integration tests pass (pytest -m integration)
- [ ] No skipped tests (pytest -v | grep SKIPPED)
- [ ] Manual spot-checks complete

## Documentation ✓
- [ ] README updated
- [ ] CHANGELOG.md updated
- [ ] SECURITY.md reflects changes
- [ ] API docstrings complete
- [ ] Examples work (manual test)

## Release ✓
- [ ] Version bumped (pyproject.toml)
- [ ] Git tag created
- [ ] Release notes written
- [ ] Package built locally (pip install -e .)
- [ ] All quality gates pass in CI

## Post-Release ✓
- [ ] PyPI upload (twine upload dist/*)
- [ ] GitHub release created
- [ ] Changelog linked in release notes
- [ ] Security.md referenced in release
```

### Version Management

**Semantic Versioning:**

```
MAJOR.MINOR.PATCH
  |      |      |
  |      |      └─ Bug fixes, no API changes
  |      └────────── New features, backward compatible
  └─────────────── Breaking changes
```

**Update rules:**
- Patch: Bug fixes, security patches → Auto-release
- Minor: New features, new templates → Release cycle
- Major: Breaking changes → Plan in advance

---

## Summary: Quality Gates

Every push through this gate:

```
Push Code
    ↓
[Secret Detection] ← detect-secrets scan
    ↓ ✅
[Type Checking] ← mypy --strict
    ↓ ✅
[Linting] ← ruff check
    ↓ ✅
[Formatting] ← black --check
    ↓ ✅
[Tests] ← pytest --cov >85%
    ↓ ✅
[Security Audit] ← bandit + pip-audit
    ↓ ✅
[Documentation] ← All docstrings present
    ↓ ✅
Build & Merge ✓
```

This is how we stay production-ready forever.

---

**Last Updated**: April 2026  
**Version**: 1.2.0  
**Status**: Production-Grade  
**Maintainer**: Craig Hoad

For security issues: craig@craighoad.com
