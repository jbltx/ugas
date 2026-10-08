---
'ugas': patch
---

[Fixed] Strategy pack: `GE_TrainCooldown` now lasts 15 s, the same as `GA_TrainUnit`'s `WaitDelay`. At 12 s, `Cooldown.Ability.Train` dropped 3 s before the unit finished training, so anything reading the tag saw the producer as free while it was still busy.
