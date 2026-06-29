# UGAS Genre Pack: Combat

> Skill-based melee dueling (fighting / brawler / hack-and-slash): frame-data states (hitstun &
> blockstun), a poise → stagger meter that opens punish windows, a guard/block damage channel that
> trades chip and mobility for safety, a super meter spent on specials, and combo cancels expressed
> through ability block/cancel tags — the core of the wider Combat family.

This pack is a copy-and-extend starting point for melee combat games. It is *additive*: it defines
genre-specific Attributes, Tags, Abilities, and Effects on top of the core UGAS spec and never
redefines a core concept. There is no dedicated fighting case study in the core spec, so the pack is
designed from first principles and grounded in the genre's standard frame-data mechanics. It is
deliberately distinct from the Shooter pack: melee instead of projectiles, frame phases instead of
ammo, a guard meter and a stagger meter instead of reloads and falloff.

## What's in this pack

| File | Purpose |
|------|---------|
| `spec.adoc` | Additional Combat specification — extends, never replaces, the core spec |
| `entities/attribute_set.yaml` | `FighterCombatSet`: health, poise/stagger and guard meters, super gauge, frame-data stats |
| `entities/tag_registry.yaml` | Combat tags: frame-data + stagger states, move phases, ability types, hitzones, teams |
| `entities/effect_melee_damage.yaml` | `GE_MeleeDamage`: hit resolution (damage, poise, guard, super) via a custom Execution |
| `entities/effect_hitstun.yaml` | `GE_Hitstun`: clean-hit recovery state that blocks all actions |
| `entities/effect_blockstun.yaml` | `GE_Blockstun`: blocked-hit recovery state that blocks all actions |
| `entities/effect_blocking.yaml` | `GE_Blocking`: Block-channel damage reduction + slower movement while guarding |
| `entities/effect_stagger.yaml` | `GE_Stagger`: poise-break punish window, applied by the engine Poise==0 threshold |
| `entities/ability_light_attack.yaml` | `GA_LightAttack`: fast combo starter; cancellable into a heavy |
| `entities/ability_heavy_attack.yaml` | `GA_HeavyAttack`: slow heavy blow that cancels light-attack recovery |
| `entities/ability_block.yaml` | `GA_Block`: hold to guard (Block channel), blockstun instead of hitstun on contact |
| `entities/ability_special.yaml` | `GA_Special`: spend a full super bar; super-freeze locks out the opponent |
| `entities/input_actions.yaml` | Brawl input actions: light, heavy, block, special, move |
| `entities/input_action_set_brawl.yaml` | `Brawl`: the in-match input context with combo-friendly buffering |
| `entities/input_mapping_brawl_gamepad.yaml` | Gamepad bindings: two attacks, special, hold-block, stick movement |
| `entities/input_modifiers.yaml` | Reusable input modifiers (stick dead zone, radial scaling, trigger threshold) |
| `entities/gameplay_controller.yaml` | Worked example: a fighter mid-block that just ate a heavy hit |

## How to use

1. Read `spec.adoc` for the genre-specific design (especially the melee exchange — frame-data
   states, the cancel tags, the Block damage channel, and the poise → stagger threshold).
2. Copy the entity files in `entities/` into your project and adapt them — tune the fighter base
   values in `attribute_set.yaml`, add moves as new Abilities + `GE_MeleeDamage` payloads, add
   defensive layers in their own `Channel`, or wire the one `ExecCalc_MeleeResolution` hook in your
   engine.
3. They validate against the core `schemas/*.yaml`, so AI agents (e.g. the `ugas-schema-author`
   skill) can load and extend them directly.
4. Run `python scripts/validate_schema_examples.py` after changes.

## Published spec

<!-- Link to the built HTML once published, e.g. v<version>/genres/combat/index.html -->
