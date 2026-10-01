#!/usr/bin/env python3
"""Regression tests for check_example_references.py. Standalone: no pytest.

Run from the repo root: python scripts/test_check_example_references.py
"""
from __future__ import annotations

import sys
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_example_references import check  # noqa: E402

BASE = "https://ugas.jbltx.com/0/schemas/"

ATTRIBUTE = f"""
$schema: {BASE}attribute.json
Name: Health
DefaultBaseValue: 100
"""
REGISTRY = f"""
$schema: {BASE}gameplay_tag.json
Tags:
  - Tag: Faction.Enemy
"""


def run(**files: str) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        for name, body in files.items():
            Path(tmp, f"{name}.yaml").write_text(textwrap.dedent(body), encoding="utf-8")
        return check(Path(tmp))


def expect(name: str, errors: list[str], *needles: str) -> bool:
    missing = [n for n in needles if not any(n in e for e in errors)]
    if needles and missing or not needles and errors:
        print(f"FAIL {name}: missing {missing}, got {errors}")
        return False
    print(f"ok   {name}")
    return True


def main() -> int:
    results = [
        expect(
            "scene references are checked",
            run(attr=ATTRIBUTE, reg=REGISTRY, scene=f"""
                $schema: {BASE}scene.json
                Name: Arena
                Placements:
                  - Controller: Goblin
                    StartupTags: [Faction.Player]
                    StartupEffects: [Missing_GE]
                    AttributeOverrides: {{Mana: 10}}
                Regions:
                  - Name: Pit
                    GrantedTags: [Zone.Hazard.Fire]
                SpawnPoints:
                  - Name: Respawn
                    Tags: [Spawn.Player]
            """),
            "'Faction.Player'", "'Missing_GE'", "'Mana'", "'Zone.Hazard.Fire'", "'Spawn.Player'",
        ),
        expect(
            "effect magnitudes and area tags are checked",
            run(attr=ATTRIBUTE, reg=REGISTRY, effect=f"""
                $schema: {BASE}gameplay_effect.json
                Name: GE_Blast
                DurationPolicy: Instant
                Modifiers:
                  - Attribute: Health
                    Operation: Add
                    Magnitude: {{Type: AttributeBased, BackingAttribute: AttackPower}}
                Area:
                  Shape: Sphere
                  Radius: {{Type: SetByCaller, DataTag: Data.Radius}}
                  RequireTags: [Faction.Enemy]
                  ExcludeTags: [State.Dead]
            """),
            "'AttackPower'", "'Data.Radius'", "'State.Dead'",
        ),
        expect(
            "no registry is fine when no tag is used",
            run(attr=ATTRIBUTE, effect=f"""
                $schema: {BASE}gameplay_effect.json
                Name: GE_Hit
                DurationPolicy: Instant
                Modifiers:
                  - Attribute: Health
                    Operation: Add
                    Magnitude: {{Type: ScalableFloat, Value: -1}}
            """),
        ),
        expect(
            "no registry fails once a tag is used",
            run(attr=ATTRIBUTE, effect=f"""
                $schema: {BASE}gameplay_effect.json
                Name: GE_Hit
                DurationPolicy: Instant
                GrantedTags: [State.Damaged]
            """),
            "no tag registry",
        ),
        expect(
            "the shipped examples resolve",
            check(Path(__file__).resolve().parent.parent / "schemas" / "examples"),
        ),
    ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
