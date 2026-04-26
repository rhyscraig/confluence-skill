#!/usr/bin/env python3
"""Sync version from git tags to _version.py and pyproject.toml.

This script is called as part of the release process to ensure version consistency.
It reads the current git tag and updates both _version.py and pyproject.toml.

Usage:
    python3 scripts/sync_version.py              # Auto-detect from git tags
    python3 scripts/sync_version.py --version 2.0.0  # Set explicit version
"""

import subprocess
import sys
import re
from pathlib import Path


def get_current_tag() -> str:
    """Get the current git tag (semantic version)."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().lstrip("v")
    except subprocess.CalledProcessError:
        print("No git tags found. Using default version 1.2.0")
        return "1.2.0"


def parse_version(version_str: str) -> tuple[int, int, int]:
    """Parse semantic version string into tuple.

    Args:
        version_str: Version string like "1.2.3" or "v1.2.3"

    Returns:
        Tuple of (major, minor, patch)

    Raises:
        ValueError: If version string is invalid
    """
    version_str = version_str.lstrip("v")
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def update_version_file(version: str) -> None:
    """Update _version.py with new version."""
    major, minor, patch = parse_version(version)

    version_file = Path(__file__).parent.parent / "confluence_skill" / "_version.py"
    content = f'''"""Version file - automatically updated by setuptools-scm.

Do not manually edit this file. It is generated from git tags using setuptools-scm.
See scripts/sync_version.py to regenerate this file.
"""

__version__ = "{version}"
__version_tuple__ = ({major}, {minor}, {patch})
'''
    version_file.write_text(content)
    print(f"✓ Updated {version_file} to version {version}")


def update_pyproject(version: str) -> None:
    """Update version in pyproject.toml."""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject.read_text()

    # Update version line
    updated = re.sub(
        r'version = "[^"]+"',
        f'version = "{version}"',
        content,
    )

    if updated == content:
        print(f"⚠ No version line found in pyproject.toml")
        return

    pyproject.write_text(updated)
    print(f"✓ Updated pyproject.toml to version {version}")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        version = sys.argv[2] if len(sys.argv) > 2 else None
        if not version:
            print("Error: --version requires a version argument")
            sys.exit(1)
    else:
        version = get_current_tag()

    try:
        parse_version(version)  # Validate format
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Syncing version: {version}")
    update_version_file(version)
    update_pyproject(version)
    print("✓ Version sync complete")


if __name__ == "__main__":
    main()
