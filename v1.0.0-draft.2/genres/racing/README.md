# UGAS Genre Pack: Racing

> Forza-style driving: vehicle performance attributes, track surfaces, tuning parts,
> driver abilities, and a traction pipeline that aggregates grip from every source.

This pack is the copy-and-extend companion to the **Racing case study** in the core spec
(Section 15.2). It ships the matching Attributes, Tags, Abilities, and Effects as
schema-conformant entities, plus a worked vehicle example.

## What's in this pack

| File | Purpose |
|------|---------|
| `spec.adoc` | Additional Racing specification — extends, never replaces, the core spec |
| `entities/attribute_set.yaml` | `VehiclePerformanceSet`: drivetrain, aero, tires, boost resource, telemetry |
| `entities/tag_registry.yaml` | Racing tags: surfaces, vehicle classes/states, ability types, race phases |
| `entities/effect_tuning_sport.yaml` | Infinite tuning upgrade: drivetrain + `+10%` grip (`Upgrades` channel) |
| `entities/effect_biome_mud.yaml` | Mud surface: `-60%` grip (`Surface` channel) and lower top speed |
| `entities/effect_biome_asphalt.yaml` | Asphalt surface: overrides `Surface`-channel grip to the `1.0` baseline |
| `entities/effect_nitro_boost.yaml` | Timed nitro burst applied by `GA_NitroBoost` |
| `entities/effect_drift_charge.yaml` | Timed + periodic boost refill granted while drifting |
| `entities/effect_traction_update.yaml` | Instant `ExecutionCalculation` recomputing `AvailableTraction` |
| `entities/ability_nitro_boost.yaml` | `GA_NitroBoost`: spend boost for a burst of performance |
| `entities/ability_drift.yaml` | `GA_Drift`: hold to slide, trading grip for boost charge |
| `entities/gameplay_controller.yaml` | Worked example: a tuned Sport car on mud showing traction aggregation |

## How to use

1. Read `spec.adoc` for the genre-specific design (especially the traction pipeline).
2. Copy the entity files in `entities/` into your project and adapt them.
3. They validate against the core `schemas/*.yaml`, so AI agents (e.g. the
   `ugas-schema-author` skill) can load and extend them directly.
4. Run `python scripts/validate_schema_examples.py` after changes.

## Published spec

<!-- Link to the built HTML once published, e.g. v<version>/genres/racing/index.html -->
