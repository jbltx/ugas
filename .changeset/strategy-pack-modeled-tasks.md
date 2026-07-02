---
'ugas': patch
---

[Changed] Strategy genre pack — re-author `GA_AutoAttack` and `GA_AreaStrike` onto the modeled ability tasks. Auto-attack now uses `ApplyEffectToTarget` (nearest `Faction.Hostile` within `MaxRange`) and area-strike uses `ApplyEffectToActorsInRadius` (blast sparing `Faction.Friendly`), instead of the `WaitTargetData` placeholder — which a reference runtime treats as a no-op, so the abilities hit nobody as shipped. Affiliation (who is `Faction.Hostile`) and ground-target selection remain documented engine seams (§17.2). Surfaced by the real-world strategy harness evaluation.
