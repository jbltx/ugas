---
'ugas': minor
---

[Added] World & Spatial Model §17.4 (Zones and Regions). Defines a first-class `Region` — a standing volume (Sphere/Box/Capsule + `SpatialFilter`) that grants Gameplay Tags to the GCs whose anchor is inside it and removes them on exit — formalising the pattern previously only illustrated by the §16.2 biome effects and the §14 "zone transition" buff-clearing. Normative membership semantics: grant-on-entry / remove-on-exit via the reference-counted §7.2 tag container; regions affect occupants only through tag grants (§3.1, never direct mutation); membership re-evaluated on the ambient §10.6 spatial budget (or engine trigger-volume callbacks); region-granted tags are derived and not persisted (§14). Spec only — the authored `RegionDefinition` representation co-develops with the reference implementation. Third installment of the spatial-pillar series.
