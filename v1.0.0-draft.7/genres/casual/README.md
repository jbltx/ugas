# UGAS Genre Pack: Casual

> Low-barrier, short-session casual play, centered on the idle/incremental loop: exponential
> economic growth from multiplicative `Generators × Prestige × Booster` channels feeding a periodic
> passive-income tick, plus an energy gate that rations active play — the same patterns generalize to
> hypercasual "plays remaining" and match-3 lives.

This pack is a copy-and-extend starting point for casual games. It is *additive*: it defines
genre-specific Attributes, Tags, Abilities, and Effects on top of the core UGAS spec and never
redefines a core concept. There is no dedicated case study for casual in the core spec, so the pack
is designed from first principles and grounded in the genre's standard mechanics.

## What's in this pack

| File | Purpose |
|------|---------|
| `spec.adoc` | Additional Casual specification — extends, never replaces, the core spec |
| `entities/attribute_set.yaml` | `IdleEconomySet`: soft currency, income rate, prestige multiplier, energy gate, progression |
| `entities/tag_registry.yaml` | Casual tags: meta-progression, booster, generator, ability, and session states |
| `entities/effect_passive_income.yaml` | `GE_PassiveIncome`: periodic infinite tick; AttributeBased `+Currency` from CurrencyPerSecond |
| `entities/effect_generator_mine.yaml` | `GE_Generator_Mine`: flat `+5` CurrencyPerSecond (entry-tier generator) |
| `entities/effect_generator_factory.yaml` | `GE_Generator_Factory`: flat `+50` CurrencyPerSecond (mid-tier generator) |
| `entities/effect_prestige_boost.yaml` | `GE_PrestigeBoost`: `Multiply` income in the Prestige channel; grants `Meta.State.Prestiged` |
| `entities/effect_energy_regen.yaml` | `GE_EnergyRegen`: periodic infinite `+Energy` (refills the energy gate) |
| `entities/effect_double_income.yaml` | `GE_DoubleIncome`: timed `×2` income in the Booster channel; grants `Booster.State.DoubleIncome` |
| `entities/effect_offline_progress.yaml` | `GE_OfflineProgress`: instant offline "welcome back" payout via a custom Execution |
| `entities/effect_tap_reward.yaml` | `GE_TapReward`: instant `+Currency`, the payload of `GA_Tap` |
| `entities/ability_tap.yaml` | `GA_Tap`: the active click; applies `GE_TapReward` |
| `entities/ability_buy_generator.yaml` | `GA_BuyGenerator`: spend currency to install a generator |
| `entities/ability_prestige.yaml` | `GA_Prestige`: reset for a permanent multiplier; gated by `Meta.State.PrestigeReady` |
| `entities/ability_play.yaml` | `GA_Play`: spend energy to play an active round |
| `entities/gameplay_controller.yaml` | Worked example: an idle save with 3 mines + 1 factory, prestiged, boosted |
| `entities/input_actions.yaml` | Tap, BuyGenerator, Prestige, Play, Boost input actions |
| `entities/input_action_set_idle.yaml` | `Idle`: the single touch-first idle input context |
| `entities/input_mapping_idle_touch.yaml` | Touch bindings: whole-screen tap + on-screen economy buttons |
| `entities/input_mapping_idle_pc.yaml` | Mouse/keyboard bindings for desktop/web |
| `entities/input_modifiers.yaml` | `TapDebounce`, `TouchPressThreshold` |

## How to use

1. Read `spec.adoc` for the genre-specific design (especially the channel-based income aggregation
   and the periodic passive-income tick).
2. Copy the entity files in `entities/` into your project and adapt them — tune the generator income
   values and prestige magnitude in `attribute_set.yaml`/the effect files to set the growth curve, add
   generator tiers as new `GE_Generator_*` effects, or wire the `ExecCalc_OfflineProgress` hook in your
   engine.
3. They validate against the core `schemas/*.yaml`, so AI agents (e.g. the `ugas-schema-author`
   skill) can load and extend them directly.
4. Run `python scripts/validate_schema_examples.py` after changes.

## Published spec

<!-- Link to the built HTML once published, e.g. v<version>/genres/casual/index.html -->
