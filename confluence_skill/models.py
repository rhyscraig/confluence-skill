"""Data models and validation for Confluence skill."""

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Any

import yaml
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationError


class MergeStrategy(str, Enum):
    """How to handle existing documents."""

    APPEND = "append"
    REPLACE = "replace"
    INTERACTIVE = "interactive"
    SKIP = "skip"


class DocumentStatus(str, Enum):
    """Document lifecycle status."""

    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class DocumentTemplate(str, Enum):
    """Document templates available."""

    API = "api"
    ARCHITECTURE = "architecture"
    RUNBOOK = "runbook"
    ADR = "adr"
    FEATURE = "feature"
    INFRASTRUCTURE = "infrastructure"
    TROUBLESHOOTING = "troubleshooting"
    CUSTOM = "custom"


class ConfluenceConfig(BaseModel):
    """Confluence instance configuration."""

    instance_url: str = Field(..., description="Confluence Cloud instance URL")
    space_key: Optional[str] = Field(None, description="Default space key")
    auth_token_env: str = Field(default="CONFLUENCE_TOKEN", description="Auth token env var")
    api_timeout_seconds: int = Field(default=30, ge=5, le=60)
    rate_limit_per_minute: int = Field(default=60, ge=10, le=300)

    @field_validator("instance_url")
    @classmethod
    def validate_instance_url(cls, v):
        """Validate Confluence URL format."""
        if not v.startswith("https://") or ".atlassian.net" not in v:
            raise ValueError("Must be HTTPS Confluence Cloud instance (*.atlassian.net)")
        return v.rstrip("/")

    model_config = ConfigDict(use_enum_values=True)


class MetadataConfig(BaseModel):
    """Document metadata configuration."""

    owner: Optional[str] = None
    audience: list[str] = Field(default_factory=list)
    status: DocumentStatus = DocumentStatus.DRAFT
    labels: list[str] = Field(default_factory=list)
    version: Optional[str] = None
    last_updated: Optional[datetime] = None
    last_updated_by: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


class DocumentationConfig(BaseModel):
    """Documentation generation configuration."""

    template: DocumentTemplate = DocumentTemplate.CUSTOM
    space_key: Optional[str] = None
    parent_page: Optional[str] = None
    parent_page_id: Optional[str] = None
    auto_title: bool = True
    merge_strategy: MergeStrategy = MergeStrategy.INTERACTIVE
    version_tracking: bool = True
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)

    model_config = ConfigDict(use_enum_values=True)


class CodeAnalysisConfig(BaseModel):
    """Code analysis configuration."""

    enabled: bool = True
    repos: list[dict[str, Any]] = Field(default_factory=list)
    extract: list[str] = Field(default_factory=lambda: ["apis", "architecture", "dependencies"])
    max_file_size_kb: int = 500
    max_files_to_analyze: int = 100

    @field_validator("max_file_size_kb", "max_files_to_analyze")
    @classmethod
    def validate_limits(cls, v):
        """Ensure limits are reasonable."""
        if v <= 0:
            raise ValueError("Must be positive")
        return v


class GuardrailsConfig(BaseModel):
    """Safety guardrails configuration."""

    enabled: bool = True
    require_approval: bool = True
    dry_run_by_default: bool = True
    validate_links: bool = True
    check_permissions: bool = True
    validate_metadata: bool = True
    max_document_size_kb: int = 2000
    required_metadata_fields: list[str] = Field(default_factory=lambda: ["owner", "audience"])
    deprecated_terms: list[str] = Field(default_factory=list)


class IntegrationConfig(BaseModel):
    """External service integrations."""

    github: dict[str, Any] = Field(default_factory=dict)
    jira: dict[str, Any] = Field(default_factory=dict)


class OutputConfig(BaseModel):
    """Output and logging configuration."""

    verbose: bool = False
    log_file: Optional[str] = None
    create_audit_trail: bool = True


class JiraConfig(BaseModel):
    """Jira integration configuration."""

    enabled: bool = False
    instance_url: Optional[str] = None
    auth_token_env: str = "JIRA_TOKEN"
    default_project: Optional[str] = None
    auto_link_related: bool = True
    create_tasks_for_gaps: bool = False
    epic_link_pattern: Optional[str] = None  # e.g., "PROJ-\d+"
    custom_fields: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)


