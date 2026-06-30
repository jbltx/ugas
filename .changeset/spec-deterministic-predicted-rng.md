---
'ugas': minor
---

[Added] Normative rule for randomness in Execution Calculations (§9.5) that resolves the predicted-RNG desync: any randomness consumed during a *predicted* Execution Calculation MUST be drawn from a deterministic, seeded stream exposed as `context.RNG`, seeded from `PredictionKey.Seed` (§13.8.1) and positioned per the `(Sub, draw index)` scheme so a predicting client and the authoritative server roll identically and no rollback is caused by RNG drift. Defines the small `DeterministicRNG` interface (`NextFloat()` / `NextInt(min, max)`) that conforming implementations MUST provide on the calculation `context`, and adds the matching `RNG: DeterministicRNG` field to the `EffectContext` struct (§9.9). Forbids ambient `RandomFloat()`-style globals for gameplay-affecting rolls, including in single-player / non-networked play (where the same `context.RNG` path is seeded from a local source).

[Added] Non-predictable escape hatch: a calculation that genuinely needs non-reproducible or server-only randomness MUST declare `Predictable = false` (a `RequiresServerAuthority` marker) on `ExecutionCalculation`, in which case the activation aborts prediction and falls back to server authority for the random outcome, tied to the §13.8.2 fallback.

[Fixed] §15.4 `ExecCalc_ArmorPenetration` replaced the bare `if (RandomFloat() < critChance)` critical-hit roll with `if (context.RNG.NextFloat() < critChance)` and a comment pointing to the §9.5 rule and the §13.8.1 seed. Documentation only — no schema or entity changes; references the §13.8.1 `PredictionKey.Seed` hook without modifying §13. Closes #5.
