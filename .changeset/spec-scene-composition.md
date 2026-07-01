---
'ugas': minor
---

[Added] Scene Composition §18 (new Part VII) — the content layer that instances authored gameplay definitions into a playable world. Defines **Placements** (a §4 controller config instanced at a world pose with startup tags/effects/attribute overrides), **Scenes** (a composable, loadable unit of placements + §17.4 regions + spawn points, with a normative regions→placements→spawn-points load order), **Spawn Points** (named poses selected by §17.2 queries for dynamic spawning), **composition** (additive `Extends`) and **streaming** (governed by §17.6 partitioning + §14 persistence), and **determinism/persistence** (deterministic declaration-order load, seeded §9.5 RNG, per-instance §14 snapshots keyed by InstanceId; derived tags re-evaluated, not serialised). Spec only; a scene schema, reference implementation, and authoring skill are follow-ups.
