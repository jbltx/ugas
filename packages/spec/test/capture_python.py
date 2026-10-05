#!/usr/bin/env python3
"""Dump what scripts/check_example_references.py reports, with its inputs, as JSON.

Used by parity.test.mjs to hold the JS checkReferences to the Python checker. Covers:

- every fixture in scripts/test_check_example_references.py, captured by running that
  test's main() with its `check` wrapped, so new Python fixtures are picked up as is;
- the shipped examples, and each genre pack's entities.

Each case is {name, scope, files: [{path, text}], errors: [str]}, files in the order the
Python loader read them and with the path it reported. Run from anywhere:
    python3 packages/spec/test/capture_python.py
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import check_example_references as checker  # noqa: E402
import test_check_example_references as fixtures  # noqa: E402

cases: list[dict] = []


def capture(name: str, directory: Path) -> list[str]:
    files = []
    for path in sorted(directory.rglob("*")):
        if path.suffix.lower() not in {".yaml", ".yml", ".json"} or path.name in {"pack.yaml", "index.json"}:
            continue
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        files.append({"path": str(rel), "text": path.read_text(encoding="utf-8")})
    errors = checker.check(directory)
    cases.append({"name": name, "scope": directory.name, "files": files, "errors": errors})
    return errors


fixture_count = 0


def wrapped(directory: Path) -> list[str]:
    global fixture_count
    fixture_count += 1
    return capture(f"python fixture #{fixture_count}", directory)


fixtures.check = wrapped
with contextlib.redirect_stdout(sys.stderr):
    status = fixtures.main()
if status != 0:
    sys.exit("test_check_example_references.py fails on its own; fix that first")

capture("schemas/examples", ROOT / "schemas" / "examples")
for pack in sorted((ROOT / "genres").iterdir()):
    if (pack / "entities").is_dir():
        capture(f"genres/{pack.name}/entities", pack / "entities")

json.dump({"fixtures": fixture_count, "cases": cases}, sys.stdout)
