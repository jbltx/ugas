#!/usr/bin/env python3
"""Verify the generated consumer artifacts in a built version tree.

Doubles as the CI drift guard: run it after build-artifacts.sh. Checks that
  * index.json and sections/index.json validate against their meta-schemas,
  * every manifest resource path exists and its sha256 matches,
  * no section file splits a fenced code block,
  * the generated llms.txt lists every genre pack and every schema,
  * no unsubstituted %%UGAS_VERSION%% placeholder leaked into the artifacts.

Usage:
    check_artifacts.py <version-dir> <llms-txt>
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft7Validator

FENCE_RE = re.compile(r"^\s*(```|~~~)")


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def validate_meta(version_dir: Path, errors: list[str]) -> dict | None:
    manifest_path = version_dir / "index.json"
    sections_index = version_dir / "sections" / "index.json"
    meta_dir = version_dir / "schemas" / "manifest"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = [
        (manifest, meta_dir / "index.schema.json"),
        (json.loads(sections_index.read_text(encoding="utf-8")),
         meta_dir / "sections-index.schema.json"),
    ]
    genres_index = version_dir / "genres" / "index.json"
    if genres_index.is_file():
        checks.append(
            (json.loads(genres_index.read_text(encoding="utf-8")),
             meta_dir / "genres-index.schema.json")
        )
    # versions.json lives at the docs root (one level up), when the landing page
    # has already produced it.
    versions_json = version_dir.parent / "versions.json"
    if versions_json.is_file() and (meta_dir / "versions.schema.json").is_file():
        checks.append(
            (json.loads(versions_json.read_text(encoding="utf-8")),
             meta_dir / "versions.schema.json")
        )
    for data, schema_path in checks:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errs = sorted(Draft7Validator(schema).iter_errors(data), key=lambda e: list(e.path))
        for e in errs:
            fail(f"{schema_path.name}: {list(e.path)} {e.message}", errors)
    return manifest


def check_checksums(version_dir: Path, manifest: dict, errors: list[str]) -> None:
    for r in manifest["resources"]:
        # manifest paths are docs-root-relative (vX/...); resolve against the
        # version dir by dropping that leading version segment — works whether
        # the dir is named vX (publish) or something else (preview dist/).
        rel = Path(*Path(r["path"]).parts[1:])
        p = version_dir / rel
        if not p.is_file():
            fail(f"manifest path missing on disk: {r['path']}", errors)
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest != r["sha256"]:
            fail(f"checksum mismatch: {r['path']}", errors)
        if p.stat().st_size != r["bytes"]:
            fail(f"byte size mismatch: {r['path']}", errors)


def check_genre_index(version_dir: Path, errors: list[str]) -> None:
    gi = version_dir / "genres" / "index.json"
    if not gi.is_file():
        return
    data = json.loads(gi.read_text(encoding="utf-8"))

    def resolve(p: str) -> Path:  # strip leading vX/ segment
        return version_dir / Path(*Path(p).parts[1:])

    for pack in data.get("packs", []):
        if not resolve(pack["specPath"]).is_file():
            fail(f"genres/index.json specPath missing: {pack['specPath']}", errors)
        for e in pack["entities"]:
            if not resolve(e["path"]).is_file():
                fail(f"genres/index.json entity path missing: {e['path']}", errors)


def check_bundle(version_dir: Path, errors: list[str]) -> None:
    bundle_path = version_dir / "schemas" / "bundle.json"
    if not bundle_path.is_file():
        return
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    try:
        Draft7Validator.check_schema(bundle)
    except Exception as e:  # malformed bundle
        fail(f"schemas/bundle.json is not a valid draft-07 schema: {e}", errors)
        return
    # It must resolve offline: instantiating the validator and validating a
    # trivial doc must not raise a $ref resolution error.
    try:
        Draft7Validator(bundle).is_valid({})
    except Exception as e:
        fail(f"schemas/bundle.json has unresolved internal $refs: {e}", errors)


def check_fences(version_dir: Path, errors: list[str]) -> None:
    for md in sorted((version_dir / "sections").glob("*.md")):
        n = sum(1 for line in md.read_text(encoding="utf-8").splitlines() if FENCE_RE.match(line))
        if n % 2:
            fail(f"unbalanced code fence in section {md.name}", errors)


def check_llms(version_dir: Path, llms_path: Path, manifest: dict, errors: list[str]) -> None:
    text = llms_path.read_text(encoding="utf-8")
    packs = sorted(
        d.name for d in (version_dir / "genres").iterdir()
        if d.is_dir() and (d / "spec.adoc").is_file() and not d.name.startswith("_")
    )
    for pack in packs:
        if f"genres/{pack}/spec.adoc" not in text:
            fail(f"llms.txt missing genre pack: {pack}", errors)
    schema_yamls = sorted(
        p.name for p in (version_dir / "schemas").glob("*.yaml")
    )
    for s in schema_yamls:
        if f"schemas/{s}" not in text:
            fail(f"llms.txt missing schema: {s}", errors)


def check_placeholders(version_dir: Path, llms_path: Path, errors: list[str]) -> None:
    for f in [version_dir / "index.json", llms_path]:
        if "%%UGAS_VERSION%%" in f.read_text(encoding="utf-8"):
            fail(f"unsubstituted %%UGAS_VERSION%% in {f.name}", errors)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"Usage: {argv[0]} <version-dir> <llms-txt>", file=sys.stderr)
        return 2
    version_dir = Path(argv[1])
    llms_path = Path(argv[2])

    errors: list[str] = []
    manifest = validate_meta(version_dir, errors)
    if manifest is not None:
        check_checksums(version_dir, manifest, errors)
        check_llms(version_dir, llms_path, manifest, errors)
    check_genre_index(version_dir, errors)
    check_bundle(version_dir, errors)
    check_fences(version_dir, errors)
    check_placeholders(version_dir, llms_path, errors)

    if errors:
        print(f"✗ {len(errors)} artifact check(s) failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    n = len(manifest["resources"]) if manifest else 0
    print(f"✓ artifacts OK ({n} resources, meta-schemas valid, checksums match)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
