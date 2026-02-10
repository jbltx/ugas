#!/usr/bin/env python3
"""Bump version and create a new Docusaurus docs version.

This script:
1. Regenerates docs from SPEC.md with versioned static asset paths
2. Copies SPEC.md and schemas to website/static/v<version>/
3. Creates a new Docusaurus docs version

Can be triggered via GitHub Actions.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Semantic version regex
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$")


def parse_semver(version: str) -> Tuple[int, int, int, Optional[str], Optional[str]]:
    """Parse a semantic version string."""
    match = SEMVER_RE.match(version)
    if not match:
        raise ValueError(f"Invalid semantic version: {version}")
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    prerelease = match.group(4)
    build = match.group(5)
    return major, minor, patch, prerelease, build


def format_semver(
    major: int,
    minor: int,
    patch: int,
    prerelease: Optional[str] = None,
    build: Optional[str] = None,
) -> str:
    """Format semantic version components into a string."""
    version = f"{major}.{minor}.{patch}"
    if prerelease:
        version += f"-{prerelease}"
    if build:
        version += f"+{build}"
    return version


def get_current_version(website_root: Path) -> Optional[str]:
    """Get the latest version from versions.json."""
    versions_file = website_root / "versions.json"
    if not versions_file.exists():
        return None
    versions = json.loads(versions_file.read_text())
    return versions[0] if versions else None


def bump_version(current: str, bump_type: str) -> str:
    """Bump version based on type (major, minor, patch)."""
    major, minor, patch, _, _ = parse_semver(current)
    if bump_type == "major":
        return format_semver(major + 1, 0, 0)
    elif bump_type == "minor":
        return format_semver(major, minor + 1, 0)
    elif bump_type == "patch":
        return format_semver(major, minor, patch + 1)
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> None:
    """Run a command and check for errors."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(result.returncode)
    if result.stdout:
        print(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bump version and create a new Docusaurus docs version"
    )
    parser.add_argument(
        "version",
        help="Version string (e.g., '1.1.0') or bump type ('major', 'minor', 'patch')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes",
    )
    args = parser.parse_args()

    # Resolve paths
    scripts_dir = Path(__file__).resolve().parent
    repo_root = scripts_dir.parent
    website_root = repo_root / "website"
    generate_script = scripts_dir / "generate_docusaurus_spec.py"

    # Determine target version
    if args.version in ("major", "minor", "patch"):
        current = get_current_version(website_root)
        if not current:
            print("Error: No existing version found. Please specify an explicit version.")
            sys.exit(1)
        target_version = bump_version(current, args.version)
        print(f"Bumping from {current} to {target_version}")
    else:
        # Validate explicit version
        try:
            parse_semver(args.version)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        target_version = args.version

    if args.dry_run:
        print(f"\nDry run - would create version {target_version}")
        print(f"  1. Regenerate docs with --version={target_version}")
        print(f"  2. Copy static assets to website/static/v{target_version}/")
        print(f"  3. Run: npm run docusaurus docs:version {target_version}")
        return

    print(f"\nCreating version {target_version}...")

    # Step 1: Regenerate docs with versioned paths
    print("\n[1/2] Regenerating docs with versioned static paths...")
    run_command(
        [sys.executable, str(generate_script), "--version", target_version],
        cwd=repo_root,
    )

    # Step 2: Create Docusaurus version
    print(f"\n[2/2] Creating Docusaurus version {target_version}...")
    run_command(
        ["npm", "run", "docusaurus", "docs:version", target_version],
        cwd=website_root,
    )

    print(f"\n✓ Version {target_version} created successfully!")
    print(f"  - Static assets: website/static/v{target_version}/")
    print(f"  - Versioned docs: website/versioned_docs/version-{target_version}/")


if __name__ == "__main__":
    main()
