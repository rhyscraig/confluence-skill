"""Page hierarchy validation and nesting enforcement for Confluence skill."""

from dataclasses import dataclass
from typing import Any


@dataclass
class PageHierarchyConfig:
    """Configuration for page hierarchy validation."""

    enforce_nesting: bool = True
    max_depth: int = 3
    parent_page_only_for_roots: bool = True
    aws_documentation_style: bool = True


class PageHierarchyValidator:
    """Validates and enforces proper page nesting hierarchies."""

    def __init__(self, config: PageHierarchyConfig | None = None):
        """Initialize validator.

        Args:
            config: Hierarchy configuration
        """
        self.config = config or PageHierarchyConfig()

    def validate_page_creation(
        self,
        title: str,
        parent_page_id: str | None = None,
        children: list[dict[str, Any]] | None = None,
        is_root_level: bool = True,
    ) -> tuple[bool, str | None]:
        """Validate page creation request.

        Args:
            title: Page title
            parent_page_id: Parent page ID (None if root level)
            children: List of child pages to be created
            is_root_level: Whether this is a root-level page

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.config.enforce_nesting:
            return True, None

        # Root-level pages must have children if configured
        if is_root_level and self.config.parent_page_only_for_roots:
            if parent_page_id is None and not children:
                return (
                    False,
                    f"Cannot create root-level page '{title}' without children. "
                    "Root pages must be parent pages with child pages nested underneath. "
                    "Specify parent_page_id or provide children list.",
                )

        # Pages with parent_id cannot have children_ids (non-root pages)
        # Parent relationships are only specified when creating child pages
        if parent_page_id and children:
            return (
                False,
                f"Page '{title}' has parent_page_id but also specifies children. "
                "Only root-level parent pages can have children.",
            )

        return True, None

    def build_nested_structure(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build creation order respecting parent-child dependencies.

        Args:
            pages: List of page configs with parent_page_title references

        Returns:
            Flattened list in creation order (parents first)

        Raises:
            ValueError: If hierarchy is invalid
        """
        if not self.config.enforce_nesting:
            return pages

        # Build parent-child relationships
        pages_by_title = {p.get("title"): p for p in pages}
        creation_order = []
        visited = set()
        in_progress = set()

        def get_depth(page_title: str, path: set[str] | None = None) -> int:
            """Calculate depth of a page by counting ancestors."""
            if path is None:
                path = set()

            if page_title in path:
                raise ValueError(f"Circular parent-child relationship detected with page '{page_title}'")

            depth = 1
            parent_title = pages_by_title.get(page_title, {}).get("parent_page_title")
            if parent_title:
                path.add(page_title)
                depth += get_depth(parent_title, path)
                path.discard(page_title)
            return depth

        def add_page_and_dependencies(page_title: str) -> None:
            """Recursively add page and its dependencies to creation order."""
            if page_title in visited:
                return

            if page_title in in_progress:
                raise ValueError(f"Circular parent-child relationship detected with page '{page_title}'")

            in_progress.add(page_title)
            page = pages_by_title.get(page_title)

            if not page:
                raise ValueError(f"Page '{page_title}' referenced but not found in pages list")

            # Check depth
            depth = get_depth(page_title)
            if depth > self.config.max_depth:
                raise ValueError(
                    f"Page '{page_title}' at depth {depth} exceeds max depth {self.config.max_depth}. "
                    "Maximum 3 levels: Root → Parent → Section → Details"
                )

            # Add parent first if specified
            parent_title = page.get("parent_page_title")
            if parent_title:
                add_page_and_dependencies(parent_title)

            in_progress.remove(page_title)
            visited.add(page_title)
            creation_order.append(page)

        # Build creation order
        for page in pages:
            add_page_and_dependencies(page.get("title"))

        return creation_order

    def validate_tree_structure(self, page_tree: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate complete page tree structure.

        Args:
            page_tree: Hierarchical page structure

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.config.enforce_nesting:
            return True, None

        def check_depth(node: dict[str, Any], depth: int = 1) -> tuple[bool, str | None]:
            """Check depth of node and children."""
            if depth > self.config.max_depth:
                return (
                    False,
                    f"Page tree exceeds max depth {self.config.max_depth}. "
                    f"Page '{node.get('title')}' at depth {depth}.",
                )

            children = node.get("children", [])
            for child in children:
                valid, error = check_depth(child, depth + 1)
                if not valid:
                    return valid, error

            return True, None

        return check_depth(page_tree)

    def get_hierarchy_info(self, page_tree: dict[str, Any]) -> dict[str, Any]:
        """Get information about page hierarchy.

        Args:
            page_tree: Hierarchical page structure

        Returns:
            Dictionary with hierarchy info
        """

        def count_depths(node: dict[str, Any], depth: int = 1) -> tuple[int, int]:
            """Count max depth and total pages."""
            max_d = depth
            total = 1
            for child in node.get("children", []):
                child_max, child_total = count_depths(child, depth + 1)
                max_d = max(max_d, child_max)
                total += child_total
            return max_d, total

        max_depth, total_pages = count_depths(page_tree)

        return {
            "max_depth": max_depth,
            "total_pages": total_pages,
            "exceeds_max": max_depth > self.config.max_depth,
            "exceeds_max_by": max(0, max_depth - self.config.max_depth),
        }
