"""Tests for page hierarchy validation module."""

import pytest

from ..page_hierarchy import PageHierarchyConfig, PageHierarchyValidator


class TestPageHierarchyConfig:
    """Tests for PageHierarchyConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = PageHierarchyConfig()
        assert config.enforce_nesting is True
        assert config.max_depth == 3
        assert config.parent_page_only_for_roots is True
        assert config.aws_documentation_style is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = PageHierarchyConfig(
            enforce_nesting=False,
            max_depth=5,
            parent_page_only_for_roots=False,
            aws_documentation_style=False,
        )
        assert config.enforce_nesting is False
        assert config.max_depth == 5
        assert config.parent_page_only_for_roots is False
        assert config.aws_documentation_style is False


class TestPageHierarchyValidator:
    """Tests for PageHierarchyValidator."""

    def test_validator_with_default_config(self):
        """Test validator initialization with default config."""
        validator = PageHierarchyValidator()
        assert validator.config.enforce_nesting is True
        assert validator.config.max_depth == 3

    def test_validator_with_custom_config(self):
        """Test validator initialization with custom config."""
        config = PageHierarchyConfig(enforce_nesting=False)
        validator = PageHierarchyValidator(config)
        assert validator.config.enforce_nesting is False

    def test_validation_disabled(self):
        """Test that validation passes when disabled."""
        config = PageHierarchyConfig(enforce_nesting=False)
        validator = PageHierarchyValidator(config)

        valid, error = validator.validate_page_creation(
            title="Root Page",
            parent_page_id=None,
            children=None,
            is_root_level=True,
        )
        assert valid is True
        assert error is None

    def test_root_page_without_children_fails(self):
        """Test that root page without children fails validation."""
        validator = PageHierarchyValidator()

        valid, error = validator.validate_page_creation(
            title="Root Page",
            parent_page_id=None,
            children=None,
            is_root_level=True,
        )
        assert valid is False
        assert "without children" in error
        assert "Root Page" in error

    def test_root_page_with_children_passes(self):
        """Test that root page with children passes validation."""
        validator = PageHierarchyValidator()

        valid, error = validator.validate_page_creation(
            title="Root Page",
            parent_page_id=None,
            children=[{"title": "Child 1"}],
            is_root_level=True,
        )
        assert valid is True
        assert error is None

    def test_non_root_page_without_children_passes(self):
        """Test that non-root page without children passes validation."""
        validator = PageHierarchyValidator()

        valid, error = validator.validate_page_creation(
            title="Child Page",
            parent_page_id="page-123",
            children=None,
            is_root_level=False,
        )
        assert valid is True
        assert error is None

    def test_page_with_parent_and_children_fails(self):
        """Test that page with both parent and children fails."""
        validator = PageHierarchyValidator()

        valid, error = validator.validate_page_creation(
            title="Invalid Page",
            parent_page_id="page-123",
            children=[{"title": "Child 1"}],
            is_root_level=False,
        )
        assert valid is False
        assert "has parent_page_id but also specifies children" in error

    def test_parent_page_only_for_roots_disabled(self):
        """Test that root page without children passes when setting is disabled."""
        config = PageHierarchyConfig(parent_page_only_for_roots=False)
        validator = PageHierarchyValidator(config)

        valid, error = validator.validate_page_creation(
            title="Root Page",
            parent_page_id=None,
            children=None,
            is_root_level=True,
        )
        assert valid is True
        assert error is None

    def test_build_nested_structure_with_validation_disabled(self):
        """Test structure building with validation disabled."""
        config = PageHierarchyConfig(enforce_nesting=False)
        validator = PageHierarchyValidator(config)

        pages = [
            {"title": "Page A"},
            {"title": "Page B"},
        ]
        result = validator.build_nested_structure(pages)
        assert len(result) == 2

    def test_build_nested_structure_respects_dependencies(self):
        """Test that build_nested_structure respects parent dependencies."""
        validator = PageHierarchyValidator()

        pages = [
            {"title": "Child", "parent_page_title": "Parent"},
            {"title": "Parent"},
        ]
        result = validator.build_nested_structure(pages)

        # Parent should come before child
        assert result[0]["title"] == "Parent"
        assert result[1]["title"] == "Child"

    def test_build_nested_structure_detects_circular_dependency(self):
        """Test that circular dependencies are detected."""
        validator = PageHierarchyValidator()

        pages = [
            {"title": "Page A", "parent_page_title": "Page B"},
            {"title": "Page B", "parent_page_title": "Page A"},
        ]

        with pytest.raises(ValueError, match="Circular"):
            validator.build_nested_structure(pages)

    def test_build_nested_structure_detects_missing_parent(self):
        """Test that missing parent pages are detected."""
        validator = PageHierarchyValidator()

        pages = [
            {"title": "Child", "parent_page_title": "NonexistentParent"},
        ]

        with pytest.raises(ValueError, match="not found"):
            validator.build_nested_structure(pages)

    def test_build_nested_structure_detects_depth_exceeded(self):
        """Test that max depth exceeded is detected."""
        validator = PageHierarchyValidator()

        pages = [
            {"title": "Root"},
            {"title": "L1", "parent_page_title": "Root"},
            {"title": "L2", "parent_page_title": "L1"},
            {"title": "L3", "parent_page_title": "L2"},
            {"title": "L4", "parent_page_title": "L3"},  # Exceeds max depth of 3
        ]

        with pytest.raises(ValueError, match="exceeds max depth"):
            validator.build_nested_structure(pages)

    def test_validate_tree_structure_passes(self):
        """Test tree validation passes for valid structure."""
        validator = PageHierarchyValidator()

        tree = {
            "title": "Root",
            "children": [
                {
                    "title": "Child1",
                    "children": [{"title": "Grandchild1", "children": []}],
                },
                {"title": "Child2", "children": []},
            ],
        }

        valid, error = validator.validate_tree_structure(tree)
        assert valid is True
        assert error is None

    def test_validate_tree_structure_fails_on_depth(self):
        """Test tree validation fails when max depth exceeded."""
        validator = PageHierarchyValidator()

        tree = {
            "title": "Root",
            "children": [
                {
                    "title": "L1",
                    "children": [
                        {
                            "title": "L2",
                            "children": [
                                {
                                    "title": "L3",
                                    "children": [{"title": "L4", "children": []}],
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        valid, error = validator.validate_tree_structure(tree)
        assert valid is False
        assert "exceeds max depth" in error

    def test_get_hierarchy_info_depth_and_count(self):
        """Test getting hierarchy information."""
        validator = PageHierarchyValidator()

        tree = {
            "title": "Root",
            "children": [
                {
                    "title": "Child1",
                    "children": [{"title": "Grandchild1", "children": []}],
                },
                {"title": "Child2", "children": []},
            ],
        }

        info = validator.get_hierarchy_info(tree)
        assert info["max_depth"] == 3
        assert info["total_pages"] == 4
        assert info["exceeds_max"] is False
        assert info["exceeds_max_by"] == 0

    def test_get_hierarchy_info_exceeds_max(self):
        """Test hierarchy info when max depth exceeded."""
        validator = PageHierarchyValidator()

        tree = {
            "title": "Root",
            "children": [
                {
                    "title": "L1",
                    "children": [
                        {
                            "title": "L2",
                            "children": [
                                {
                                    "title": "L3",
                                    "children": [{"title": "L4", "children": []}],
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        info = validator.get_hierarchy_info(tree)
        assert info["max_depth"] == 5
        assert info["total_pages"] == 5
        assert info["exceeds_max"] is True
        assert info["exceeds_max_by"] == 2
