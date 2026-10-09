---
'ugas': patch
---

[Fixed] Casual pack: `Boost` is no longer bound to `D` on PC or to `Touch.Button.Boost` on touch. `GA_Boost` has no cost, so a direct binding let a player claim `GE_DoubleIncome` every cooldown without watching an ad or opening a chest. Engine logic fires `Boost` once the reward pays out, as `ability_boost.yaml` already describes.
