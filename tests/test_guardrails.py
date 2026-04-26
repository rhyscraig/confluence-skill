"""Tests for guardrails and validation."""

import pytest

from skills.confluence.guardrails import GuardailValidator, ApprovalGate
from skills.confluence.models import GuardrailsConfig, DocumentMetadata


@pytest.fixture
def guardrails_config():
    """Create guardrails configuration."""
    return GuardrailsConfig(
        enabled=True,
        validate_metadata=True,
        required_metadata_fields=["owner", "audience"],
        deprecated_terms=["legacy", "deprecated"],
        max_document_size_kb=2000,
    )


@pytest.fixture
def validator(guardrails_config):
    """Create validator instance."""
    return GuardailValidator(guardrails_config)


def test_validator_creation(guardrails_config):
    """Test validator initialization."""
    validator = GuardailValidator(guardrails_config)
    assert validator.config == guardrails_config
    assert validator.errors == []
    assert validator.warnings == []


def test_validate_metadata_complete(validator, document_metadata):
    """Test validation of complete metadata."""
    result = validator.validate_metadata(document_metadata)
    assert result is True
    assert len(validator.errors) == 0


def test_validate_metadata_missing_owner(validator):
    """Test validation catches missing owner."""
    metadata = DocumentMetadata(
        title="Test Doc",
        owner=None,  # Missing owner
        audience=["engineers"],
    )

    result = validator.validate_metadata(metadata)
    assert result is False
    assert len(validator.errors) > 0
    assert any("owner" in str(e.message).lower() for e in validator.errors)


def test_validate_metadata_missing_audience(validator):
    """Test validation catches missing audience."""
    metadata = DocumentMetadata(
        title="Test Doc",
        owner="test-team",
        audience=[],  # Empty audience
    )

    result = validator.validate_metadata(metadata)
    assert result is False
    assert any("audience" in str(e.message).lower() for e in validator.errors)


def test_validate_metadata_deprecated_terms(validator, document_metadata):
    """Test validation detects deprecated terms."""
    document_metadata.title = "Legacy API Documentation"

    result = validator.validate_metadata(document_metadata)
    # Should still be valid but have warnings
    assert any("legacy" in str(w.message).lower() for w in validator.warnings)


def test_validate_content_size_warning(validator, document_metadata):
    """Test validation warns about large documents."""
    # Create content larger than limit (2MB)
    large_content = "<p>" + ("x" * 3000000) + "</p>"

    validator.validate_content(large_content, document_metadata)
    assert any("size" in str(w.message).lower() for w in validator.warnings)


def test_validate_content_deprecated_terms(validator, document_metadata):
    """Test validation detects deprecated terms in content."""
    content = "<p>This is legacy code that is now deprecated</p>"

    validator.validate_content(content, document_metadata)
    assert any("deprecated" in str(w.message).lower() for w in validator.warnings)


def test_validator_reset():
    """Test validator reset clears errors."""
    config = GuardrailsConfig()
    validator = GuardailValidator(config)

    # Add some errors
    from skills.confluence.models import ValidationError
    validator.errors = [ValidationError("error", "test", "Test error")]
    validator.warnings = [ValidationError("warning", "test", "Test warning")]

    # Reset
    validator.reset()
    assert validator.errors == []
    assert validator.warnings == []


def test_disabled_guardrails(document_metadata):
    """Test that disabled guardrails don't validate."""
    config = GuardrailsConfig(enabled=False)
    validator = GuardailValidator(config)

    # Create invalid metadata
    metadata = DocumentMetadata(
        title="Test",
        owner=None,  # Missing required field
    )

    result = validator.validate_metadata(metadata)
    assert result is True  # No validation since disabled


def test_approval_gate_no_approval_required():
    """Test approval gate when approval not required."""
    gate = ApprovalGate(require_approval=False)

    # Should always approve
    result = gate.request_approval("doc-1", "create", "Test doc")
    assert result is True


def test_approval_gate_non_interactive():
    """Test approval gate in non-interactive mode."""
    gate = ApprovalGate(require_approval=True, interactive=False)

    result = gate.request_approval("doc-1", "create", "Test doc")
    assert result is False


def test_approval_gate_caching():
    """Test approval gate caches approvals."""
    gate = ApprovalGate(require_approval=False)

    gate._approved.add("doc-1")

    # Second call should return cached approval
    result = gate.request_approval("doc-1", "update", "Test doc")
    assert result is True


def test_anchor_validation(validator):
    """Test anchor link validation."""
    metadata = DocumentMetadata(title="Test")

    # Content with missing anchor
    content = '<a href="#missing-anchor">Link</a>'

    validator.validate_content(content, metadata)
    # Should have error about missing anchor
    assert any("anchor" in str(e.message).lower() for e in validator.errors)


def test_summary_generation(validator, document_metadata):
    """Test validation summary generation."""
    validator.validate_metadata(document_metadata)

    summary = validator.get_summary()
    assert "✅" in summary  # Should show success


def test_summary_with_errors(validator):
    """Test summary with errors."""
    metadata = DocumentMetadata(title="Test", owner=None)

    validator.validate_metadata(metadata)
    summary = validator.get_summary()

    assert "❌" in summary or "Errors" in summary
