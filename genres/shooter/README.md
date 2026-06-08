# UGAS Genre Pack: Shooter

> First/third-person gunplay: survivability with regenerating shields, weapon-handling "feel"
> stats, an ammo economy (magazine + reserve), aim-down-sights, and hitscan damage with hitzone
> multipliers — the core of the wider shooter family (FPS, TPS, hero shooter, battle royale).

This pack is a copy-and-extend starting point for shooters. It is *additive*: it defines
genre-specific Attributes, Tags, Abilities, and Effects on top of the core UGAS spec and never
redefines a core concept. There is no dedicated case study for shooters in the core spec, so the
pack is designed from first principles and grounded in the genre's standard mechanics.

## What's in this pack

| File | Purpose |
|------|---------|
| `spec.adoc` | Additional Shooter specification — extends, never replaces, the core spec |
| `entities/attribute_set.yaml` | `ShooterCombatSet`: survivability, weapon-handling feel, ammo economy |
| `entities/tag_registry.yaml` | Shooter tags: weapon-handling states, loadout, hitzones, teams |
| `entities/effect_equip_rifle.yaml` | `GE_EquipRifle`: grants the weapon-loadout tags |
| `entities/effect_ads.yaml` | `GE_ADS`: tighter cone + slower movement while aiming (Aim channel) |
| `entities/effect_attachment_barrel.yaml` | `GE_AttachmentBarrel`: cone + range upgrade (Attachments channel) |
| `entities/effect_reloading.yaml` | `GE_Reloading`: in-progress reload state that blocks fire/aim |
| `entities/effect_reload.yaml` | `GE_Reload`: instant magazine transfer via a custom Execution |
| `entities/effect_ballistic_damage.yaml` | `GE_BallisticDamage`: hit resolution (shields, hitzone, falloff) |
| `entities/ability_fire.yaml` | `GA_Fire`: trace + apply damage; costs ammo, paced by a cooldown |
| `entities/ability_reload.yaml` | `GA_Reload`: enter reloading, wait, transfer rounds |
| `entities/ability_aim.yaml` | `GA_Aim`: hold to aim down sights |
| `entities/gameplay_controller.yaml` | Worked example: a soldier aiming a rifle with a barrel attachment |

## How to use

1. Read `spec.adoc` for the genre-specific design (especially the gunplay loop and the two-channel
   accuracy aggregation).
2. Copy the entity files in `entities/` into your project and adapt them — change the rifle base
   values in `attribute_set.yaml`, add new weapon `GE_Equip*` effects, or wire the two `ExecCalc_*`
   hooks (`ExecCalc_MagazineReload`, `ExecCalc_HitResolution`) in your engine.
3. They validate against the core `schemas/*.yaml`, so AI agents (e.g. the `ugas-schema-author`
   skill) can load and extend them directly.
4. Run `python scripts/validate_schema_examples.py` after changes.

## Published spec

<!-- Link to the built HTML once published, e.g. v<version>/genres/shooter/index.html -->
