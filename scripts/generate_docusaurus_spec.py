#!/usr/bin/env python3
"""Generate Docusaurus docs from SPEC.md.

Creates a docs/spec/ tree with categories per Part/Appendix and one page per
section, preserving original content.

During script execution, all relative URLs to YAML/JSON files are replaced
by raw-loader imports for Docusaurus MDX.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Dict


PART_HEADING_RE = re.compile(r"^#\s+(Part\s+[IVXLC]+:\s+.+|Appendices)\s*$")
SECTION_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
TITLE_HEADING_RE = re.compile(r"^#\s+(.+?)\s*$")
# Matches markdown links to .yaml or .json files: [text](path/to/file.yaml)
YAML_JSON_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+\.(?:yaml|json))\)")


def slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "section"


def path_to_import_name(file_path: str) -> str:
    """Convert a file path to a valid JavaScript import variable name."""
    # Get just the filename without directory
    name = Path(file_path).name
    # Replace dots and dashes with underscores
    name = re.sub(r"[.\-]", "_", name)
    # Ensure it starts with a letter
    if name and name[0].isdigit():
        name = "file_" + name
    return name


def process_yaml_json_links(
    content: str, part_slug: str, version: Optional[str] = None
) -> Tuple[str, List[str], bool]:
    """
    Process content to replace YAML/JSON links with raw-loader imports.

    Args:
        content: The markdown content to process
        part_slug: The slug of the current part (unused but kept for signature compatibility)
        version: Optional version string (e.g., "1.0.0"). If None, uses unversioned path.

    Returns:
        Tuple of (processed_content, import_statements, has_imports)
    """
    matches = list(YAML_JSON_LINK_RE.finditer(content))
    if not matches:
        return content, [], False

    imports: Dict[str, str] = {}  # path -> import_name

    # Collect all unique file paths and generate import names
    for match in matches:
        file_path = match.group(2)
        if file_path not in imports:
            imports[file_path] = path_to_import_name(file_path)

    # Generate import statements
    import_statements = []
    import_statements.append("import CodeBlock from '@theme/CodeBlock';")
    for file_path, import_name in sorted(imports.items()):
        # The file paths in SPEC.md are relative to repo root (e.g., "schemas/file.yaml")
        # Files are copied to website/static/v<version>/, so use @site/static/v<version>/<path>
        if version:
            relative_path = f"@site/static/v{version}/{file_path}"
        else:
            relative_path = f"@site/static/{file_path}"
        import_statements.append(f"import {import_name} from '!!raw-loader!{relative_path}';")

    # Replace links with CodeBlock components
    def replace_link(match: re.Match) -> str:
        link_text = match.group(1)
        file_path = match.group(2)
        import_name = imports[file_path]
        # Determine language from extension
        ext = Path(file_path).suffix.lstrip(".")
        language = "yaml" if ext in ("yaml", "yml") else "json"
        return f'<CodeBlock language="{language}" title="{link_text}">{{{import_name}}}</CodeBlock>'

    processed_content = YAML_JSON_LINK_RE.sub(replace_link, content)

    return processed_content, import_statements, True


def read_lines(path: Path) -> List[str]:
    return path.read_text(encoding="utf-8").splitlines()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_front_matter(title: str, sidebar_position: Optional[int]) -> str:
    safe_title = json.dumps(title, ensure_ascii=True)
    lines = ["---", f"title: {safe_title}"]
    if sidebar_position is not None:
        lines.append(f"sidebar_position: {sidebar_position}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def normalize_body(lines: List[str]) -> str:
    # Trim leading empty lines for cleaner docs.
    while lines and lines[0].strip() == "":
        lines.pop(0)
    return "\n".join(lines).rstrip() + "\n"


def find_part_blocks(lines: List[str]) -> List[Tuple[int, int, str]]:
    part_starts: List[Tuple[int, str]] = []
    for idx, line in enumerate(lines):
        match = PART_HEADING_RE.match(line)
        if match:
            part_starts.append((idx, match.group(1)))

    blocks: List[Tuple[int, int, str]] = []
    for i, (start, title) in enumerate(part_starts):
        end = part_starts[i + 1][0] if i + 1 < len(part_starts) else len(lines)
        blocks.append((start, end, title))
    return blocks


def extract_title_and_preface(lines: List[str]) -> Tuple[str, List[str], int]:
    for idx, line in enumerate(lines):
        match = TITLE_HEADING_RE.match(line)
        if match:
            title = match.group(1)
            return title, lines[idx + 1 :], idx + 1
    return "Specification", lines, 0


def extract_sections(
    lines: List[str], start: int, end: int
) -> List[Tuple[str, int, int]]:
    sections: List[Tuple[str, int, int]] = []
    section_starts: List[Tuple[int, str]] = []
    for idx in range(start, end):
        match = SECTION_HEADING_RE.match(lines[idx])
        if match:
            section_starts.append((idx, match.group(1)))

    for i, (sec_start, title) in enumerate(section_starts):
        sec_end = section_starts[i + 1][0] if i + 1 < len(section_starts) else end
        sections.append((title, sec_start, sec_end))
    return sections


def write_category(path: Path, label: str, position: int) -> None:
    payload = {
        "label": label,
        "position": position,
        "collapsible": True,
        "collapsed": True,
    }
    write_text(path / "_category_.json", json.dumps(payload, indent=2) + "\n")


def copy_assets(
    spec_path: Path, schemas_path: Path, website_root: Path, version: Optional[str] = None
) -> None:
    """Copy SPEC.md and schemas folder to website/static for versioning.

    Args:
        spec_path: Path to SPEC.md
        schemas_path: Path to schemas folder
        website_root: Path to website root
        version: Optional version string (e.g., "1.0.0"). If provided, copies to
                 static/v<version>/. If None, copies to static/ directly.
    """
    if version:
        static_dir = website_root / "static" / f"v{version}"
    else:
        static_dir = website_root / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    # Copy SPEC.md
    dest_spec = static_dir / "SPEC.md"
    shutil.copy2(spec_path, dest_spec)

    # Copy schemas folder
    dest_schemas = static_dir / "schemas"
    if dest_schemas.exists():
        shutil.rmtree(dest_schemas)
    shutil.copytree(schemas_path, dest_schemas)


def generate_docs(
    spec_path: Path, docs_root: Path, website_root: Path, version: Optional[str] = None
) -> None:
    """Generate Docusaurus docs from SPEC.md.

    Args:
        spec_path: Path to SPEC.md
        docs_root: Path to Docusaurus docs root
        website_root: Path to Docusaurus website root
        version: Optional version string for static assets (e.g., "1.0.0")
    """
    # Copy SPEC.md and schemas to website/static for versioning
    schemas_path = spec_path.parent / "schemas"
    if schemas_path.exists():
        copy_assets(spec_path, schemas_path, website_root, version)

    lines = read_lines(spec_path)

    title, preface_lines, title_end_idx = extract_title_and_preface(lines)

    part_blocks = find_part_blocks(lines)
    if not part_blocks:
        raise ValueError("No parts found in SPEC.md")

    first_part_start = part_blocks[0][0]
    preface = normalize_body(lines[title_end_idx:first_part_start])

    spec_root = docs_root / "spec"
    write_category(spec_root, "UGAS Specification", 1)

    # Process index content for YAML/JSON links
    processed_preface, preface_imports, preface_has_imports = process_yaml_json_links(
        preface, "", version
    )
    front_matter = build_front_matter(title, 1)
    if preface_has_imports:
        imports_block = "\n".join(preface_imports) + "\n\n"
        index_content = front_matter + imports_block + processed_preface
        write_text(spec_root / "index.mdx", index_content)
    else:
        index_content = front_matter + preface
        write_text(spec_root / "index.md", index_content)

    for part_index, (part_start, part_end, part_title) in enumerate(part_blocks, 1):
        part_slug = slugify(part_title)
        part_dir = spec_root / part_slug
        write_category(part_dir, part_title, part_index + 1)

        sections = extract_sections(lines, part_start, part_end)
        for sec_index, (sec_title, sec_start, sec_end) in enumerate(sections, 1):
            body_lines = lines[sec_start + 1 : sec_end]
            body = normalize_body(body_lines)

            # Process body for YAML/JSON links
            processed_body, imports, has_imports = process_yaml_json_links(
                body, part_slug, version
            )
            front_matter = build_front_matter(sec_title, sec_index)

            if has_imports:
                imports_block = "\n".join(imports) + "\n\n"
                content = front_matter + imports_block + processed_body
                filename = f"{sec_index:02d}-{slugify(sec_title)}.mdx"
            else:
                content = front_matter + body
                filename = f"{sec_index:02d}-{slugify(sec_title)}.md"

            write_text(part_dir / filename, content)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Docusaurus docs from SPEC.md")
    parser.add_argument(
        "--spec",
        default=str(Path(__file__).resolve().parents[1] / "SPEC.md"),
        help="Path to SPEC.md",
    )
    parser.add_argument(
        "--docs",
        default=str(Path(__file__).resolve().parents[1] / "website" / "docs"),
        help="Path to Docusaurus docs root",
    )
    parser.add_argument(
        "--website",
        default=str(Path(__file__).resolve().parents[1] / "website"),
        help="Path to Docusaurus website root",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Version string for static assets (e.g., '1.0.0'). If not provided, uses unversioned paths.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec_path = Path(args.spec).resolve()
    docs_root = Path(args.docs).resolve()
    website_root = Path(args.website).resolve()

    if not spec_path.exists():
        raise FileNotFoundError(f"SPEC not found: {spec_path}")
    if not docs_root.exists():
        raise FileNotFoundError(f"Docs root not found: {docs_root}")
    if not website_root.exists():
        raise FileNotFoundError(f"Website root not found: {website_root}")

    generate_docs(spec_path, docs_root, website_root, args.version)


if __name__ == "__main__":
    main()
