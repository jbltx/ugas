#!/usr/bin/env python3
"""Regression tests for check_example_references.py. Standalone: no pytest.

Run from the repo root: python scripts/test_check_example_references.py
"""
from __future__ import annotations

import json
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
            Path(tmp, name if "." in name else f"{name}.yaml").write_text(textwrap.dedent(body), encoding="utf-8")
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
                    Shape: Sphere
                    Origin: [0, 0, 0]
                    Radius: 4
                    Filter: {{ExcludeTags: [State.Immune]}}
                    GrantedTags: [Zone.Hazard.Fire]
                SpawnPoints:
                  - Name: Respawn
                    Tags: [Spawn.Player]
            """),
            "'Faction.Player'", "'Missing_GE'", "'Mana'", "'Zone.Hazard.Fire'", "'State.Immune'",
            "'Spawn.Player'",
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
            "task Params.InputID is checked",
            run(reg=REGISTRY, jump=f"""
                $schema: {BASE}input_action.json
                Name: Jump
                ValueType: Digital
            """, ability=f"""
                $schema: {BASE}gameplay_ability.json
                Name: GA_Charge
                Tasks:
                  - Type: WaitInputRelease
                    Params: {{InputID: Charge}}
            """),
            "Tasks.Params.InputID 'Charge'",
        ),
        expect(
            "mapping bindings must be in the mapping's action set",
            run(jump=f"""
                $schema: {BASE}input_action.json
                Name: Jump
                ValueType: Digital
            """, steer=f"""
                $schema: {BASE}input_action.json
                Name: Steer
                ValueType: Axis1D
            """, sets=f"""
                $schema: {BASE}input_action_set.json
                Name: OnFoot
                Actions: [Jump]
                ---
                $schema: {BASE}input_action_set.json
                Name: InVehicle
                Actions: [Steer]
            """, mapping=f"""
                $schema: {BASE}input_mapping.json
                ActionSet: OnFoot
                Bindings:
                  - Action: Jump
                    Inputs: [{{Device: Keyboard, Input: Space}}]
                  - Action: Steer
                    Inputs: [{{Device: Keyboard, Input: A}}]
            """),
            "'Steer' is not in action set 'OnFoot'",
        ),
        expect(
            "json examples are checked",
            run(**{"ability.json": json.dumps({
                "$schema": f"{BASE}gameplay_ability.json",
                "Name": "GA_Json",
                "Cost": "MissingEffect",
            })}),
            "Cost 'MissingEffect'",
        ),
        expect(
            "the shipped examples resolve",
            check(Path(__file__).resolve().parent.parent / "schemas" / "examples"),
        ),
    ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
