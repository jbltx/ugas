# UGAS Genre Pack: Strategy

> RTS / 4X / tower-defense: unit combat stats, a resource economy driven by periodic income,
> tech-upgrade channels, and a damage-type × armor-class rock-paper-scissors matrix resolved in a
> custom Execution.

This pack is designed from first principles (the core spec ships no strategy case study). It
provides the matching Attributes, Tags, Abilities, and Effects as schema-conformant entities, plus a
worked unit example. Its two signature mechanics are an **economy of periodic income effects** and a
**damage-type × armor-class mitigation matrix** (`ExecCalc_ArmorMitigation`), with **tech upgrades**
stacking declaratively through a modifier `Channel`.

## What's in this pack

| File | Purpose |
|------|---------|
| `spec.adoc` | Additional Strategy specification — extends, never replaces, the core spec |
| `entities/attribute_set.yaml` | `UnitStatsSet`: unit combat stats, mitigation telemetry, and the commander-scoped economy |
| `entities/tag_registry.yaml` | Strategy tags: unit types, armor classes, damage types, unit states, ability types, factions |
| `entities/effect_mineral_income.yaml` | `GE_MineralIncome`: infinite + `Period 1.0`, `+5` Minerals/sec (the economy showcase) |
| `entities/effect_energy_regen.yaml` | `GE_EnergyRegen`: infinite + `Period 2.0`, refills a caster's Energy |
| `entities/effect_unit_damage.yaml` | `GE_UnitDamage`: instant; runs `ExecCalc_ArmorMitigation` (matrix + flat armor) |
| `entities/effect_weapon_upgrade.yaml` | `GE_WeaponUpgrade`: infinite `Multiply +0.15` AttackDamage in the `Upgrades` channel |
| `entities/effect_armor_upgrade.yaml` | `GE_ArmorUpgrade`: infinite flat `+2` Armor per rank |
| `entities/effect_constructing.yaml` | `GE_Constructing`: timed state granting `Unit.State.Constructing` (blocks the unit's abilities) |
| `entities/effect_slow.yaml` | `GE_Slow`: timed `Multiply -0.4` MoveSpeed in the `Debuffs` channel (tower-defense flavour) |
| `entities/effect_areastrike_damage.yaml` | `GE_AreaStrikeDamage`: instant Magic AoE via `ExecCalc_ArmorMitigation` |
| `entities/ability_auto_attack.yaml` | `GA_AutoAttack`: range-gated, AttackSpeed-paced; applies `GE_UnitDamage` |
| `entities/ability_construct_building.yaml` | `GA_ConstructBuilding`: spend Minerals, place a site, build over time |
| `entities/ability_train_unit.yaml` | `GA_TrainUnit`: spend Minerals + supply; produce a unit on a cooldown |
| `entities/ability_area_strike.yaml` | `GA_AreaStrike`: spend Energy to blast an area with Magic damage and a slow |
| `entities/gameplay_controller.yaml` | Worked example: a Siege Tank showing the tech-channel AttackDamage aggregation |
| `entities/input_actions.yaml` | RTS actions: Select, AttackMove, Build, Train, CastAbility, CameraPan |
| `entities/input_action_set_command.yaml` | `Command` action set grouping the strategy inputs |
| `entities/input_mapping_command_pc.yaml` | PC keyboard + mouse bindings (point-and-click + hotkeys) |
| `entities/input_modifiers.yaml` | Camera-feel input modifiers (scroll speed, dead zone, smoothing) |

## How to use

1. Read `spec.adoc` for the genre-specific design (especially the periodic economy and the damage
   matrix).
2. Copy the entity files in `entities/` into your project and adapt them.
3. They validate against the core `schemas/*.yaml`, so AI agents (e.g. the `ugas-schema-author`
   skill) can load and extend them directly.
4. Implement the `ExecCalc_ArmorMitigation` hook in your engine; everything else is data.
5. Run `python scripts/validate_schema_examples.py` after changes.

## Published spec

<!-- Link to the built HTML once published, e.g. v<version>/genres/strategy/index.html -->
