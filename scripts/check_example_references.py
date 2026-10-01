#!/usr/bin/env python3
"""Check that the gameplay examples resolve as a set.

Loads every gameplay entity under a directory (default: schemas/examples) and
asserts each cross-entity reference names an entity in that same directory:

- effect Modifiers[].Attribute and attribute Clamping Min/Max names -> attribute (§5.4, §9)
- ability Cost / Cooldown and task Params.EffectClass -> effect (§8.5)
- effect GrantedAbilities[].AbilityClass -> ability
- every tag an ability or effect uses -> the tag registry (§7)

Schema validation cannot catch these: each file is valid on its own. Consumers
vendor the examples as one set, so a dangling name is a broken example.

Run from the repo root: check_example_references.py [DIR ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

ABILITY_TAG_FIELDS = (
    "AbilityTags",
    "BlockedByTags",
    "BlockAbilitiesWithTags",
    "CancelAbilitiesWithTags",
    "ActivationRequiredTags",
    "ActivationBlockedTags",
    "ActivationOwnedTags",
)
EFFECT_TAG_FIELDS = ("GrantedTags", "ApplicationRequiredTags", "GameplayCues")


def schema_type(doc: dict) -> str | None:
    ref = doc.get("$schema")
    return ref.rsplit("/", 1)[-1].removesuffix(".json") if isinstance(ref, str) else None


def load(directory: Path):
    """Return {type: [(source, doc), ...]} for every document under directory."""
    entities: dict[str, list[tuple[str, dict]]] = {}
    for path in sorted(directory.rglob("*")):
        if path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")):
            if isinstance(doc, dict):
                rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
                entities.setdefault(schema_type(doc), []).append((str(rel), doc))
    return entities


def check(directory: Path) -> list[str]:
    entities = load(directory)
    attributes = [(src, a) for src, a in entities.get("attribute", [])]
    for src, aset in entities.get("attribute_set", []):
        attributes += [(src, a) for a in aset.get("Attributes") or []]

    attribute_names = {a.get("Name") for _, a in attributes}
    effect_names = {e.get("Name") for _, e in entities.get("gameplay_effect", [])}
    ability_names = {a.get("Name") for _, a in entities.get("gameplay_ability", [])}
    registered = {
        t.get("Tag")
        for _, reg in entities.get("gameplay_tag", [])
        for t in reg.get("Tags") or []
    }

    errors: list[str] = []

    def expect(src: str, field: str, name, known: set, kind: str) -> None:
        if name not in known:
            errors.append(f"{src}: {field} '{name}' names no {kind} in {directory.name}/")

    def expect_tag(src: str, field: str, tag: str) -> None:
        # A parent of a registered tag is implicitly registered (§7 hierarchy).
        if tag not in registered and not any(r.startswith(tag + ".") for r in registered):
            errors.append(f"{src}: {field} tag '{tag}' is not in the tag registry")

    for src, attr in attributes:
        for bound in ("Min", "Max"):
            value = (attr.get("Clamping") or {}).get(bound)
            if isinstance(value, str):
                expect(src, f"{attr.get('Name')}.Clamping.{bound}", value, attribute_names, "attribute")

    for src, effect in entities.get("gameplay_effect", []):
        for mod in effect.get("Modifiers") or []:
            expect(src, "Modifiers.Attribute", mod.get("Attribute"), attribute_names, "attribute")
        for grant in effect.get("GrantedAbilities") or []:
            expect(src, "GrantedAbilities.AbilityClass", grant.get("AbilityClass"), ability_names, "ability")
        for field in EFFECT_TAG_FIELDS:
            for tag in effect.get(field) or []:
                expect_tag(src, field, tag)

    for src, ability in entities.get("gameplay_ability", []):
        for field in ("Cost", "Cooldown"):
            if ability.get(field) is not None:
                expect(src, field, ability[field], effect_names, "effect")
        for field in ABILITY_TAG_FIELDS:
            for tag in (ability.get("Tags") or {}).get(field) or []:
                expect_tag(src, f"Tags.{field}", tag)
        for task in ability.get("Tasks") or []:
            params = task.get("Params") or {}
            if "EffectClass" in params:
                expect(src, "Tasks.Params.EffectClass", params["EffectClass"], effect_names, "effect")
            if "EventTag" in params:
                expect_tag(src, "Tasks.Params.EventTag", params["EventTag"])

    if (entities.get("gameplay_ability") or entities.get("gameplay_effect")) and not registered:
        errors.append(f"{directory.name}/: abilities or effects use tags but no tag registry was found")
    return errors


def main(argv: list[str]) -> int:
    directories = [Path(a).resolve() for a in argv] or [ROOT / "schemas" / "examples"]
    errors = [e for d in directories for e in check(d)]
    if errors:
        print(f"✗ {len(errors)} unresolved example reference(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"✓ example references resolve ({', '.join(d.name for d in directories)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
