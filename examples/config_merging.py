"""Configuration merging example.

This shows how the Confluence skill handles:
1. Central configuration
2. Local repository overrides
3. Configuration validation
"""

from skills.confluence.models import (
    SkillConfig,
    LocalConfig,
    DocumentationConfig,
    JiraConfig,
)


def main():
    """Demonstrate configuration merging."""
    # Central configuration (organization-wide)
    central = SkillConfig.from_yaml("~/.confluence.yaml")
    print(f"Central space: {central.documentation.space_key}")
    print(f"Jira project: {central.jira.default_project}")
    
    # Local configuration (repo-specific)
    local = LocalConfig(
        documentation=DocumentationConfig(
            space_key="CustomSpace"
        ),
        jira=JiraConfig(
            default_project="LOCAL"
        )
    )
    print(f"\nLocal overrides:")
    print(f"  Space: {local.documentation.space_key}")
    print(f"  Project: {local.jira.default_project}")
    
    # Merge: local overrides central
    merged = central.merge(local)
    print(f"\nMerged result:")
    print(f"  Space: {merged.documentation.space_key}")
    print(f"  Project: {merged.jira.default_project}")
    
    # Validation
    errors = merged.validate_required_fields()
    if errors:
        print(f"\nValidation errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✅ Configuration valid!")


if __name__ == "__main__":
    main()
