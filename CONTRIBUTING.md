# Contributing to Confluence Skill

Thank you for your interest in contributing! This project follows enterprise-grade standards for code quality, testing, and documentation.

## Development Setup

### Prerequisites
- Python 3.12+
- Poetry

### Installation

```bash
git clone https://github.com/rhyscraig/confluence-skill.git
cd confluence-skill
poetry install
```

### Local Development

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=. --cov-report=html

# Format code
poetry run black .

# Type checking
poetry run mypy .

# Lint
poetry run ruff check .

# Security audit
poetry run bandit -r . && poetry run pip-audit
```

## Code Standards

- **Type Safety**: All code must have type hints (mypy strict mode)
- **Coverage**: Maintain >85% test coverage
- **Style**: Black for formatting, Ruff for linting
- **Documentation**: Docstrings on all public classes/functions
- **Tests**: Unit tests for all features, integration tests for API interactions

## Project Structure

```
confluence-skill/
├── confluence_skill/          # Main package
│   ├── __init__.py           # Public API
│   ├── skill.py              # ConfluenceSkill class
│   ├── confluence_client.py   # API client
│   ├── models.py             # Pydantic models
│   ├── code_scanner.py       # Code analysis
│   ├── doc_generators.py     # Template generators
│   ├── guardrails.py         # Safety validation
│   ├── jira_integration.py   # Jira integration
│   └── mcp.py                # MCP server
├── tests/                     # Test suite
├── docs/                      # Documentation
├── examples/                  # Usage examples
├── pyproject.toml            # Project config
└── README.md                 # User guide
```

## Contributing Process

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/your-feature`
3. **Make changes** following the standards above
4. **Test**: Run full test suite and ensure coverage >85%
5. **Commit**: Use clear, descriptive messages
6. **Push**: `git push origin feature/your-feature`
7. **Create PR**: Include description of changes

## Commit Messages

Use clear, imperative messages:
- ✅ "Add validation for page titles"
- ✅ "Fix rate limiting edge case"
- ❌ "Fixed stuff"
- ❌ "Updates"

## Testing Guidelines

- Write tests for all new features
- Maintain >85% code coverage
- Test error conditions, not just happy paths
- Use descriptive test names: `test_validate_space_key_rejects_invalid_format`

## Areas for Contribution

- [ ] Additional documentation templates
- [ ] Performance optimizations
- [ ] Additional Jira integration features
- [ ] Confluence Server (non-Cloud) support
- [ ] CI/CD integration examples
- [ ] More language examples

## Questions?

- Check [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design patterns
- Review [docs/SKILL_DEVELOPMENT.md](docs/SKILL_DEVELOPMENT.md) for extension points
- Look at [examples/](examples/) for usage patterns

## Code Review

All PRs require:
- ✅ Tests pass
- ✅ >85% coverage maintained
- ✅ Linting passes (ruff, black, mypy)
- ✅ Security checks pass (bandit, pip-audit)
- ✅ Docstrings updated
- ✅ CHANGELOG entry (if applicable)

---

We appreciate all contributions, no matter how small!
