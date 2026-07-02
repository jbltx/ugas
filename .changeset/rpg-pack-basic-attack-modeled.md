---
'ugas': patch
---

[Changed] RPG genre pack — re-author `GA_BasicAttack` onto the modeled `ApplyEffectToTarget`. The shipped attack resolved its hit as `[PlayMontage, WaitGameplayEvent, ApplyEffectToTarget{EffectClass only}]`; a reference runtime treats `PlayMontage`/`WaitGameplayEvent` as no-ops and the range-less `ApplyEffectToTarget` self-acquires within a zero-radius sphere, so the default attack connected with nobody as shipped. It now applies `GE_BasicAttackDamage` to the nearest `Team.Hostile` within `MaxRange` — with new `Team.Friendly`/`Team.Hostile` affiliation tags in the registry (affiliation is engine-assigned per §17.2; the worked-example hero is `Team.Friendly`). `PlayMontage`/`WaitGameplayEvent` remain as documented engine seams for the swing + hit-window. Surfaced by the real-world RPG harness evaluation (same class as the strategy and combat pack fixes).
