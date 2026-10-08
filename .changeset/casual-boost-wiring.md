---
'ugas': patch
---

[Fixed] Casual pack: the `Boost` action now does something. The `Idle` action set listed it, but no mapping bound it and no ability used it, so `GE_DoubleIncome` could not be triggered from input. A new `GA_Boost` applies `GE_DoubleIncome`, with no cost and a 300 s cooldown (`GE_BoostCooldown`, `Cooldown.Ability.Boost`) that outlasts the 60 s booster. `Boost` is bound to `D` on PC and `Touch.Button.Boost` on touch, and the worked controller grants `GA_Boost` and carries the matching cooldown.
