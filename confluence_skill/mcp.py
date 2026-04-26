"""MCP (Model Context Protocol) server for Confluence skill.

This module exposes the Confluence skill as an MCP server for use with:
- Claude Desktop
- Claude Code (IDE extension)
- claude.ai

The server handles tool calls and returns structured results back to Claude.
"""

import json
import sys
from typing import Any

from .skill import ConfluenceSkill
from .models import (
    SkillConfig,
    ConfluenceConfig,
    DocumentationConfig,
    MetadataConfig,
    JiraConfig,
)


def get_default_config(repo_path: str = ".") -> SkillConfig:
    """Get default skill configuration.
    
    Can be overridden by .confluence.yaml in the repository.
    """
    confluence = ConfluenceConfig(
        instance_url="https://darkmothcreative.atlassian.net",
        space_key="Engineering",
        auth_token_env="CONFLUENCE_TOKEN"
    )

    documentation = DocumentationConfig(
        space_key="Engineering",
        auto_title=True,
        metadata=MetadataConfig(
            owner="craig",
            audience=["engineers"]
        )
    )

    jira = JiraConfig(
        enabled=True,
        instance_url="https://darkmothcreative.atlassian.net",
        auth_token_env="JIRA_TOKEN",
        default_project="TPC",
        auto_link_related=True,
        create_tasks_for_gaps=True,
    )

    return SkillConfig(
        confluence=confluence,
        documentation=documentation,
        jira=jira
    )


TOOLS = [
    {
        "name": "confluence_document",
        "description": "Generate documentation from code repositories and publish to Confluence. Automatically uses repo's .confluence.yaml for space and Jira project binding.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "What to document (e.g., 'Document the payment API', 'Create architecture decision record')"
                },
                "repo_path": {
                    "type": "string",
                    "description": "Repository path. Use '.' for current repo. Will load .confluence.yaml for bindings.",
                    "default": "."
                },
                "doc_type": {
                    "type": "string",
                    "enum": ["api", "architecture", "runbook", "adr", "feature", "infrastructure", "troubleshooting", "custom"],
                    "description": "Documentation template type"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Preview changes without writing to Confluence",
                    "default": True
                }
            },
            "required": ["task"]
        }
    },
    {
        "name": "confluence_search",
        "description": "Search for pages in a Confluence space by title or content",
        "input_schema": {
            "type": "object",
            "properties": {
                "space_key": {
                    "type": "string",
                    "description": "Confluence space key (e.g., 'Engineering', 'terrorgems', 'Hoad-cloud-platforms')"
                },
                "query": {
                    "type": "string",
                    "description": "Search query (matches title or content)",
                    "default": ""
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 50
                }
            },
            "required": ["space_key"]
        }
    },
    {
        "name": "confluence_archive",
        "description": "Archive a Confluence page safely (preferred over deletion)",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "Confluence page ID"
                }
            },
            "required": ["page_id"]
        }
    }
]


def process_document(tool_input: dict[str, Any]) -> dict[str, Any]:
    """Process confluence_document tool call."""
    try:
        repo_path = tool_input.get("repo_path", ".")
        config = get_default_config(repo_path)
        skill = ConfluenceSkill(config)

        result = skill.document(
            task=tool_input["task"],
            repo_path=repo_path,
            doc_type=tool_input.get("doc_type"),
            dry_run=tool_input.get("dry_run", True)
        )

        return {
            "success": result.success,
            "title": result.title,
            "document_url": result.document_url,
            "document_id": result.document_id,
            "preview": result.content_preview[:500] if result.content_preview else None,
            "duration_seconds": result.duration_seconds,
            "error_count": len(result.errors),
            "warning_count": len(result.warnings),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def process_search(tool_input: dict[str, Any]) -> dict[str, Any]:
    """Process confluence_search tool call."""
    try:
        config = get_default_config()
        skill = ConfluenceSkill(config)

        pages = skill.search_pages(
            space_key=tool_input["space_key"],
            query=tool_input.get("query", ""),
            limit=tool_input.get("limit", 50)
        )

        return {
            "success": True,
            "pages": [
                {
                    "id": p.get("id"),
                    "title": p.get("title"),
                    "type": p.get("type")
                }
                for p in pages
            ],
            "count": len(pages)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def process_archive(tool_input: dict[str, Any]) -> dict[str, Any]:
    """Process confluence_archive tool call."""
    try:
        config = get_default_config()
        skill = ConfluenceSkill(config)

        success = skill.archive_page(tool_input["page_id"])
        return {
            "success": success,
            "page_id": tool_input["page_id"],
            "message": "Page archived successfully" if success else "Failed to archive page"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def serve() -> None:
    """MCP server entry point.
    
    Listens for tool calls from Claude and returns results.
    """
    while True:
        try:
            line = input()
        except EOFError:
            break

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        tool_name = request.get("tool")
        tool_input = request.get("input", {})

        if tool_name == "confluence_document":
            result = process_document(tool_input)
        elif tool_name == "confluence_search":
            result = process_search(tool_input)
        elif tool_name == "confluence_archive":
            result = process_archive(tool_input)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        print(json.dumps(result))
        sys.stdout.flush()


if __name__ == "__main__":
    serve()
