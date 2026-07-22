#!/usr/bin/env python3
"""Generate RAG retrieval artifacts from the pre-chunked spec sections.

Produces, into <version-dir>/rag/:
  * chunks.jsonl  — one JSON object per line (Appendix F): id, version, pillar,
    sectionId, headingPath, anchor, sourceUrl, tokens, sha256, text. Chunks are
    cut at ### subsections (a section's intro before its first ### is its own
    chunk); an oversized subsection splits on #### then on blank lines, but never
    inside a fenced code/YAML block.
  * llms-index.json — intent -> [chunk id] routing so a consumer can do intent
    routing with no embeddings (and seed retrieval for those that use them).

Runs after build_sections.py (it reads sections/ + sections/index.json).

Usage:
    build_rag.py <version-dir> <version> [--base-url URL]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

DEFAULT_BASE_URL = "https://ugas.jbltx.com"
TARGET_MAX_TOKENS = 1500
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
NUM_RE = re.compile(r"^\d+(\.\d+)*\.?\s")

# Curated author intents -> (sectionId, [title keywords]). Keywords match
# subsection titles within the section; the section's intro chunk is always
# included. Unresolved entries are dropped so every id in llms-index is real.
INTENTS = {
    "author an effect": ("gameplay-effects", ["modifier", "execution calc"]),
    "modifier pipeline": ("attributes", ["modifier pipeline"]),
    "gate an ability on state": ("gameplay-abilities", ["activation", "requirement"]),
    "define an attribute": ("attributes", ["data structure", "clamp"]),
    "author a gameplay tag": ("gameplay-tags", ["hierarchical", "container"]),
    "duration and periodic effects": ("gameplay-effects", ["duration", "periodic"]),
    "ability lifecycle": ("gameplay-abilities", ["lifecycle", "commit"]),
    "attribute sets": ("attribute-sets", []),
    "input integration": ("input-integration", ["actions", "mappings", "modifiers"]),
    "gameplay cues / feedback": ("gameplay-cues", []),
    "networking and replication": ("network-replication", ["prediction", "reconciliation"]),
    "state persistence": ("state-persistence", ["snapshot", "restoration"]),
}


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"\s+", "-", s).strip("-")


def strip_number(title: str) -> str:
    return NUM_RE.sub("", title).strip() or title.strip()


def approx_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))


def has_content(text: str) -> bool:
    """True if the chunk has body beyond its heading lines (code counts)."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not HEADING_RE.match(line):
            return True
    return False


def split_fenced_aware(lines: list[str], level_marker: str) -> list[list[str]]:
    """Split lines at headings of exactly `level_marker` (e.g. '#### '),
    ignoring headings inside fenced blocks. Returns list of line-groups."""
    groups: list[list[str]] = []
    current: list[str] = []
    in_fence = False
    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            current.append(line)
            continue
        if not in_fence and line.startswith(level_marker) and HEADING_RE.match(line):
            if current:
                groups.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        groups.append(current)
    return groups


def split_paragraphs_fenced_aware(lines: list[str]) -> list[list[str]]:
    """Fallback split on blank lines, never breaking a fenced block."""
    groups: list[list[str]] = []
    current: list[str] = []
    in_fence = False
    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
        if not in_fence and line.strip() == "" and current:
            current.append(line)
            groups.append(current)
            current = []
        else:
            current.append(line)
    if current:
        groups.append(current)
    return groups


def pack(groups: list[list[str]]) -> list[list[str]]:
    """Greedily merge adjacent groups while under the token budget."""
    out: list[list[str]] = []
    buf: list[str] = []
    for g in groups:
        candidate = buf + g
        if buf and approx_tokens("".join(candidate)) > TARGET_MAX_TOKENS:
            out.append(buf)
            buf = list(g)
        else:
            buf = candidate
    if buf:
        out.append(buf)
    return out


def part_title(parent_id: str | None) -> str | None:
    if not parent_id:
        return None
    words = []
    for w in parent_id.split("-"):
        words.append(w.upper() if re.fullmatch(r"[ivx]+", w) else w.capitalize())
    return " ".join(words)


