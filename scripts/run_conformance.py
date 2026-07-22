#!/usr/bin/env python3
"""Run the conformance corpus against the schema bundle.

Asserts every entity under conformance/valid/ validates and every entity under
conformance/invalid/ is rejected — a shared, labelled corpus that regression-
tests the schemas here and that downstream loaders/validators can run too.

Validation goes through the in-memory schema bundle (built from schemas/), so
this also exercises the bundle's offline $ref resolution and $schema dispatch.

Run from the repo root: run_conformance.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_schema_bundle  # noqa: E402


def load_docs(path: Path):
    if path.suffix == ".json":
        import json
        return [json.loads(path.read_text(encoding="utf-8"))]
    return [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d]


def schema_type(doc: dict) -> str | None:
    ref = doc.get("$schema") if isinstance(doc, dict) else None
    if not ref:
        return None
    return ref.rsplit("/", 1)[-1].removesuffix(".json")


def main() -> int:
    bundle = build_schema_bundle.build(ROOT / "schemas", "v0")
    validator = Draft7Validator(bundle)  # internal #/$defs refs resolve against the bundle
    known_types = set(bundle["$defs"])

    corpus = ROOT / "conformance"
    errors: list[str] = []
    n_valid = n_invalid = 0

    for path in sorted((corpus / "valid").glob("*")):
        if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        for doc in load_docs(path):
            n_valid += 1
            if schema_type(doc) not in known_types:
                errors.append(f"valid/{path.name}: $schema does not name a known type")
                continue
            errs = list(validator.iter_errors(doc))
            if errs:
                errors.append(f"valid/{path.name}: expected to pass but failed — {errs[0].message}")

    for path in sorted((corpus / "invalid").glob("*")):
        if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        for doc in load_docs(path):
            n_invalid += 1
            if schema_type(doc) not in known_types:
                errors.append(f"invalid/{path.name}: $schema does not name a known type (dispatch would not engage)")
                continue
            if not list(validator.iter_errors(doc)):
                errors.append(f"invalid/{path.name}: expected to fail but passed")

    if errors:
        print(f"✗ {len(errors)} conformance failure(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"✓ conformance OK ({n_valid} valid pass, {n_invalid} invalid rejected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
