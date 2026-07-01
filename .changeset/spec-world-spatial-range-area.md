---
'ugas': minor
---

[Added] World & Spatial Model §17.3 (Range and Area Application) plus the schema fields that back it. `MaxRange` is added to the ability schema — a target-requiring activation must be within range (§17.2 `Distance`), validated server-side per §13.7. An optional `Area` block is added to the effect schema (Shape `Sphere`/`Cone`, an `AttributeBased`-capable `Radius`, a tag/affiliation filter, and `MaxTargets`) so an effect can apply to every matching anchor within an area via a single §17.2 query — the multi-target/AoE capability the genre packs previously faked with a hard-coded task-parameter radius. Both `.json`/`.yaml` schema twins updated; additive and backward-compatible (no new `required` fields, no `additionalProperties: false`). Second installment of the spatial-pillar series.
