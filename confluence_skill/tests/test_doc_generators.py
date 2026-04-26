"""Tests for document generators."""

import pytest

from skills.confluence.doc_generators import (
    APIDocGenerator,
    ArchitectureDocGenerator,
    RunbookDocGenerator,
    ADRDocGenerator,
    create_generator,
)
from skills.confluence.models import DocumentMetadata, DocumentTemplate


@pytest.fixture
def metadata():
    """Create sample metadata."""
    return DocumentMetadata(
        title="Test Documentation",
        owner="test-team",
        audience=["engineers"],
    )


def test_api_doc_generator(metadata, extracted_info):
    """Test API documentation generator."""
    generator = APIDocGenerator(metadata, extracted_info)
    content = generator.generate()

    assert "API Documentation" in content
    assert "Endpoints" in content
    assert "/users" in content


def test_api_doc_no_apis(metadata):
    """Test API generator with no extracted APIs."""
    generator = APIDocGenerator(metadata, {})
    content = generator.generate()

    assert "API Documentation" in content
    assert content  # Should still generate something


def test_architecture_doc_generator(metadata, extracted_info):
    """Test architecture documentation generator."""
    generator = ArchitectureDocGenerator(metadata, extracted_info)
    content = generator.generate()

    assert "Architecture Documentation" in content
    assert "System Architecture" in content
    assert "Dependencies" in content
    assert "requests" in content


def test_runbook_generator(metadata):
    """Test runbook documentation generator."""
    generator = RunbookDocGenerator(metadata)
    content = generator.generate()

    assert "Runbook" in content
    assert "Overview" in content
    assert "Prerequisites" in content
    assert "Troubleshooting Steps" in content
    assert "Escalation" in content


def test_adr_generator(metadata):
    """Test ADR documentation generator."""
    generator = ADRDocGenerator(metadata)
    content = generator.generate()

    assert "Architecture Decision Record" in content
    assert "Status" in content
    assert "Context" in content
    assert "Decision" in content
    assert "Consequences" in content


def test_metadata_in_content(metadata):
    """Test that metadata appears in generated content."""
    generator = APIDocGenerator(metadata)
    content = generator.generate()

    assert metadata.title in content or "Document Information" in content


def test_create_generator_api(metadata, extracted_info):
    """Test create_generator factory with API template."""
    generator = create_generator(
        DocumentTemplate.API,
        metadata,
        extracted_info,
    )
    assert isinstance(generator, APIDocGenerator)
    content = generator.generate()
    assert "API Documentation" in content


def test_create_generator_architecture(metadata, extracted_info):
    """Test create_generator factory with architecture template."""
    generator = create_generator(
        DocumentTemplate.ARCHITECTURE,
        metadata,
        extracted_info,
    )
    assert isinstance(generator, ArchitectureDocGenerator)


def test_create_generator_runbook(metadata):
    """Test create_generator factory with runbook template."""
    generator = create_generator(
        DocumentTemplate.RUNBOOK,
        metadata,
    )
    assert isinstance(generator, RunbookDocGenerator)


def test_create_generator_adr(metadata):
    """Test create_generator factory with ADR template."""
    generator = create_generator(
        DocumentTemplate.ADR,
        metadata,
    )
    assert isinstance(generator, ADRDocGenerator)


def test_storage_format_wrapping(metadata):
    """Test that content is wrapped in storage format."""
    generator = APIDocGenerator(metadata)
    content = generator.generate()

    # Should contain Confluence storage format markers
    assert "ac:structured-macro" in content
    assert "ac:name" in content


def test_metadata_section_generation(metadata):
    """Test metadata section generation."""
    generator = APIDocGenerator(metadata)
    content = generator.generate()

    assert "Document Information" in content
    assert metadata.owner in content or "test-team" in content
