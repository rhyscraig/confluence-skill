# Document Templates

This skill provides built-in templates for common documentation types. Each template has a specific structure and is optimized for its use case.

## API Documentation (`api`)

Use for documenting REST APIs and service endpoints.

### Features
- Automatic endpoint extraction from code
- Method and path display
- Source file references
- Link to repository

### Best For
- REST API specifications
- Service endpoint documentation
- API reference guides

### Generated Sections
1. **Overview**: Brief description
2. **Endpoints**: Table of all endpoints
3. **Authentication**: Auth requirements
4. **Response Examples**: Sample responses
5. **Error Handling**: Error codes and messages

### Example
```yaml
documentation:
  template: "api"
  metadata:
    owner: "platform-team"
    audience: ["backend-engineers", "integrators"]
```

---

## Architecture Documentation (`architecture`)

Use for documenting system design and architecture.

### Features
- Automatic file structure extraction
- Dependency mapping
- Component relationships
- Technology stack overview

### Best For
- System architecture documents
- Service design documentation
- Technology decisions
- Component relationships

### Generated Sections
1. **Overview**: High-level architecture
2. **System Components**: Major components
3. **Dependencies**: External services/libraries
4. **Data Flow**: How data flows through system
5. **Technology Stack**: Languages, frameworks, databases

### Example
```yaml
documentation:
  template: "architecture"
  metadata:
    audience: ["architects", "lead-engineers"]
```

---

## Runbook (`runbook`)

Use for operational procedures and troubleshooting.

### Features
- Step-by-step procedure format
- Prerequisite checking
- Escalation paths
- Quick reference format

### Best For
- On-call procedures
- Incident response
- Operational runbooks
- Deployment procedures

### Generated Sections
1. **Overview**: What this runbook is for
2. **Prerequisites**: What must be true first
3. **Steps**: Numbered procedure steps
4. **Troubleshooting**: Common issues during procedure
5. **Escalation**: Who to contact if it fails
6. **Rollback**: How to undo changes

### Example
```yaml
documentation:
  template: "runbook"
  metadata:
    owner: "oncall-team"
    audience: ["oncall", "engineers"]
    labels: ["operations", "runbook"]
```

---

## Architecture Decision Record (`adr`)

Use for documenting architectural decisions (ADR format).

### Features
- Structured decision format
- Context and consequences
- Status tracking (proposed, accepted, deprecated)
- Decision rationale

### Best For
- Recording architectural decisions
- Design decisions
- Technology choices
- RFC-style documentation

### Generated Sections
1. **Status**: Decision status (proposed/accepted/deprecated)
2. **Context**: Why this decision matters
3. **Decision**: What was decided
4. **Consequences**: Implications of the decision
5. **Alternatives**: Other options considered

### Example
```yaml
documentation:
  template: "adr"
  metadata:
    status: "published"
    audience: ["architects", "tech-leads"]
```

---

## Feature Documentation (`feature`)

Use for documenting new features and functionality.

### Features
- Use case oriented
- User-centric perspective
- Implementation details
- Related API endpoints

### Best For
- Feature specifications
- Release notes
- User guides
- Product documentation

### Generated Sections
1. **Overview**: What the feature is
2. **Use Cases**: When to use it
3. **User Guide**: How to use it
4. **API Reference**: Relevant endpoints
5. **Configuration**: How to configure
6. **Examples**: Code examples

### Example
```yaml
documentation:
  template: "feature"
  metadata:
    audience: ["engineers", "product", "users"]
```

---

## Infrastructure Documentation (`infrastructure`)

Use for infrastructure and deployment documentation.

### Features
- Infrastructure diagrams
- Component listing
- Deployment procedures
- Monitoring setup

### Best For
- Infrastructure as Code documentation
- Deployment guides
- Cloud architecture
- System requirements

### Generated Sections
1. **System Architecture**: Diagram and overview
2. **Components**: Infrastructure components
3. **Networking**: Network topology
4. **Deployment**: How to deploy
5. **Scaling**: Scaling considerations
6. **Monitoring**: Observability setup
7. **Backup**: Backup and disaster recovery

### Example
```yaml
documentation:
  template: "infrastructure"
  metadata:
    owner: "devops-team"
    audience: ["devops", "infrastructure-engineers"]
```

---

## Troubleshooting Guide (`troubleshooting`)

Use for troubleshooting and debugging guides.

### Features
- Common issues indexed
- Symptom-based lookup
- Debug commands
- Root cause analysis

### Best For
- Troubleshooting guides
- FAQ documents
- Debug guides
- Common issues
- Support documentation

### Generated Sections
1. **Common Issues**: List of known issues
   - Symptoms
   - Root cause
   - Resolution steps
2. **Debug Tips**: Useful debug commands
3. **Log Locations**: Where to find logs
4. **Metrics**: Key metrics to monitor
5. **Getting Help**: Escalation paths

### Example
```yaml
documentation:
  template: "troubleshooting"
  metadata:
    audience: ["support", "engineers"]
    labels: ["troubleshooting", "faq"]
```

---

## Custom Documentation (`custom`)

Use for custom or specialized documentation that doesn't fit other templates.

### Features
- Minimal template structure
- Maximum flexibility
- Custom sections
- User-defined layout

### Best For
- Unique documentation needs
- Custom processes
- Specialized domains
- One-off documentation

### Generated Sections
1. **Title and Metadata**: Standard metadata section
2. **Content**: User-defined content

### Example
```yaml
documentation:
  template: "custom"
  metadata:
    owner: "team-lead"
```

---

## Template Selection Guide

| Need | Template | Best For |
|------|----------|----------|
| API endpoints | `api` | REST API documentation |
| System design | `architecture` | Architecture documents |
| Procedures | `runbook` | Operational procedures |
| Decisions | `adr` | Architectural decisions |
| New features | `feature` | Feature specifications |
| Infrastructure | `infrastructure` | Infrastructure docs |
| Debugging | `troubleshooting` | Troubleshooting guides |
| Custom | `custom` | Everything else |

---

## Customizing Templates

You can customize template behavior through configuration:

```yaml
documentation:
  template: "api"
  metadata:
    owner: "team-name"
    audience: 
      - "backend-engineers"
      - "platform-team"
    labels:
      - "auto-generated"
      - "api-docs"
    version: "2.0"
```

Or by creating a custom generator:

```python
from skills.confluence.doc_generators import DocGenerator

class MyCustomGenerator(DocGenerator):
    def generate(self) -> str:
        # Your custom generation logic
        return html_content
```
