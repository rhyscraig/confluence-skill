"""Template-based documentation generation."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from .models import DocumentTemplate, DocumentMetadata


class DocGenerator(ABC):
    """Base class for document generators."""

    def __init__(self, metadata: DocumentMetadata, extracted_info: Optional[dict] = None):
        """Initialize generator.

        Args:
            metadata: Document metadata
            extracted_info: Extracted code/content information
        """
        self.metadata = metadata
        self.extracted_info = extracted_info or {}

    @abstractmethod
    def generate(self) -> str:
        """Generate document body.

        Returns:
            Document body in Confluence storage format
        """
        pass

    def _wrap_storage(self, html: str) -> str:
        """Wrap HTML in Confluence storage format.

        Args:
            html: HTML content

        Returns:
            Confluence storage format
        """
        return f"""<ac:structured-macro ac:name="info">
  <ac:parameter ac:name="icon">true</ac:parameter>
  <ac:rich-text-body>
    <p><em>Auto-generated on {datetime.utcnow().isoformat()} by Confluence Skill</em></p>
  </ac:rich-text-body>
</ac:structured-macro>
{html}"""

    def _add_metadata_section(self) -> str:
        """Generate metadata section.

        Returns:
            HTML for metadata
        """
        parts = []
        parts.append("<h2>Document Information</h2>")
        parts.append("<table><tbody>")

        if self.metadata.owner:
            parts.append(f"<tr><td><strong>Owner</strong></td><td>{self.metadata.owner}</td></tr>")

        if self.metadata.audience:
            audience_str = ", ".join(self.metadata.audience)
            parts.append(f"<tr><td><strong>Audience</strong></td><td>{audience_str}</td></tr>")

        if self.metadata.status:
            parts.append(f"<tr><td><strong>Status</strong></td><td>{self.metadata.status}</td></tr>")

        if self.metadata.version:
            parts.append(f"<tr><td><strong>Version</strong></td><td>{self.metadata.version}</td></tr>")

        parts.append("</tbody></table>")
        return "\n".join(parts)


class APIDocGenerator(DocGenerator):
    """Generator for API documentation."""

    def generate(self) -> str:
        """Generate API documentation."""
        parts = ["<h1>API Documentation</h1>"]

        # Metadata
        parts.append(self._add_metadata_section())

        # API Endpoints
        apis = self.extracted_info.get("apis", [])
        if apis:
            parts.append("<h2>Endpoints</h2>")
            parts.append("<table><tbody>")
            parts.append("<tr><th>Method</th><th>Path</th><th>File</th></tr>")

            for api in apis:
                method = api.get("method", "GET").upper()
                path = api.get("path", "")
                file_ref = api.get("file", "")
                parts.append(f"<tr><td><code>{method}</code></td><td><code>{path}</code></td><td>{file_ref}</td></tr>")

            parts.append("</tbody></table>")

        return self._wrap_storage("\n".join(parts))


class ArchitectureDocGenerator(DocGenerator):
    """Generator for architecture documentation."""

    def generate(self) -> str:
        """Generate architecture documentation."""
        parts = ["<h1>Architecture Documentation</h1>"]

        # Metadata
        parts.append(self._add_metadata_section())

        # Architecture Info
        arch = self.extracted_info.get("architecture", [])
        if arch:
            parts.append("<h2>System Architecture</h2>")
            for item in arch:
                if item.get("type") == "file_structure":
                    parts.append(f"<p>{item.get('summary', '')}</p>")

        # Dependencies
        deps = self.extracted_info.get("dependencies", [])
        if deps:
            parts.append("<h2>Dependencies</h2>")
            parts.append("<ul>")
            for dep in deps[:20]:  # Limit to first 20
                parts.append(f"<li>{dep.get('name', '')} ({dep.get('spec', '')})</li>")
            parts.append("</ul>")

        return self._wrap_storage("\n".join(parts))


class RunbookDocGenerator(DocGenerator):
    """Generator for runbook documentation."""

    def generate(self) -> str:
        """Generate runbook documentation."""
        parts = ["<h1>Runbook</h1>"]

        # Metadata
        parts.append(self._add_metadata_section())

        parts.append("<h2>Overview</h2>")
        parts.append("<p>This is a runbook template. Please fill in the sections below.</p>")

        parts.append("<h2>Prerequisites</h2>")
        parts.append("<ul><li>List prerequisites here</li></ul>")

        parts.append("<h2>Troubleshooting Steps</h2>")
        parts.append("<ol><li>Step 1</li><li>Step 2</li><li>Step 3</li></ol>")

        parts.append("<h2>Escalation</h2>")
        parts.append("<p>If steps above don't resolve the issue, escalate to:</p>")
        parts.append("<ul><li>Escalation point</li></ul>")

        return self._wrap_storage("\n".join(parts))


class ADRDocGenerator(DocGenerator):
    """Generator for Architecture Decision Records."""

    def generate(self) -> str:
        """Generate ADR documentation."""
        parts = ["<h1>Architecture Decision Record</h1>"]

        # Metadata
        parts.append(self._add_metadata_section())

        parts.append("<h2>Status</h2>")
        parts.append(f"<p><strong>{self.metadata.status.upper()}</strong></p>")

        parts.append("<h2>Context</h2>")
        parts.append("<p>The issue motivating this decision and any context that influences or constrains the decision.</p>")

        parts.append("<h2>Decision</h2>")
        parts.append("<p>The change that we're proposing or have agreed to do.</p>")

        parts.append("<h2>Consequences</h2>")
        parts.append("<p>What becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated.</p>")

        return self._wrap_storage("\n".join(parts))


class FeatureDocGenerator(DocGenerator):
    """Generator for feature documentation."""

    def generate(self) -> str:
        """Generate feature documentation."""
        parts = ["<h1>Feature Documentation</h1>"]

        # Metadata
        parts.append(self._add_metadata_section())

        parts.append("<h2>Overview</h2>")
        parts.append("<p>Brief description of the feature.</p>")

        parts.append("<h2>Use Cases</h2>")
        parts.append("<ul><li>Use case 1</li><li>Use case 2</li></ul>")

        parts.append("<h2>Implementation Details</h2>")
        parts.append("<p>Technical details of the implementation.</p>")

        # Include extracted APIs if available
        apis = self.extracted_info.get("apis", [])
        if apis:
            parts.append("<h2>API Endpoints</h2>")
            parts.append("<ul>")
            for api in apis[:10]:
                method = api.get("method", "GET")
                path = api.get("path", "")
                parts.append(f"<li><code>{method} {path}</code></li>")
            parts.append("</ul>")

        return self._wrap_storage("\n".join(parts))


class InfrastructureDocGenerator(DocGenerator):
    """Generator for infrastructure documentation."""

    def generate(self) -> str:
        """Generate infrastructure documentation."""
        parts = ["<h1>Infrastructure Documentation</h1>"]

        # Metadata
        parts.append(self._add_metadata_section())

        parts.append("<h2>System Architecture</h2>")
        parts.append("<p>Diagram and description of the infrastructure.</p>")

        # Dependencies as infrastructure components
        deps = self.extracted_info.get("dependencies", [])
        if deps:
            parts.append("<h2>Components</h2>")
            parts.append("<ul>")
            for dep in deps[:20]:
                parts.append(f"<li>{dep.get('name', '')} - {dep.get('spec', '')}</li>")
            parts.append("</ul>")

        parts.append("<h2>Deployment</h2>")
        parts.append("<p>Deployment steps and procedures.</p>")

        parts.append("<h2>Monitoring</h2>")
        parts.append("<p>Monitoring and alerting configuration.</p>")

        return self._wrap_storage("\n".join(parts))


class TroubleshootingDocGenerator(DocGenerator):
    """Generator for troubleshooting guide."""

    def generate(self) -> str:
        """Generate troubleshooting guide."""
        parts = ["<h1>Troubleshooting Guide</h1>"]

        # Metadata
        parts.append(self._add_metadata_section())

        parts.append("<h2>Common Issues</h2>")
        parts.append("<h3>Issue 1: [Issue Name]</h3>")
        parts.append("<p><strong>Symptoms:</strong> Description of what happens</p>")
        parts.append("<p><strong>Root Cause:</strong> Why this happens</p>")
        parts.append("<p><strong>Resolution:</strong> Steps to fix</p>")

        parts.append("<h2>Debug Tips</h2>")
        parts.append("<ul><li>Useful debug commands</li><li>Log locations</li></ul>")

        parts.append("<h2>Getting Help</h2>")
        parts.append("<p>If issues persist, contact the team or open an issue.</p>")

        return self._wrap_storage("\n".join(parts))


class CustomDocGenerator(DocGenerator):
    """Generator for custom documentation."""

    def generate(self) -> str:
        """Generate custom documentation."""
        parts = ["<h1>" + self.metadata.title + "</h1>"]

        # Metadata
        parts.append(self._add_metadata_section())

        parts.append("<h2>Content</h2>")
        parts.append("<p>Custom documentation content goes here.</p>")

        return self._wrap_storage("\n".join(parts))


def create_generator(
    template: DocumentTemplate,
    metadata: DocumentMetadata,
    extracted_info: Optional[dict] = None,
) -> DocGenerator:
    """Factory function to create appropriate document generator.

    Args:
        template: Document template type
        metadata: Document metadata
        extracted_info: Extracted code/content information

    Returns:
        Appropriate DocGenerator instance
    """
    generators = {
        DocumentTemplate.API: APIDocGenerator,
        DocumentTemplate.ARCHITECTURE: ArchitectureDocGenerator,
        DocumentTemplate.RUNBOOK: RunbookDocGenerator,
        DocumentTemplate.ADR: ADRDocGenerator,
        DocumentTemplate.FEATURE: FeatureDocGenerator,
        DocumentTemplate.INFRASTRUCTURE: InfrastructureDocGenerator,
        DocumentTemplate.TROUBLESHOOTING: TroubleshootingDocGenerator,
        DocumentTemplate.CUSTOM: CustomDocGenerator,
    }

    generator_class = generators.get(template, CustomDocGenerator)
    return generator_class(metadata, extracted_info)
