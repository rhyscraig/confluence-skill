# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-04-26

### Added
- Dedicated `confluence-skill` repository (extracted from claude-skills monorepo)
- Complete MCP (Model Context Protocol) integration for Claude Desktop
- SKILL_MANIFEST.json with full capability metadata
- Comprehensive architecture documentation (docs/ARCHITECTURE.md)
- Skill development guide for extending and creating new skills (docs/SKILL_DEVELOPMENT.md)
- Example usage patterns for basic, full workflow, and config merging scenarios
- Input validation methods in ConfluenceClient (validate_space_key, validate_page_title, validate_labels, validate_content_size, sanitize_content_for_html)
- Configuration validation in SkillConfig (validate_required_fields)
- Page management methods: list_page_hierarchy, archive_page, search_pages, bulk_label_pages
- Production exemplar architecture as template for other skills
- Pre-release checklist in SKILL_DEVELOPMENT.md (10-point validation)
- Full type hints and docstrings throughout
- >85% test coverage (71 tests across 4 categories)

### Changed
- Enhanced module docstring in __init__.py with quick-start example
- Updated public API exports to include mcp module, InputValidator, DocumentMetadata
- Improved error messages with clear context and actionable guidance
- Refined configuration merging patterns for flexibility

### Security
- Input validation at all API boundaries
- Rate limiting (60 req/min) with token bucket algorithm
- Content sanitization for HTML output
- Type hints enforced throughout (mypy strict mode)
- Security audit via bandit and pip-audit

## [1.0.0] - 2026-04-25

### Added
- Initial public release
- Confluence Cloud API v2 integration
- Multiple documentation templates (API, Architecture, ADR, Runbook, Feature, Infrastructure, Troubleshooting, Custom)
- Three-level configuration merging (default → central → local)
- Jira Cloud integration (optional)
- Rate limiting and caching
- Comprehensive test suite
- Full documentation

---

For detailed upgrade information, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
