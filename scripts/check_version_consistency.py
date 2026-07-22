#!/usr/bin/env python3
"""Guard against version drift and placeholder leakage (feedback F4).

Enforces two invariants in the source tree:

1. Authored data files (schemas, examples, genre entities) reference schemas via
   the `%%UGAS_VERSION%%` placeholder — never a concrete version. A concrete
   version baked into source is placeholder leakage: it would pin those files to
   a stale release and bypass the publish-time substitution.

2. Genre AsciiDoc headers (:revnumber: / :ugas-version:) match package.json, so
   the source never advertises a version it is not.

Run from the repo root: check_version_consistency.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# A concrete pinned version inside a canonical schema URL, e.g.
# https://ugas.jbltx.com/v1.0.0-draft.4/schemas/attribute.json
CONCRETE_URL = re.compile(r"ugas\.jbltx\.com/v[0-9][^/\s\"']*/schemas/")


def check_placeholder_leakage(errors: list[str]) -> None:
    globs = [
        "schemas/*.json",
        "schemas/*.yaml",
        "schemas/examples/*.yaml",
        "schemas/manifest/*.json",
        "genres/**/entities/*.yaml",
    ]
    for pattern in globs:
        for path in ROOT.glob(pattern):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if ("$schema" in line or "$id" in line) and CONCRETE_URL.search(line):
                    rel = path.relative_to(ROOT)
                    errors.append(
                        f"{rel}:{lineno} pins a concrete version in a schema URL; "
                        f"use %%UGAS_VERSION%% instead"
                    )


def check_genre_headers(version: str, errors: list[str]) -> None:
    docs = sorted((ROOT / "genres").glob("*/spec.adoc"))
    for extra in ("index.adoc", "taxonomy.adoc"):
        p = ROOT / "genres" / extra
        if p.is_file():
            docs.append(p)
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        for attr, expected in ((":revnumber:", version), (":ugas-version:", f"v{version}")):
            m = re.search(rf"^{re.escape(attr)}\s*(.+)$", text, flags=re.M)
            if m and m.group(1).strip() != expected:
                rel = doc.relative_to(ROOT)
                errors.append(
                    f"{rel} {attr} is {m.group(1).strip()!r}, expected {expected!r} "
                    f"(package.json version) — run scripts/sync_version.py"
                )


def main() -> int:
    version = json.loads((ROOT / "package.json").read_text())["version"]
    errors: list[str] = []
    check_placeholder_leakage(errors)
    check_genre_headers(version, errors)

    if errors:
        print(f"✗ {len(errors)} version-consistency issue(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"✓ version consistency OK (package.json = {version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
