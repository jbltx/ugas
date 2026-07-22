#!/usr/bin/env python3
"""Generate llms.txt from the resource manifest (index.json).

The llms.txt index used to be hand-maintained and drifted from reality (listed
3 genre packs while 10 shipped, 6 schemas while 11 shipped). Generating it from
the checksummed manifest makes that drift structurally impossible: every schema,
example, spec section, and genre pack in the manifest is listed here.

Usage:
    build_llms_txt.py <index.json> <out-llms.txt> [--full-txt-path llms-full.txt]

Links are docs-root-relative (``v<version>/...``), matching where the manifest
places resources; llms.txt itself lives at the docs root.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

HEADER = """# Universal Gameplay Ability System (UGAS)

> UGAS is an open, engine-agnostic specification for standardizing gameplay abilities, attributes, effects, and tags across game engines (Unreal, Unity, Godot) and AI world models. It defines a portable, data-driven architecture for gameplay logic.

The specification covers four pillars: Attributes (numeric state with a modifier pipeline), Gameplay Tags (hierarchical semantic labels), Gameplay Abilities (asynchronous stateful actions), and Gameplay Effects (the sole mutation mechanism for attributes and tags).
"""


def by_kind(resources: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for r in resources:
        out[r["kind"]].append(r)
    return out


def link(r: dict) -> str:
    return f"- [{r['title']}]({r['path']}): {r['title']}"


def build(manifest: dict, full_txt_path: str) -> str:
    resources = manifest["resources"]
    kinds = by_kind(resources)
    lines = [HEADER, ""]

    lines.append("## Specification\n")
    for r in resources:
        if r["kind"] == "spec":
            lines.append(f"- [UGAS Specification (Markdown)]({r['path']}): full spec, Markdown")
        elif r["kind"] == "html":
            if r["id"] == "spec.html":
                lines.append(f"- [UGAS Specification (HTML)]({r['path']}): full spec, HTML")
        elif r["kind"] == "spec-source":
            lines.append(f"- [UGAS Specification (AsciiDoc)]({r['path']}): AsciiDoc source")
    lines.append(f"- [Complete LLM context file]({full_txt_path}): entire spec + all schemas + examples in one file")
    lines.append("")

    lines.append("## Machine-readable manifests\n")
    # (kind, description) for the machine artifacts consumers vendor. Matched on
    # kind so the human genres/index.adoc is never mistaken for genres/index.json.
    manifest_kinds = {
        "section-index": "Spec section index (stable ids + anchors)",
        "genre-index": "Genre pack + entity index",
        "schema-bundle": "Offline JSON-Schema validation bundle",
    }
    lines.append("- [Resource manifest (index.json)](index.json): checksummed listing of every resource at this version")
    for r in resources:
        if r["kind"] in manifest_kinds:
            lines.append(f"- [{r['title']}]({r['path']}): {manifest_kinds[r['kind']]}")
    lines.append("- [Versions manifest](../versions.json): all published versions + latest alias")
    lines.append("")

    lines.append("## Spec sections\n")
    lines.append("Each spec section is individually fetchable; load one instead of the whole spec.\n")
    for r in sorted(kinds.get("spec-section", []), key=lambda r: r["path"]):
        lines.append(f"- [{r['title']}]({r['path']})")
    lines.append("")

    lines.append("## Schema Definitions\n")
    for r in sorted(kinds.get("schema", []), key=lambda r: r["path"]):
        lines.append(f"- [{r['title']}]({r['path']})")
    lines.append("")

    if kinds.get("example"):
        lines.append("## Examples\n")
        for r in sorted(kinds["example"], key=lambda r: r["path"]):
            lines.append(f"- [{r['title']}]({r['path']})")
        lines.append("")

    lines.append("## Genre Packs (templates)\n")
    lines.append("Additive, copy-and-extend starter kits per genre: a genre spec that extends (never replaces) the core spec, plus schema-conformant template entities you can load directly.\n")
    packs = sorted(kinds.get("genre-pack-spec", []), key=lambda r: r["path"])
    for r in packs:
        pack = r["path"].split("/genres/")[1].split("/")[0]
        if pack.startswith("_"):  # _template is a scaffold, not a shipped pack
            continue
        entities_dir = "/".join(r["path"].split("/")[:-1]) + "/entities/"
        lines.append(f"- [{r['title']}]({r['path']}): template entities under {entities_dir}")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("index_json")
    ap.add_argument("out")
    ap.add_argument("--full-txt-path", default="llms-full.txt")
    args = ap.parse_args()

    manifest = json.loads(Path(args.index_json).read_text(encoding="utf-8"))
    text = build(manifest, args.full_txt_path)
    Path(args.out).write_text(text, encoding="utf-8")

    n_packs = sum(1 for r in manifest["resources"] if r["kind"] == "genre-pack-spec")
    n_schemas = sum(1 for r in manifest["resources"] if r["kind"] == "schema" and r["path"].endswith(".yaml"))
    print(f"Wrote {args.out} ({n_packs} genre packs, {n_schemas} schemas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
