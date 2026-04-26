# Claude Skill Development Guide

This document uses the Confluence skill as an exemplar for developing enterprise-grade Claude skills.

## Principles

### 1. Clear Separation of Concerns

**Good**: Each module has one responsibility

```
confluence_client.py  → API interaction
skill.py             → Workflow orchestration
models.py            → Configuration & validation
doc_generators.py    → Content generation
```

**Bad**: Single monolithic file doing everything

### 2. Input Validation at Boundaries

**Good**: Validate all user input before API calls

```python
# In create_page():
valid, error = InputValidator.validate_space_key(space_key)
if not valid:
    raise ValueError(f"Invalid space key: {error}")
```

**Bad**: Assuming input is valid and getting API errors

### 3. Configuration Merging

**Good**: Three-level hierarchy (default → central → local)

```
Default config (hardcoded)
    ↓
Central config (~/.skill/config.yaml)
    ↓
Local config (repo/.skill.yaml)
```

**Bad**: Single fixed configuration

### 4. Graceful Degradation

**Good**: Optional features that work without them

```python
if jira_integration.client.enabled:
    # Use Jira
else:
    # Continue without it
```

**Bad**: Features that break if optional dependency fails

### 5. Fail-Fast Pattern

**Good**: Validate configuration immediately

```python
def __init__(self, config):
    errors = config.validate_required_fields()
    if errors:
        raise ValueError(f"Config errors:\n" + "\n".join(errors))
```

**Bad**: Let errors surface in random functions later

## Project Layout

```
skills/confluence/
├── __init__.py                    # Exports public API
├── skill.py                       # ConfluenceSkill (main)
├── confluence_client.py           # API wrapper
├── models.py                      # Config & validation
├── doc_generators.py              # Template generators
├── code_scanner.py                # Code analysis
├── jira_integration.py            # Optional Jira integration
├── guardrails.py                  # Validation & safety
├── mcp.py                         # Claude integration (MCP)
├── SKILL_MANIFEST.json            # Skill metadata
├── README.md                      # User documentation
├── docs/
│   ├── ARCHITECTURE.md            # Design decisions
│   ├── SKILL_DEVELOPMENT.md       # This file
│   ├── TEMPLATES.md               # Template reference
│   └── examples/
│       ├── basic_usage.py         # Hello world
│       ├── full_workflow.py       # Complete example
│       └── config_merging.py      # Configuration example
├── tests/
│   ├── conftest.py                # Pytest fixtures
│   ├── test_skill.py              # Main skill tests
│   ├── test_client.py             # Client tests
│   ├── test_models.py             # Configuration tests
│   └── test_jira_integration.py   # Jira tests
└── .confluence.yaml               # Example local config
```

## Core Files Checklist

### skill.py (Main Skill)
- ✅ Single SkillClass with clear public methods
- ✅ Comprehensive docstrings on all public methods
- ✅ Full type hints (input and return)
- ✅ Error handling with try/except
- ✅ Logging of operations (optional)
- ✅ Result objects not tuple returns

### confluence_client.py (API Client)
- ✅ Stateless methods (no stored state except config)
- ✅ Rate limiting built-in
- ✅ Caching for expensive operations
- ✅ Clear method names matching API concepts
- ✅ Input validation at all API calls
- ✅ Rich error messages with suggestions

### models.py (Configuration)
- ✅ Pydantic v2 BaseModel for validation
- ✅ Field validators for custom logic
- ✅ Clear default values
- ✅ Enum for constants
- ✅ Dataclass for non-config data
- ✅ Config merging logic

### Tests (tests/)
- ✅ 70+ unit and integration tests
- ✅ >85% code coverage
- ✅ Mocking for external APIs
- ✅ Fixtures for common setup
- ✅ Clear test naming (test_what_should_happen)
- ✅ Organized by module

### Documentation
- ✅ README.md with quick start
- ✅ ARCHITECTURE.md with design decisions
- ✅ SKILL_MANIFEST.json with metadata
- ✅ Examples with working code
- ✅ API reference (docstrings)

