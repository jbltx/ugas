#!/usr/bin/env python3
"""Bundle the individual JSON schemas into one self-contained schemas/bundle.json.

Consumers (browser builds, CI, air-gapped) get one-file, network-free
validation: every entity type lives under ``#/$defs/<type>`` with all internal
``$ref``s rewritten to resolve inside the bundle. A top-level ``allOf`` of
``if``/``then`` clauses dispatches on the entity's own ``$schema`` — a document
whose ``$schema`` names ``<type>`` is validated against that type's schema.

Usage:
    build_schema_bundle.py <schemas-dir> <version> [--out schemas/bundle.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# Not entity types: skip the bundle itself, the meta-schemas, and examples.
SKIP = {"bundle"}


def rewrite_refs(node, type_name: str):
    """Prefix every internal (#/...) $ref so it resolves under #/$defs/<type>."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str) and v.startswith("#/"):
                out[k] = f"#/$defs/{type_name}{v[1:]}"
            else:
                out[k] = rewrite_refs(v, type_name)
        return out
    if isinstance(node, list):
        return [rewrite_refs(v, type_name) for v in node]
    return node


def load_type_body(path: Path, type_name: str) -> dict:
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema.pop("$schema", None)
    schema.pop("$id", None)
    return rewrite_refs(schema, type_name)


def build(schemas_dir: Path, version: str) -> dict:
    defs: dict[str, dict] = {}
    for path in sorted(schemas_dir.glob("*.json")):
        type_name = path.stem
        if type_name in SKIP:
            continue
        defs[type_name] = load_type_body(path, type_name)

    dispatch = [
        {
            "if": {
                "required": ["$schema"],
                "properties": {"$schema": {"pattern": rf"/schemas/{t}\.json$"}},
            },
            "then": {"$ref": f"#/$defs/{t}"},
        }
        for t in defs
    ]

    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"https://ugas.jbltx.com/{version}/schemas/bundle.json",
        "title": "UGAS schema bundle",
        "description": (
            "Self-contained bundle of every UGAS entity schema. Validate an entity "
            "against #/$defs/<type> (type = the <type> in its $schema), or against the "
            "whole bundle to dispatch on $schema automatically. Resolves offline."
        ),
        "$defs": defs,
        "allOf": dispatch,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("schemas_dir")
    ap.add_argument("version")
    ap.add_argument("--out")
    args = ap.parse_args()

    schemas_dir = Path(args.schemas_dir)
    if not schemas_dir.is_dir():
        print(f"schemas dir not found: {schemas_dir}")
        return 1
    version = args.version if args.version.startswith("v") else f"v{args.version}"

    bundle = build(schemas_dir, version)
    out = Path(args.out) if args.out else schemas_dir / "bundle.json"
    out.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(bundle['$defs'])} entity types)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
