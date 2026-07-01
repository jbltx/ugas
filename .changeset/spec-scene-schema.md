---
'ugas': minor
---

[Added] `scene` schema (JSON + YAML twins) for §18 Scene Composition. Validates a Scene's `Name` + `Placements` (`Controller`, `InstanceId`, `Position`/`Rotation`, `StartupTags`/`StartupEffects`, `AttributeOverrides`, `Enabled`), its `Regions` (§17.4), and its `SpawnPoints`. Registered with the schema-equivalence and example validators, with an `arena_scene.yaml` worked example. Completes the §18 authoring surface so scenes can be authored and machine-validated.
