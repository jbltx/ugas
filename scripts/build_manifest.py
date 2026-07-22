#!/usr/bin/env python3
"""Generate the machine-readable resource manifest (index.json) for a version.

Walks a built version tree (the ``source/`` layout that CI copies to
``docs/v<version>/``) and emits one authoritative, checksummed listing of every
resource: id, kind, title, path, canonical url, mediaType, bytes, sha256.

This is the single source of truth every other consumer artifact builds on:
``llms.txt`` is generated from it (see build_llms_txt.py), so the human index
can never drift from what actually ships.

Usage:
    build_manifest.py <built-version-dir> <version> [--base-url URL] [--out FILE]

``version`` is with or without a leading ``v`` (normalized to ``v...``).
Paths in the manifest are docs-root-relative (``v<version>/...``); urls are
``<base-url>/<path>`` (base-url default https://ugas.jbltx.com).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

DEFAULT_BASE_URL = "https://ugas.jbltx.com"

MEDIA_TYPES = {
    ".md": "text/markdown",
    ".json": "application/json",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".adoc": "text/asciidoc",
    ".html": "text/html",
    ".jsonl": "application/jsonl",
    ".txt": "text/plain",
}

SKIP_DIRS = {"spec"}  # AsciiDoc chapter includes — superseded by sections/ for consumers
# llms.txt/llms-full.txt live at the docs root, not the version dir, and llms.txt
# is generated *from* this manifest — never enumerate them here.
SKIP_FILES = {"SPEC.xml", "llms.txt", "llms-full.txt"}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def media_type(path: Path) -> str:
    if path.name in {"bundle.json"} or path.parent.name in {"schemas", "manifest"}:
        if path.suffix == ".json":
            return "application/schema+json"
    return MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")


def load_section_titles(built: Path) -> dict[str, dict]:
    idx = built / "sections" / "index.json"
    if not idx.is_file():
        return {}
    data = json.loads(idx.read_text(encoding="utf-8"))
    return {Path(s["path"]).name: s for s in data.get("sections", [])}


def titlecase(stem: str) -> str:
    return " ".join(w.capitalize() for w in re.split(r"[_\-]", stem))


def classify(rel: Path, section_titles: dict[str, dict]) -> tuple[str, str, str] | None:
    """Return (kind, id, title) for a resource, or None to skip it."""
    parts = rel.parts
    name = rel.name
    stem = rel.stem

    if parts[0] in SKIP_DIRS or name in SKIP_FILES:
        return None
    if rel.as_posix() == "index.json":  # the manifest itself
        return None

    # Top-level spec forms
    if rel.as_posix() == "SPEC.md":
        return "spec", "spec", "UGAS Specification (Markdown)"
    if rel.as_posix() == "SPEC.adoc":
        return "spec-source", "spec.adoc", "UGAS Specification (AsciiDoc source)"
    if rel.as_posix() == "index.html":
        return "html", "spec.html", "UGAS Specification (HTML)"

    # Spec sections
    if parts[0] == "sections":
        if name == "index.json":
            return "section-index", "sections.index", "Spec section index"
        meta = section_titles.get(name)
        sid = meta["id"] if meta else stem
        title = meta["title"] if meta else titlecase(stem)
        return "spec-section", f"spec.{sid}", title

    # Schemas
    if parts[0] == "schemas":
        if name == "bundle.json":
            return "schema-bundle", "schema.bundle", "Offline JSON-Schema bundle"
        if len(parts) >= 2 and parts[1] == "manifest" and rel.suffix == ".json":
            return "meta-schema", f"meta.{stem}", f"{titlecase(stem)} manifest schema"
        if len(parts) >= 2 and parts[1] == "examples":
            return "example", f"example.{stem}", titlecase(stem)
        if rel.suffix == ".json":
            return "schema", f"schema.{stem}", f"{titlecase(stem)} schema"
        if rel.suffix in {".yaml", ".yml"}:
            return "schema", f"schema.{stem}.yaml", f"{titlecase(stem)} schema (YAML)"
        if name == "README.md":
            return "doc", "schemas.readme", "Schema README"
        return "other", f"file.{rel.as_posix()}", name

    # Genres
    if parts[0] == "genres":
        if name == "index.json":
            return "genre-index", "genres.index", "Genre pack index"
        if len(parts) == 2 and rel.suffix in {".adoc", ".html", ".md"}:
            kind = "html" if rel.suffix == ".html" else "doc"
            return kind, f"genres.{stem}.{rel.suffix.lstrip('.')}", titlecase(stem)
        if len(parts) >= 3:
            pack = parts[1]
            if parts[2] == "entities":
                return "genre-entity", f"genre.{pack}.{stem}", f"{titlecase(pack)}: {stem}"
            if name == "spec.adoc":
                return "genre-pack-spec", f"genre.{pack}.spec", f"{titlecase(pack)} pack spec"
            if name == "pack.yaml":
                return "doc", f"genre.{pack}.meta", f"{titlecase(pack)} pack metadata"
            if name == "index.html":
                return "html", f"genre.{pack}.html", f"{titlecase(pack)} pack (HTML)"
            if name == "README.md":
                return "doc", f"genre.{pack}.readme", f"{titlecase(pack)} pack README"
        return "other", f"file.{rel.as_posix()}", name

    # RAG artifacts
    if parts[0] == "rag":
        return "rag", f"rag.{stem}", f"RAG {titlecase(stem)}"

    if rel.suffix == ".html":
        return "html", f"file.{rel.as_posix()}", name
    return "other", f"file.{rel.as_posix()}", name


def build(built: Path, version: str, base_url: str) -> dict:
    section_titles = load_section_titles(built)
    resources = []
    for path in sorted(built.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(built)
        result = classify(rel, section_titles)
        if result is None:
            continue
        kind, rid, title = result
        docs_path = f"{version}/{rel.as_posix()}"
        resources.append(
            {
                "id": rid,
                "kind": kind,
                "title": title,
                "path": docs_path,
                "url": f"{base_url}/{docs_path}",
                "mediaType": media_type(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_of(path),
            }
        )

    resources.sort(key=lambda r: r["path"])
    return {
        "spec": "ugas",
        "version": version.lstrip("v"),
        "resources": resources,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("built_dir")
    ap.add_argument("version")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--out")
    args = ap.parse_args()

    built = Path(args.built_dir)
    if not built.is_dir():
        print(f"Built dir not found: {built}")
        return 1
    version = args.version if args.version.startswith("v") else f"v{args.version}"

    manifest = build(built, version, args.base_url.rstrip("/"))
    out = Path(args.out) if args.out else built / "index.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(manifest['resources'])} resources)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
