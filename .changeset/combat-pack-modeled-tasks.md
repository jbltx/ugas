---
'ugas': patch
---

[Changed] Combat genre pack — re-author `GA_LightAttack`, `GA_HeavyAttack`, and `GA_Special` onto the modeled `ApplyEffectToTarget` ability task. Each normal previously resolved its hit as `[WaitDelay, WaitTargetData(MeleeSweep), ApplyEffectToTarget{EffectClass only}, WaitDelay]` — but `WaitTargetData` is an unmodeled task a reference runtime treats as a no-op, and the follow-on `ApplyEffectToTarget` carried no `MaxRange`, so the attacks connected with nobody as shipped. They now use `ApplyEffectToTarget` with `MaxRange` + `RequireTag: Team.Hostile` (nearest hostile in range), dropping `WaitTargetData`; the `WaitDelay` startup/recovery frames are unchanged. High/mid/low hitzone guard rules and which fighter is `Team.Hostile` remain documented engine targeting seams (§17.2). Surfaced by the real-world fighting harness evaluation (same class as the strategy-pack fix).
