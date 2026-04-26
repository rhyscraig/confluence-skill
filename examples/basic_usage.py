"""Basic usage example of the Confluence skill.

This example shows:
1. Loading configuration
2. Creating a ConfluenceSkill instance
3. Generating documentation in dry-run mode
"""

from confluence_skill import ConfluenceSkill
from confluence_skill.models import SkillConfig


def main():
    """Generate basic documentation."""
    # Load configuration from .confluence.yaml or use defaults
    config = SkillConfig.from_yaml(".confluence.yaml")
    
    # Create skill instance
    skill = ConfluenceSkill(config)
    
    # Generate documentation (dry-run mode - no changes to Confluence)
    result = skill.document(
        task="Document the payment API",
        doc_type="api",
        dry_run=True  # Preview only
    )
    
    # Print results
    print(result.summary())
    
    if result.success:
        print(f"\nPreview:\n{result.content_preview}")
    else:
        print(f"\nErrors: {[e.message for e in result.errors]}")


if __name__ == "__main__":
    main()
