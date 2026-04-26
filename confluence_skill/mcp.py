"""MCP (Model Context Protocol) server for Confluence Skill.

This module implements the MCP server protocol, exposing Confluence Skill
functionality to Claude and other MCP clients.

The server exposes three main tools:
- confluence_document: Generate and publish documentation
- confluence_search: Search for pages in Confluence
- confluence_archive: Archive pages safely
"""

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from confluence_skill.skill import ConfluenceSkill
from confluence_skill.models import SkillConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
server = Server("confluence-skill")


def get_default_config() -> SkillConfig:
    """Get default Confluence Skill configuration.

    Returns:
        SkillConfig: Configuration loaded from environment or defaults
    """
    try:
        return SkillConfig.from_yaml(".confluence.yaml")
    except FileNotFoundError:
        logger.warning("No .confluence.yaml found, using environment variables only")
        return SkillConfig.from_env()


# Define tools
TOOLS: list[dict[str, Any]] = [
    {
        "name": "confluence_document",
        "description": "Generate documentation from code repositories and publish to Confluence",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Documentation task or prompt"},
                "doc_type": {
                    "type": "string",
                    "enum": ["api", "architecture", "adr", "runbook", "feature", "infrastructure", "troubleshooting", "custom"],
                    "description": "Type of documentation to generate",
                },
                "repo_path": {"type": "string", "description": "Path to code repository"},
                "dry_run": {"type": "boolean", "description": "Preview only, don't publish", "default": True},
            },
            "required": ["task", "doc_type"],
        },
    },
    {
        "name": "confluence_search",
        "description": "Search for pages in a Confluence space by title or content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "space_key": {"type": "string", "description": "Confluence space key (optional)"},
                "max_results": {"type": "integer", "description": "Maximum results to return", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "confluence_archive",
        "description": "Archive a Confluence page safely (preferred over deletion)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Confluence page ID"},
                "reason": {"type": "string", "description": "Reason for archival"},
            },
            "required": ["page_id"],
        },
    },
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools.

    Returns:
        List of Tool objects describing available operations
    """
    return [
        Tool(
            name=tool["name"],
            description=tool["description"],
            inputSchema=tool["inputSchema"],
        )
        for tool in TOOLS
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls from Claude.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        Tool result with output and any errors
    """
    try:
        config = get_default_config()
        skill = ConfluenceSkill(config)

        if name == "confluence_document":
            task = arguments.get("task", "")
            doc_type = arguments.get("doc_type", "api")
            repo_path = arguments.get("repo_path", ".")
            dry_run = arguments.get("dry_run", True)

            result = skill.document(
                task=task,
                doc_type=doc_type,
                repo_path=repo_path,
                dry_run=dry_run,
            )
            return [TextContent(type="text", text=result.summary)]

        elif name == "confluence_search":
            query = arguments.get("query", "")
            space_key = arguments.get("space_key")
            max_results = arguments.get("max_results", 10)

            pages = skill.search_pages(
                query=query,
                space_key=space_key,
            )

            # Format results
            results_text = f"Found {len(pages)} pages:\n"
            for page in pages[:max_results]:
                results_text += f"- {page.get('title', 'Untitled')} (ID: {page.get('id')})\n"

            return [TextContent(type="text", text=results_text)]

        elif name == "confluence_archive":
            page_id = arguments.get("page_id", "")
            reason = arguments.get("reason", "Archived by automation")

            result = skill.archive_page(page_id=page_id)

            return [
                TextContent(
                    type="text",
                    text=f"Successfully archived page {page_id}. Reason: {reason}",
                )
            ]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [TextContent(type="text", text=error_msg)]


async def serve() -> None:
    """Run the MCP server.

    This function starts the server and listens for requests from Claude
    or other MCP clients. It should be called as the main entry point.
    """
    async with server:
        logger.info("Confluence Skill MCP server started")
        await server.wait()


if __name__ == "__main__":
    import asyncio

    asyncio.run(serve())
