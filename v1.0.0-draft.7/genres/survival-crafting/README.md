# UGAS Genre Pack: Survival / Crafting

> Survive against a clock of needs: hunger, thirst, stamina, and body temperature that drain over
> time via periodic effects, with threshold-triggered cascading penalties (starvation, dehydration,
> hypothermia) that drain health — plus a gather → craft → build economy and an encumbrance limit.

This pack is a copy-and-extend starting point for survival / crafting games. It is *additive*: it
defines genre-specific Attributes, Tags, Abilities, and Effects on top of the core UGAS spec and
never redefines a core concept. There is no dedicated case study for survival in the core spec, so
the pack is designed from first principles and grounded in the genre's standard mechanics.

## What's in this pack

| File | Purpose |
|------|---------|
| `spec.adoc` | Additional Survival / Crafting specification — extends, never replaces, the core spec |
| `entities/attribute_set.yaml` | `SurvivorVitalsSet`: needs (hunger/thirst/stamina), body-temperature comfort window, survivability, encumbrance/crafting economy |
| `entities/tag_registry.yaml` | Survival tags: survival/activity states, items, resource nodes, biomes |
| `entities/effect_hunger_decay.yaml` | `GE_HungerDecay`: periodic infinite `Hunger` drain |
| `entities/effect_thirst_decay.yaml` | `GE_ThirstDecay`: periodic infinite `Thirst` drain |
| `entities/effect_stamina_regen.yaml` | `GE_StaminaRegen`: periodic infinite `Stamina` regen |
| `entities/effect_starvation.yaml` | `GE_Starvation`: periodic `Health` drain; grants `Survival.State.Starving` |
| `entities/effect_dehydration.yaml` | `GE_Dehydration`: periodic `Health` drain; grants `Survival.State.Dehydrated` |
| `entities/effect_exposure_cold.yaml` | `GE_Exposure_Cold`: periodic `BodyTemperature` push down; grants `Survival.State.Cold` |
| `entities/effect_exposure_heat.yaml` | `GE_Exposure_Heat`: periodic `BodyTemperature` push up; grants `Survival.State.Hot` |
| `entities/effect_hypothermia.yaml` | `GE_Hypothermia`: periodic `Health` drain + `Cold`-channel `MoveSpeed` cut |
| `entities/effect_overencumbered.yaml` | `GE_Overencumbered`: `Encumbrance`-channel `MoveSpeed` cut; grants the state |
| `entities/effect_exhaustion.yaml` | `GE_Exhaustion`: gating-only `Survival.State.Exhausted` (blocks sprint) |
| `entities/effect_eat_food.yaml` | `GE_EatFood`: instant `+Hunger` |
| `entities/effect_drink_water.yaml` | `GE_DrinkWater`: instant `+Thirst` |
| `entities/effect_gather_resource.yaml` | `GE_GatherResource`: instant `+Materials` and `+CarryWeight` |
| `entities/effect_gathering.yaml` | `GE_Gathering`: timed gathering activity state |
| `entities/effect_crafting.yaml` | `GE_Crafting`: timed crafting activity state |
| `entities/effect_sprinting.yaml` | `GE_Sprinting`: timed + periodic `Stamina` drain; grants `Survival.State.Sprinting` |
| `entities/effect_crafted_tool.yaml` | `GE_CraftedTool`: infinite `+MaxCarryWeight` buff |
| `entities/effect_survival_tick.yaml` | `GE_SurvivalTick`: optional periodic `ExecCalc_SurvivalTick` coupling deficits into one `Health` delta |
| `entities/ability_gather.yaml` | `GA_Gather`: harvest a node into the inventory |
| `entities/ability_craft.yaml` | `GA_Craft`: spend materials to craft a tool |
| `entities/ability_build.yaml` | `GA_Build`: spend materials to place a structure |
| `entities/ability_consume_food.yaml` | `GA_ConsumeFood`: eat to restore `Hunger` |
| `entities/ability_drink.yaml` | `GA_Drink`: drink to restore `Thirst` |
| `entities/ability_sprint.yaml` | `GA_Sprint`: hold to sprint, draining `Stamina` |
| `entities/input_actions.yaml` | Survival input actions (Move, Look, Jump, Sprint, Gather, Craft, Build, Eat, Drink) |
| `entities/input_action_set_survival.yaml` | `SurvivalOnFoot` action set, active while alive |
| `entities/input_mapping_survival_pc.yaml` | PC keyboard + mouse bindings for `SurvivalOnFoot` |
| `entities/input_modifiers.yaml` | Reusable input modifiers (mouse sensitivity, dead zone, normalize) |
| `entities/gameplay_controller.yaml` | Worked example: a survivor at night — cold + starving + overencumbered |

## How to use

1. Read `spec.adoc` for the genre-specific design (especially the needs/vitals decay loop and the
   threshold-cascade split between engine logic and data).
2. Copy the entity files in `entities/` into your project and adapt them — tune the decay rates in
   the `GE_*Decay` effects and the penalty magnitudes first, add biomes as area effects, or wire the
   threshold detectors (and the optional `ExecCalc_SurvivalTick`) in your engine.
3. They validate against the core `schemas/*.yaml`, so AI agents (e.g. the `ugas-schema-author`
   skill) can load and extend them directly.
4. Run `python scripts/validate_schema_examples.py` after changes.

## Published spec

<!-- Link to the built HTML once published, e.g. v<version>/genres/survival-crafting/index.html -->