def subsections(section_lines: list[str]):
    """Yield (subsection_title | None, lines) split at top-level ### headings.
    The intro before the first ### yields title=None."""
    groups = split_fenced_aware(section_lines, "### ")
    for g in groups:
        m = HEADING_RE.match(g[0])
        if m and g[0].startswith("### "):
            yield m.group(2).strip(), g
        else:
            yield None, g


def build_chunks(version_dir: Path, version: str, base_url: str) -> list[dict]:
    index = json.loads((version_dir / "sections" / "index.json").read_text(encoding="utf-8"))
    chunks: list[dict] = []
    for sec in index["sections"]:
        sec_file = version_dir / sec["path"]
        if not sec_file.is_file():
            continue
        lines = sec_file.read_text(encoding="utf-8").splitlines(keepends=True)
        source_url = f"{base_url}/{version}/{sec['path']}"
        base_head = [part_title(sec.get("parentId")), sec["title"]]

        for sub_title, sub_lines in subsections(lines):
            # Sub-split oversized subsections: #### first, then paragraphs.
            pieces = [sub_lines]
            if approx_tokens("".join(sub_lines)) > TARGET_MAX_TOKENS:
                pieces = pack(split_fenced_aware(sub_lines, "#### "))
                repacked: list[list[str]] = []
                for p in pieces:
                    if approx_tokens("".join(p)) > TARGET_MAX_TOKENS:
                        repacked.extend(pack(split_paragraphs_fenced_aware(p)))
                    else:
                        repacked.append(p)
                pieces = repacked

            for i, piece in enumerate(pieces):
                text = "".join(piece).strip("\n") + "\n"
                if not has_content(text):  # heading-only chunk — retrieval noise
                    continue
                if sub_title is None:
                    cid = sec["id"]
                    heading_path = [h for h in base_head if h]
                    anchor = sec["anchor"]
                else:
                    cid = f"{sec['id']}-{slugify(strip_number(sub_title))}"
                    heading_path = [h for h in base_head + [sub_title] if h]
                    anchor = "#" + slugify(sub_title)
                if len(pieces) > 1:
                    cid = f"{cid}-{i + 1}"
                chunks.append(
                    {
                        "id": cid,
                        "version": version.lstrip("v"),
                        "pillar": sec.get("pillar"),
                        "sectionId": sec["id"],
                        "headingPath": " ▸ ".join(heading_path),
                        "anchor": anchor,
                        "sourceUrl": source_url,
                        "tokens": approx_tokens(text),
                        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                        "text": text,
                    }
                )
    return chunks


def build_llms_index(chunks: list[dict]) -> dict:
    by_section: dict[str, list[dict]] = {}
    for c in chunks:
        by_section.setdefault(c["sectionId"], []).append(c)

    out: dict[str, list[str]] = {}
    for intent, (section_id, keywords) in INTENTS.items():
        section_chunks = by_section.get(section_id)
        if not section_chunks:
            continue
        ids: list[str] = []
        intro = next((c for c in section_chunks if c["id"] == section_id), section_chunks[0])
        ids.append(intro["id"])
        for kw in keywords:
            for c in section_chunks:
                path = c["headingPath"].lower()
                if kw.lower() in path and c["id"] not in ids:
                    ids.append(c["id"])
        out[intent] = ids
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("version_dir")
    ap.add_argument("version")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = ap.parse_args()

    version_dir = Path(args.version_dir)
    version = args.version if args.version.startswith("v") else f"v{args.version}"
    rag_dir = version_dir / "rag"
    rag_dir.mkdir(parents=True, exist_ok=True)

    chunks = build_chunks(version_dir, version, args.base_url.rstrip("/"))
    with (rag_dir / "chunks.jsonl").open("w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")

    llms_index = build_llms_index(chunks)
    (rag_dir / "llms-index.json").write_text(
        json.dumps(llms_index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {rag_dir}/chunks.jsonl ({len(chunks)} chunks) + llms-index.json ({len(llms_index)} intents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
