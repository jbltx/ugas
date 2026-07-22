#!/usr/bin/env python3
"""Generate genres/index.json — the machine-readable genre pack + entity manifest.

Lets consumers present a genre menu and load a pack's template entities
deterministically, instead of scraping the 469 KB llms-full.txt. Per pack it
records id, scope, signatureMechanic (from the pack's pack.yaml), the spec path,
and an entities[] list; multi-document entity files expand to one entry per
document. The scaffold pack (``_template``) is excluded.

Usage:
    build_genre_manifest.py <genres-dir> <version> [--out genres/index.json]

``version`` (with or without leading v) is echoed into the manifest and used to
build docs-root-relative paths (``v<version>/genres/...``).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

TITLE_RE = re.compile(r"^= UGAS Genre Pack:\s*(.+?)\s*$", re.MULTILINE)


def schema_type(doc: dict) -> str | None:
    """Short entity type from a document's $schema (gameplay_effect.json -> effect)."""
    ref = doc.get("$schema") if isinstance(doc, dict) else None
    if not ref:
        return None
    stem = ref.rsplit("/", 1)[-1].removesuffix(".json")
    return stem.removeprefix("gameplay_") if stem.startswith("gameplay_") else stem


def entity_id(doc: dict, fallback: str) -> str:
    if isinstance(doc, dict):
        for key in ("Name", "name", "Id", "id"):
            if doc.get(key):
                return str(doc[key])
    return fallback


def pack_title(spec_path: Path, pack_id: str) -> str:
    if spec_path.is_file():
        m = TITLE_RE.search(spec_path.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return pack_id


def collect_entities(pack_dir: Path, version: str, pack_id: str) -> list[dict]:
    entities: list[dict] = []
    entities_dir = pack_dir / "entities"
    if not entities_dir.is_dir():
        return entities
    for f in sorted(entities_dir.glob("*.yaml")):
        rel = f"{version}/genres/{pack_id}/entities/{f.name}"
        try:
            docs = list(yaml.safe_load_all(f.read_text(encoding="utf-8")))
        except yaml.YAMLError as e:  # surface malformed template content loudly
            raise SystemExit(f"Failed to parse {f}: {e}")
        docs = [d for d in docs if d]
        for i, doc in enumerate(docs):
            fallback = f.stem if len(docs) == 1 else f"{f.stem}[{i}]"
            entities.append(
                {
                    "id": entity_id(doc, fallback),
                    "type": schema_type(doc),
                    "path": rel,
                }
            )
    return entities


def build(genres_dir: Path, version: str) -> dict:
    packs = []
    for pack_dir in sorted(p for p in genres_dir.iterdir() if p.is_dir()):
        pid = pack_dir.name
        if pid.startswith("_"):  # scaffold, not a shipped pack
            continue
        spec_path = pack_dir / "spec.adoc"
        if not spec_path.is_file():
            continue

        meta = {}
        meta_path = pack_dir / "pack.yaml"
        if meta_path.is_file():
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}

        packs.append(
            {
                "id": pid,
                "title": pack_title(spec_path, pid),
                "scope": meta.get("scope"),
                "signatureMechanic": meta.get("signatureMechanic"),
                "specPath": f"{version}/genres/{pid}/spec.adoc",
                "entities": collect_entities(pack_dir, version, pid),
            }
        )

    return {"spec": "ugas", "version": version.lstrip("v"), "packs": packs}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("genres_dir")
    ap.add_argument("version")
    ap.add_argument("--out")
    args = ap.parse_args()

    genres_dir = Path(args.genres_dir)
    if not genres_dir.is_dir():
        print(f"genres dir not found: {genres_dir}")
        return 1
    version = args.version if args.version.startswith("v") else f"v{args.version}"

    manifest = build(genres_dir, version)
    out = Path(args.out) if args.out else genres_dir / "index.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    n_entities = sum(len(p["entities"]) for p in manifest["packs"])
    print(f"Wrote {out} ({len(manifest['packs'])} packs, {n_entities} entities)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
