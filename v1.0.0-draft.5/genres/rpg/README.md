# UGAS Genre Pack: Role-Playing (RPG)

> Action-RPG (Diablo-style) characters: primary stats, items, abilities, and a
> multiplicative damage-bucket pipeline.

This pack is the copy-and-extend companion to the **ARPG case study** in the core spec
(Section 15.3). It ships the matching Attributes, Tags, Abilities, and Effects as
schema-conformant entities, plus a worked hero example.

## What's in this pack

| File | Purpose |
|------|---------|
| `spec.adoc` | Additional RPG specification — extends, never replaces, the core spec |
| `entities/attribute_set.yaml` | `RPGCoreAttributes`: primary stats, vitals, derived combat stats, progression |
| `entities/tag_registry.yaml` | RPG tags: damage types, ability types, combat status, items, classes |
| `entities/effect_mainstat_strength.yaml` | `+1%` WeaponDamage per Strength (`MainStat` channel) |
| `entities/effect_weapon_firesword.yaml` | Fire Sword equip effect: `+20%` WeaponDamage (`DamageBonuses` channel) |
| `entities/effect_basic_attack_damage.yaml` | Instant damage equal to the source's WeaponDamage |
| `entities/effect_regeneration.yaml` | Timed + periodic health regeneration buff |
| `entities/ability_basic_attack.yaml` | `GA_BasicAttack`: single-target weapon strike |
| `entities/ability_whirlwind.yaml` | `GA_Whirlwind`: signature melee AoE |
| `entities/gameplay_controller.yaml` | Worked example: a level-5 Barbarian showing damage-bucket aggregation |

## How to use

1. Read `spec.adoc` for the genre-specific design (especially the damage buckets).
2. Copy the entity files in `entities/` into your project and adapt them.
3. They validate against the core `schemas/*.yaml`, so AI agents (e.g. the
   `ugas-schema-author` skill) can load and extend them directly.
4. Run `python scripts/validate_schema_examples.py` after changes.

## Published spec

<!-- Link to the built HTML once published, e.g. v<version>/genres/rpg/index.html -->
