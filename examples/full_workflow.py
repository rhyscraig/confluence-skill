"""Complete Confluence skill workflow example.

This example demonstrates:
1. Configuration loading and merging
2. Documentation generation
3. Jira integration
4. Page search and management
"""

from pathlib import Path
from skills.confluence import ConfluenceSkill
from skills.confluence.models import SkillConfig, LocalConfig


def main():
    """Complete workflow example."""
    # Step 1: Load central configuration
    print("1. Loading configuration...")
    config = SkillConfig.from_yaml(Path.home() / ".confluence.yaml")
    
    # Step 2: Merge with local repo configuration
    print("2. Merging with local config...")
    local_config = LocalConfig.from_yaml(".confluence.yaml")
    merged_config = config.merge(local_config)
    
    # Step 3: Create skill instance
    print("3. Creating Confluence skill...")
    skill = ConfluenceSkill(merged_config)
    
    # Step 4: Generate documentation
    print("4. Generating documentation...")
    doc_result = skill.document(
        task="Document the order processing system",
        doc_type="architecture",
        dry_run=False  # Actually write to Confluence
    )
    
    if doc_result.success:
        print(f"✅ Created: {doc_result.title}")
        print(f"   URL: {doc_result.document_url}")
    else:
        print(f"❌ Failed: {doc_result.errors}")
        return
    
    # Step 5: Search for related pages
    print("\n5. Searching for related pages...")
    pages = skill.search_pages(
        space_key=merged_config.documentation.space_key,
        query="API",
        limit=10
    )
    
    print(f"   Found {len(pages)} pages")
    for page in pages[:3]:
        print(f"   - {page['title']}")
    
    # Step 6: Add labels to documentation
    print("\n6. Adding labels...")
    label_result = skill.bulk_label_pages(
        space_key=merged_config.documentation.space_key,
        query="architecture",
        labels=["auto-generated", "updated"]
    )
    
    print(f"   Labeled: {label_result['success']} pages")


if __name__ == "__main__":
    main()
