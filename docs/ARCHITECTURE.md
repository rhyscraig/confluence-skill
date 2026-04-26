# Confluence Skill Architecture

## Overview

The Confluence skill is an enterprise-grade documentation system that integrates with Atlassian Confluence Cloud and Jira. It demonstrates best practices for Claude skill development including:

- Clear separation of concerns
- Input validation at all boundaries
- Comprehensive error handling
- Configuration merging (central + local)
- Optional graceful degradation (Jira)
- Rate limiting and caching
- MCP (Model Context Protocol) integration

## Core Components

### 1. ConfluenceClient (`confluence_client.py`)

**Responsibility**: Low-level Confluence Cloud API interaction

**Key Features**:
- HTTP session management with retry strategy
- Rate limiting (60 req/min, configurable)
- Page and permission caching
- Safe archive-instead-of-delete operations
- Input validation via InputValidator class

**Design Patterns**:
- Stateless utility methods (InputValidator)
- Rate limiter token bucket algorithm
- Cache invalidation on mutations
- HTTP error handling and user feedback

### 2. ConfluenceSkill (`skill.py`)

**Responsibility**: High-level workflow orchestration

**Key Features**:
- Multi-step document generation pipeline
- Configuration validation (fail-fast)
- Dry-run mode for safety
- Approval gates for production changes
- Metadata and content generation
- Jira integration (optional)

**Design Patterns**:
- Configuration merging strategy
- Try/catch with structured error reporting
- Progress logging with rich output
- Result objects with status tracking

### 3. Configuration (`models.py`)

**Responsibility**: Configuration validation and schema

**Key Features**:
- Pydantic v2 models for validation
- Nested configuration objects
- Enum-based constants
- YAML file loading support
- Configuration merging with local overrides

**Design Patterns**:
- Dataclass for metadata
- BaseModel for configuration
- Field validation with custom validators
- Merge strategy pattern

### 4. Code Analysis (`code_scanner.py`)

**Responsibility**: Extract APIs, dependencies, and architecture from code

**Features**:
- Language-agnostic extraction
- API documentation extraction
- Dependency analysis
- Architecture pattern detection

### 5. Document Generators (`doc_generators.py`)

**Responsibility**: Convert extracted info + metadata into Confluence storage format

**Features**:
- Multiple templates (API, Architecture, Runbook, ADR, etc.)
- Metadata section generation
- HTML storage format wrapping
- Content validation

### 6. Guardrails (`guardrails.py`)

**Responsibility**: Validation and safety checks

**Features**:
- Metadata validation
- Content size limits
- Deprecated terms detection
- Approval gates for sensitive operations

### 7. Jira Integration (`jira_integration.py`)

**Responsibility**: Optional Jira Cloud integration

**Features**:
- Issue searching and linking
- Task creation for undocumented APIs
- Epic linking
- Graceful degradation if disabled

**Design Pattern**: Optional feature that fails gracefully

### 8. MCP Server (`mcp.py`)

**Responsibility**: Claude integration via Model Context Protocol

**Features**:
- Tool definitions for Claude
- Request/response handling
- Error handling and formatting
- Support for: confluence_document, confluence_search, confluence_archive

## Data Flow

### Document Generation Flow

```
1. User Request (Claude or direct)
   ↓
2. Configuration Loading & Merging (.confluence.yaml)
   ↓
3. Input Validation (space_key, title, labels)
   ↓
4. Repository Code Analysis (APIs, dependencies)
   ↓
5. Metadata Generation (owner, audience, status)
   ↓
6. Content Generation (template-based)
   ↓
7. Guardrails Validation (size, deprecated terms)
   ↓
8. Approval Gate (if required)
   ↓
9. API Validation (space exists, has permissions)
   ↓
10. Page Create/Update
    ↓
11. Jira Integration (link issues, create tasks)
    ↓
12. Result Reporting (URL, metadata, errors)
```

## Configuration Merging Strategy

Three-level configuration hierarchy:

1. **Default** (hardcoded in SkillConfig)
2. **Central** (organization-wide at ~/.confluence/config.yaml)
3. **Local** (repo-specific at .confluence.yaml)

Each level overrides the previous. Local `.confluence.yaml` binds each repo to:
- Confluence space (terrorgems, Hoad-cloud-platforms, Engineering)
- Jira project (SCRUM, HCP, TPC, RFYT)

## Error Handling Strategy

**Fail-Fast Pattern**: Configuration errors detected immediately in __init__

**Validation-First**: InputValidator validates all user inputs before API calls

**Graceful Degradation**: Jira integration optional - works without it

**Structured Results**: All operations return result objects with:
- success: bool
- errors: list[ValidationError]
- warnings: list[ValidationError]

## Performance Considerations

- **Rate Limiting**: 60 requests/minute (respects Confluence Cloud rate limits)
- **Caching**: Pages and permissions cached locally
- **Batch Operations**: bulk_label_pages for efficiency
- **Timeout**: 30 seconds per API request with retry

## Testing Strategy

**71 Tests** covering:
- Unit tests (validators, generators, models)
- Integration tests (skill workflows)
- Configuration tests (merging, loading)
- Jira integration tests (optional features)

**Coverage**: >85% code coverage

**Categories**:
- unit: Individual component behavior
- integration: End-to-end workflows
- config: Configuration management
- jira: Optional integration

## Extension Points

The skill is designed for extensibility:

1. **New Templates**: Add to DocumentTemplate enum and create generator
2. **New Validators**: Add methods to InputValidator
3. **New Integrations**: Follow Jira integration pattern (optional, graceful)
4. **Custom Guardrails**: Extend GuardailsValidator
5. **Language Support**: Extend CodeScanner with new language extractors

## Standards Compliance

- **Type Hints**: Full type coverage with strict mypy
- **Docstrings**: Google-style docstrings on all public APIs
- **Error Handling**: Comprehensive with clear user messages
- **Configuration**: YAML-based with validation
- **Logging**: Optional (user requested no logging in v1.2.0)

## MCP Integration

The skill exposes three tools to Claude:

1. **confluence_document**: Generate docs from code
2. **confluence_search**: Search existing pages
3. **confluence_archive**: Archive pages safely

Each tool:
- Has descriptive schema
- Returns structured results
- Includes error handling
- Supports dry-run for safety

## Quality Metrics

- **Tests**: 71 passing
- **Coverage**: >85%
- **Type Hints**: 100%
- **Documentation**: Complete
- **Error Messages**: Actionable and clear
- **Version**: Semantic versioning (1.2.0)
