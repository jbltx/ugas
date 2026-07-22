#!/usr/bin/env python3
"""Split the generated SPEC.md into per-section Markdown files + a section index.

Turns the single ~168 KB SPEC.md into individually-addressable, lazy-loadable
chunks so agent/RAG consumers can fetch "the Effects section" instead of the
whole spec. Purely additive — SPEC.md is untouched.

A *section* is a top-level unit of the spec:
  * the Preamble,
  * each numbered chapter (``## N. Title`` under a ``# Part ...``),
  * each unnumbered appendix (``# Mathematical Notation`` and friends).

``# Part ...`` headings are grouping-only: they never become a file, they only
set the ``parentId`` of the chapters beneath them. Detection is fence-aware —
``#`` lines inside ``` fenced code blocks (YAML comments, embedded schemas) are
content, never headings.

Section ``id``s are derived from the heading slug with the leading number
stripped (``9. Gameplay Effects`` -> ``gameplay-effects``), so they stay stable
when chapters are renumbered.

Usage:
    build_sections.py <spec.md> <sections-out-dir>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Map a section id to the pillar it documents (null for everything else).
PILLAR_BY_ID = {
    "attributes": "attributes",
    "attribute-sets": "attributes",
    "gameplay-tags": "tags",
    "gameplay-abilities": "abilities",
    "gameplay-effects": "effects",
}

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
NUMBERED_RE = re.compile(r"^\d+(\.\d+)*\.?\s")  # "9. ", "9.1 ", "10. "


def slugify(text: str) -> str:
    """GitHub-flavored-markdown heading anchor slug."""
    slug = text.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)  # drop punctuation
    slug = re.sub(r"\s+", "-", slug)  # spaces -> hyphens
    return slug.strip("-")


def strip_number(title: str) -> str:
    """Drop a leading '9. ' / '9.1 ' so the id survives renumbering."""
    return NUMBERED_RE.sub("", title).strip() or title.strip()


def parse_headings(lines: list[str]):
    """Yield (line_index, level, title) for real Markdown headings only."""
    in_fence = False
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            yield i, len(m.group(1)), m.group(2).strip()


def is_section_start(level: int, title: str) -> bool:
    if level == 2 and NUMBERED_RE.match(title):
        return True
    if level == 1 and not title.startswith("Part "):
        return True
    return False


def build(spec_path: Path, out_dir: Path) -> dict:
    lines = spec_path.read_text(encoding="utf-8").splitlines(keepends=True)
    headings = list(parse_headings(lines))

    # Locate every section-start heading and the enclosing Part context.
    starts: list[tuple[int, str, str | None]] = []  # (line_idx, title, parent_id)
    current_part_id: str | None = None
    for idx, level, title in headings:
        if level == 1 and title.startswith("Part "):
            current_part_id = slugify(title)
            continue
        if is_section_start(level, title):
            parent = current_part_id if level == 2 else None
            starts.append((idx, title, parent))

    # Filename prefixes follow the spec's own numbering: Preamble = 00,
    # numbered chapters keep their number (§9 -> 09), appendices continue after
    # the last numbered chapter. Consumers address sections by the index `path`,
    # so the prefix is purely for stable ordering / human legibility.
    numbers = [
        int(re.match(r"^(\d+)\.", t).group(1))
        for _, t, _ in starts
        if re.match(r"^(\d+)\.", t)
    ]
    appendix_seq = max(numbers) if numbers else 0

    out_dir.mkdir(parents=True, exist_ok=True)
    index_entries = []
    for seq, (line_idx, title, parent_id) in enumerate(starts, start=1):
        end = starts[seq][0] if seq < len(starts) else len(lines)
        body = "".join(lines[line_idx:end]).rstrip("\n") + "\n"

        sid = slugify(strip_number(title))
        num_match = re.match(r"^(\d+)\.", title)
        level = 2 if num_match else 1
        if num_match:
            prefix = int(num_match.group(1))
        elif sid == "preamble":
            prefix = 0
        else:
            appendix_seq += 1
            prefix = appendix_seq
        filename = f"{prefix:02d}-{sid}.md"
        (out_dir / filename).write_text(body, encoding="utf-8")

        index_entries.append(
            {
                "id": sid,
                "title": title,
                "level": level,
                "pillar": PILLAR_BY_ID.get(sid),
                "parentId": parent_id,
                "anchor": "#" + slugify(title),
                "path": f"sections/{filename}",
                "bytes": len(body.encode("utf-8")),
            }
        )

    index = {"sections": index_entries}
    (out_dir / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return index


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"Usage: {argv[0]} <spec.md> <sections-out-dir>", file=sys.stderr)
        return 2
    spec_path = Path(argv[1])
    out_dir = Path(argv[2])
    if not spec_path.is_file():
        print(f"SPEC markdown not found: {spec_path}", file=sys.stderr)
        return 1
    index = build(spec_path, out_dir)
    print(f"Wrote {len(index['sections'])} sections + index.json to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
