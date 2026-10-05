#!/usr/bin/env python3
"""Check that the gameplay examples resolve as a set.

Loads every gameplay entity under a directory (default: schemas/examples) and
asserts each schema-supported cross-entity reference names an entity in that
same directory:

- attribute: Clamping Min/Max names -> attribute (§5.4)
- attribute set: Dependencies -> attribute set (§6)
- effect: Modifiers[].Attribute, and BackingAttribute in any magnitude
  (modifier, Duration, Area.Radius) -> attribute (§9); GrantedAbilities[]
  AbilityClass -> ability, InputID -> input action
- ability: Cost / Cooldown and task Params.EffectClass -> effect (§8.5), task
  Params.InputID (WaitInputRelease, WaitInputPressed) -> input action (§10.3)
- controller: AttributeSets[] Name -> attribute set, Attributes[].Name and
  CapturedAttributes keys -> attribute, GrantedAbilities[].AbilityClass and
  ActiveEffects[].SourceAbility -> ability, ActiveEffects[].EffectClass -> effect,
  InputID -> input action, ActiveActionSets -> input action set (§4, §14)
- scene: Extends -> scene, StartupEffects -> effect, AttributeOverrides keys
  -> attribute (§18)
- input: action set Actions and mapping Bindings[].Action -> input action,
  mapping ActionSet -> input action set, each mapping Bindings[].Action -> a member
  of that set's Actions, Bindings[].Modifiers -> input modifier (§11)
- every tag any of them uses -> the tag registry (§7): ability Tags.*, task
  Params *Tag / *Tags, effect GrantedTags, ApplicationRequiredTags,
  GameplayCues, Area.RequireTags / ExcludeTags and SetByCaller DataTag,
  controller OwnedTags and SetByCallerMagnitudes keys, scene StartupTags,
  Regions[].GrantedTags and SpawnPoints[].Tags, input ActionTags,
  ActivationTags and binding RequiredTags

Not checked, because UGAS defines no named entity for them: scene
Placements[].Controller (a GameplayControllerConfig, §18.2 -- the controller
schema is a runtime snapshot with no Name), CalculatorClass, Curve, and
instance ids such as Handle and InstigatorGC, nor task Params that name
engine assets (MontageToPlay, ProjectileClass).

Schema validation cannot catch these: each file is valid on its own. Consumers
vendor the examples as one set, so a dangling name is a broken example.

Run from the repo root: check_example_references.py [DIR ...]
"""
from __future__ import annotations

import json
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
        if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        # Same skips as validate_schema_examples.py: pack metadata and the
        # generated manifest are not schema-bearing entities.
        if path.name in {"pack.yaml", "index.json"}:
            continue
        text = path.read_text(encoding="utf-8")
        docs = [json.loads(text)] if path.suffix.lower() == ".json" else yaml.safe_load_all(text)
        for doc in docs:
            if isinstance(doc, dict):
                rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
                entities.setdefault(schema_type(doc), []).append((str(rel), doc))
    return entities


def items(value) -> list:
    return value if isinstance(value, list) else []


def mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def check(directory: Path) -> list[str]:
    entities = load(directory)
    attributes = [(src, a) for src, a in entities.get("attribute", [])]
    for src, aset in entities.get("attribute_set", []):
        attributes += [(src, a) for a in items(aset.get("Attributes"))]

    def names(kind: str) -> set:
        return {e.get("Name") for _, e in entities.get(kind, [])}

    known = {
        "attribute": {a.get("Name") for _, a in attributes},
        "attribute set": names("attribute_set"),
        "effect": names("gameplay_effect"),
        "ability": names("gameplay_ability"),
        "scene": names("scene"),
        "input action": names("input_action"),
        "input action set": names("input_action_set"),
        "input modifier": names("input_modifier"),
    }
    registered = {
        t.get("Tag")
        for _, reg in entities.get("gameplay_tag", [])
        for t in items(reg.get("Tags"))
    }

    errors: list[str] = []
    tag_uses: list[tuple[str, str, str]] = []

    def expect(src: str, field: str, name, kind: str) -> None:
        if name not in known[kind]:
            errors.append(f"{src}: {field} '{name}' names no {kind} in {directory.name}/")

    def expect_all(src: str, field: str, values, kind: str) -> None:
        for name in items(values):
            expect(src, field, name, kind)

    def tags(src: str, field: str, values) -> None:
        for tag in items(values):
            tag_uses.append((src, field, tag))

    def magnitude(src: str, field: str, mag) -> None:
        mag = mapping(mag)
        if mag.get("BackingAttribute") is not None:
            expect(src, f"{field}.BackingAttribute", mag["BackingAttribute"], "attribute")
        if mag.get("DataTag") is not None:
            tags(src, f"{field}.DataTag", [mag["DataTag"]])

    def grants(src: str, field: str, values) -> None:
        for grant in items(values):
            expect(src, f"{field}.AbilityClass", grant.get("AbilityClass"), "ability")
            if grant.get("InputID") is not None:
                expect(src, f"{field}.InputID", grant["InputID"], "input action")

    for src, attr in attributes:
        for bound in ("Min", "Max"):
            value = mapping(attr.get("Clamping")).get(bound)
            if isinstance(value, str):
                expect(src, f"{attr.get('Name')}.Clamping.{bound}", value, "attribute")

    for src, aset in entities.get("attribute_set", []):
        expect_all(src, "Dependencies", aset.get("Dependencies"), "attribute set")

    for src, effect in entities.get("gameplay_effect", []):
        magnitude(src, "Duration", effect.get("Duration"))
        for mod in items(effect.get("Modifiers")):
            expect(src, "Modifiers.Attribute", mod.get("Attribute"), "attribute")
            magnitude(src, "Modifiers.Magnitude", mod.get("Magnitude"))
        grants(src, "GrantedAbilities", effect.get("GrantedAbilities"))
        for field in EFFECT_TAG_FIELDS:
            tags(src, field, effect.get(field))
        area = mapping(effect.get("Area"))
        magnitude(src, "Area.Radius", area.get("Radius"))
        tags(src, "Area.RequireTags", area.get("RequireTags"))
        tags(src, "Area.ExcludeTags", area.get("ExcludeTags"))

    for src, ability in entities.get("gameplay_ability", []):
        for field in ("Cost", "Cooldown"):
            if ability.get(field) is not None:
                expect(src, field, ability[field], "effect")
        for field in ABILITY_TAG_FIELDS:
            tags(src, f"Tags.{field}", mapping(ability.get("Tags")).get(field))
        for task in items(ability.get("Tasks")):
            for key, value in mapping(task.get("Params")).items():
                if key == "EffectClass":
                    expect(src, "Tasks.Params.EffectClass", value, "effect")
                elif key == "InputID":
                    expect(src, "Tasks.Params.InputID", value, "input action")
                elif key.endswith("Tag") and isinstance(value, str):
                    tags(src, f"Tasks.Params.{key}", [value])
                elif key.endswith("Tags"):
                    tags(src, f"Tasks.Params.{key}", value)

    for src, gc in entities.get("gameplay_controller", []):
        for aset in items(gc.get("AttributeSets")):
            expect(src, "AttributeSets.Name", aset.get("Name"), "attribute set")
            for attr in items(aset.get("Attributes")):
                expect(src, "AttributeSets.Attributes.Name", attr.get("Name"), "attribute")
        grants(src, "GrantedAbilities", gc.get("GrantedAbilities"))
        for active in items(gc.get("ActiveEffects")):
            expect(src, "ActiveEffects.EffectClass", active.get("EffectClass"), "effect")
            if active.get("SourceAbility") is not None:
                expect(src, "ActiveEffects.SourceAbility", active["SourceAbility"], "ability")
            expect_all(src, "ActiveEffects.CapturedAttributes",
                       list(mapping(active.get("CapturedAttributes"))), "attribute")
            tags(src, "ActiveEffects.SetByCallerMagnitudes",
                 list(mapping(active.get("SetByCallerMagnitudes"))))
        expect_all(src, "ActiveActionSets", gc.get("ActiveActionSets"), "input action set")
        tags(src, "OwnedTags", gc.get("OwnedTags"))

    for src, scene in entities.get("scene", []):
        expect_all(src, "Extends", scene.get("Extends"), "scene")
        for placement in items(scene.get("Placements")):
            tags(src, "Placements.StartupTags", placement.get("StartupTags"))
            expect_all(src, "Placements.StartupEffects", placement.get("StartupEffects"), "effect")
            expect_all(src, "Placements.AttributeOverrides",
                       list(mapping(placement.get("AttributeOverrides"))), "attribute")
        for region in items(scene.get("Regions")):
            tags(src, "Regions.GrantedTags", region.get("GrantedTags"))
        for spawn in items(scene.get("SpawnPoints")):
            tags(src, "SpawnPoints.Tags", spawn.get("Tags"))

    for src, action in entities.get("input_action", []):
        tags(src, "Tags.ActionTags", mapping(action.get("Tags")).get("ActionTags"))

    for src, aset in entities.get("input_action_set", []):
        expect_all(src, "Actions", aset.get("Actions"), "input action")
        activation = mapping(aset.get("ActivationTags"))
        tags(src, "ActivationTags.RequiredTags", activation.get("RequiredTags"))
        tags(src, "ActivationTags.BlockedTags", activation.get("BlockedTags"))

    set_actions = {
        aset.get("Name"): set(items(aset.get("Actions")))
        for _, aset in entities.get("input_action_set", [])
    }
    for src, imap in entities.get("input_mapping", []):
        set_name = imap.get("ActionSet")
        expect(src, "ActionSet", set_name, "input action set")
        for binding in items(imap.get("Bindings")):
            action = binding.get("Action")
            expect(src, "Bindings.Action", action, "input action")
            # A mapping binds within its Action Set (§11.5), so the action must be a member.
            if set_name in set_actions and action not in set_actions[set_name]:
                errors.append(f"{src}: Bindings.Action '{action}' is not in action set '{set_name}'")
            expect_all(src, "Bindings.Modifiers", binding.get("Modifiers"), "input modifier")
            tags(src, "Bindings.Tags.RequiredTags", mapping(binding.get("Tags")).get("RequiredTags"))

    if tag_uses and not registered:
        errors.append(f"{directory.name}/: examples use tags but no tag registry was found")
    elif registered:
        for src, field, tag in tag_uses:
            # A parent of a registered tag is implicitly registered (§7 hierarchy).
            if tag not in registered and not any(r.startswith(f"{tag}.") for r in registered):
                errors.append(f"{src}: {field} tag '{tag}' is not in the tag registry")
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