class SkillConfig(BaseModel):
    """Complete Confluence skill configuration."""

    confluence: ConfluenceConfig
    documentation: DocumentationConfig = Field(default_factory=DocumentationConfig)
    code_analysis: CodeAnalysisConfig = Field(default_factory=CodeAnalysisConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    integration: IntegrationConfig = Field(default_factory=IntegrationConfig)
    jira: JiraConfig = Field(default_factory=JiraConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    def validate_required_fields(self) -> list[str]:
        """Validate that required configuration fields are set.

        Returns:
            List of errors (empty if valid)
        """
        errors = []

        if not self.confluence.instance_url:
            errors.append("confluence.instance_url is required")
        if not self.confluence.space_key:
            errors.append("confluence.space_key is required")
        if not self.documentation.metadata or not self.documentation.metadata.owner:
            errors.append("documentation.metadata.owner is required")
        if not self.documentation.metadata or not self.documentation.metadata.audience:
            errors.append("documentation.metadata.audience must be non-empty")

        return errors

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SkillConfig":
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert to dictionary (handles enums)."""
        return asdict(self)

    def merge(self, local: "LocalConfig") -> "SkillConfig":
        """Merge local config overrides into this config.

        Args:
            local: Local repository configuration

        Returns:
            Merged configuration with local overrides
        """
        merged_data = self.model_dump()

        # Merge documentation config
        if local.documentation:
            doc_data = local.documentation.model_dump(exclude_none=True)
            merged_data["documentation"].update(doc_data)

        # Merge Jira config
        if local.jira:
            jira_data = local.jira.model_dump(exclude_none=True)
            merged_data["jira"].update(jira_data)

        # Merge code analysis config
        if local.code_analysis:
            ca_data = local.code_analysis.model_dump(exclude_none=True)
            merged_data["code_analysis"].update(ca_data)

        return SkillConfig(**merged_data)

    model_config = ConfigDict(use_enum_values=True)


class LocalConfig(BaseModel):
    """Local repository-level configuration overrides."""

    documentation: Optional[DocumentationConfig] = None
    jira: Optional[JiraConfig] = None
    code_analysis: Optional[CodeAnalysisConfig] = None

    @classmethod
    def from_yaml(cls, path: str | Path) -> "LocalConfig":
        """Load local config from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**(data or {}))

    model_config = ConfigDict(use_enum_values=True)


@dataclass
class DocumentMetadata:
    """Metadata for a Confluence document."""

    title: str
    page_id: Optional[str] = None
    space_key: Optional[str] = None
    parent_page_id: Optional[str] = None
    version: str = "1.0"
    owner: Optional[str] = None
    audience: list[str] = field(default_factory=list)
    status: str = "draft"
    labels: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    source_repos: list[str] = field(default_factory=list)
    source_hash: Optional[str] = None

    def content_hash(self) -> str:
        """Generate hash of metadata for change detection."""
        content = f"{self.title}|{self.version}|{self.status}|{','.join(sorted(self.labels))}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class DocumentChange:
    """Represents a change to a document."""

    document_id: str
    title: str
    action: str  # create, update, merge
    changes_made: list[str] = field(default_factory=list)
    metadata_before: Optional[DocumentMetadata] = None
    metadata_after: Optional[DocumentMetadata] = None
    dry_run: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def summary(self) -> str:
        """Generate summary of changes."""
        summary_lines = [f"{self.action.upper()}: {self.title}"]
        if self.changes_made:
            summary_lines.append(f"  Changes: {', '.join(self.changes_made)}")
        if self.dry_run:
            summary_lines.append("  [DRY RUN - NOT APPLIED]")
        return "\n".join(summary_lines)


@dataclass
class ValidationError:
    """Represents a validation error."""

    level: str  # error, warning, info
    field: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class DocumentGenerationResult:
    """Result of document generation operation."""

    success: bool
    document_id: Optional[str] = None
    document_url: Optional[str] = None
    title: Optional[str] = None
    changes: list[DocumentChange] = field(default_factory=list)
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    content_preview: Optional[str] = None
    dry_run: bool = True
    duration_seconds: float = 0.0

    def has_errors(self) -> bool:
        """Check if generation had errors."""
        return any(e.level == "error" for e in self.errors)

    def summary(self) -> str:
        """Generate summary of result."""
        lines = []
        if self.success:
            lines.append(f"✅ Document '{self.title}' generated successfully")
            if self.document_url:
                lines.append(f"   URL: {self.document_url}")
        else:
            lines.append(f"❌ Generation failed")

        if self.errors:
            lines.append(f"  Errors ({len(self.errors)}):")
            for err in self.errors[:5]:
                lines.append(f"    - {err.field}: {err.message}")

        if self.warnings:
            lines.append(f"  Warnings ({len(self.warnings)}):")
            for warn in self.warnings[:5]:
                lines.append(f"    - {warn.field}: {warn.message}")

        if self.dry_run:
            lines.append("  [DRY RUN MODE]")

        lines.append(f"  Duration: {self.duration_seconds:.2f}s")
        return "\n".join(lines)