### MCP Integration (mcp.py)
- ✅ Tool definitions with schemas
- ✅ Input validation
- ✅ Error handling
- ✅ Result formatting
- ✅ Server entry point

## Development Workflow

### Phase 1: Design
1. Create SKILL_MANIFEST.json early
2. Define configuration in models.py
3. List required external APIs
4. Plan error scenarios

### Phase 2: Core Implementation
1. Implement API client (confluence_client.py)
2. Implement skill orchestration (skill.py)
3. Add input validation
4. Write unit tests as you go

### Phase 3: Integration
1. Add optional integrations (jira_integration.py)
2. Add guardrails (guardrails.py)
3. Add MCP server (mcp.py)
4. Write integration tests

### Phase 4: Documentation
1. Write README with examples
2. Document architecture decisions
3. Add code examples
4. Create skill manifest

### Phase 5: Polish
1. Achieve >85% test coverage
2. Full type hints
3. Comprehensive docstrings
4. Error message quality

## Common Patterns

### Configuration Merging
```python
# In skill/__init__.py
def __init__(self, config: SkillConfig):
    errors = config.validate_required_fields()
    if errors:
        raise ValueError(f"Config errors:\n" + 
                        "\n".join(f"  - {e}" for e in errors))
    self.config = config
```

### Input Validation
```python
# In client method
def create_page(self, space_key: str, title: str):
    valid, error = InputValidator.validate_space_key(space_key)
    if not valid:
        raise ValueError(f"Invalid space key: {error}")
    
    # Now safe to use space_key
```

### Result Objects
```python
@dataclass
class DocumentGenerationResult:
    success: bool
    document_id: Optional[str] = None
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    duration_seconds: float = 0.0
    
    def summary(self) -> str:
        # User-friendly summary
        pass
```

### Graceful Degradation
```python
if working_config.jira.enabled:
    jira_integration = JiraIntegration(working_config.jira)
    if not jira_integration.client.enabled:
        # Token missing but Jira config enabled - warn but continue
        self.console.print("[yellow]Jira disabled (token missing)[/yellow]")
else:
    jira_integration = None

# Later: check if jira_integration exists before using
if jira_integration:
    issues = jira_integration.link_related_issues(...)
```

### MCP Tool Definition
```python
TOOLS = [
    {
        "name": "skill_action",
        "description": "User-facing description",
        "input_schema": {
            "type": "object",
            "properties": {
                "param": {
                    "type": "string",
                    "description": "Parameter description"
                }
            },
            "required": ["param"]
        }
    }
]
```

## Anti-Patterns to Avoid

1. ❌ **Global State**: Store state in modules, not globals
2. ❌ **Silent Failures**: Always raise or log errors
3. ❌ **Mixed Concerns**: Keep API code separate from orchestration
4. ❌ **Incomplete Validation**: Validate everything at boundaries
5. ❌ **No Type Hints**: Use full type hints always
6. ❌ **Monolithic Files**: Split by responsibility
7. ❌ **Hard-coded Values**: Put in config or constants
8. ❌ **Tuple Returns**: Use result objects or exceptions

## Checklist Before Release

- ✅ Tests >85% coverage
- ✅ All type hints present
- ✅ All docstrings present
- ✅ README with examples
- ✅ ARCHITECTURE.md complete
- ✅ SKILL_MANIFEST.json accurate
- ✅ MCP server tested
- ✅ Configuration examples provided
- ✅ Error messages are actionable
- ✅ Version bumped (semver)

## Example: Creating a New Skill from This Template

1. Copy skills/confluence/ → skills/myskill/
2. Replace "Confluence" with "MySkill" everywhere
3. Update SKILL_MANIFEST.json
4. Implement MySkillClient (replace ConfluenceClient)
5. Implement MySkill (replace ConfluenceSkill)
6. Update tests with your scenarios
7. Add MCP tools for Claude
8. Document architecture decisions

This skill serves as your starting point. Good luck! 🚀
