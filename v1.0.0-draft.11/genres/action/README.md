# UGAS Genre Pack: Action / Action-Adventure

> Mario-style platforming: tight movement attributes, a variable-height jump, power-ups,
> and a tag-driven movement state machine — the core of the wider action-adventure family.

This pack is the copy-and-extend companion to the **Platformer case study** in the core spec
(Section 15.1). It ships the matching Attributes, Tags, Abilities, and Effects as
schema-conformant entities, plus a worked hero example.

## What's in this pack

| File | Purpose |
|------|---------|
| `spec.adoc` | Additional Action specification — extends, never replaces, the core spec |
| `entities/attribute_set.yaml` | `PlatformerMovementSet`: jump/movement feel, form, and vitals |
| `entities/tag_registry.yaml` | Action tags: movement states, power-ups, ability types, hazards |
| `entities/effect_grounded.yaml` | `GE_Grounded`: physics-owned grounded state |
| `entities/effect_in_air.yaml` | `GE_InAir`: airborne state granted by `GA_Jump` |
| `entities/effect_jump_cut.yaml` | `GE_JumpCut`: raises gravity for a variable-height jump |
| `entities/effect_super_mushroom.yaml` | `GE_SuperMushroom`: doubles size, grants `+1` health |
| `entities/effect_invincibility_star.yaml` | `GE_InvincibilityStar`: timed immunity + speed boost |
| `entities/effect_contact_damage.yaml` | `GE_ContactDamage`: `-1` health on contact |
| `entities/ability_jump.yaml` | `GA_Jump`: signature variable-height jump |
| `entities/ability_ground_pound.yaml` | `GA_GroundPound`: airborne radius slam |
| `entities/gameplay_controller.yaml` | Worked example: a "Super" hero showing power-up aggregation |

## How to use

1. Read `spec.adoc` for the genre-specific design (especially the movement state machine).
2. Copy the entity files in `entities/` into your project and adapt them.
3. They validate against the core `schemas/*.yaml`, so AI agents (e.g. the
   `ugas-schema-author` skill) can load and extend them directly.
4. Run `python scripts/validate_schema_examples.py` after changes.

## Published spec

<!-- Link to the built HTML once published, e.g. v<version>/genres/action/index.html -->
