# UGAS Genre Pack: Sports

> Team and athlete sports: physical and on-ball skill attributes, a stamina reserve that drains
> with effort, and a team momentum meter. Its signature is a *stamina-driven performance coupling* —
> speed and finishing degrade continuously as an athlete tires (an AttributeBased magnitude), while a
> momentum surge multiplies offensive skill — covering the traditional-sim and arcade ends of the
> sports family.

This pack is a copy-and-extend starting point for sports games. It is *additive*: it defines
genre-specific Attributes, Tags, Abilities, and Effects on top of the core UGAS spec and never
redefines a core concept. There is no dedicated case study for sports in the core spec, so the pack
is designed from first principles and grounded in the genre's standard mechanics.

## What's in this pack

| File | Purpose |
|------|---------|
| `spec.adoc` | Additional Sports specification — extends, never replaces, the core spec |
| `entities/attribute_set.yaml` | `AthletePerformanceSet`: physical stats, skill ratings, stamina, momentum, telemetry |
| `entities/tag_registry.yaml` | Sports tags: athlete/team states, affiliation, roles, ability types |
| `entities/effect_fatigue.yaml` | `GE_Fatigue`: AttributeBased `Speed`/`ShotAccuracy` coupling to `Stamina` (the signature) |
| `entities/effect_sprint_drain.yaml` | `GE_SprintDrain`: timed + periodic `Stamina` drain while sprinting |
| `entities/effect_stamina_recover.yaml` | `GE_StaminaRecover`: periodic `Stamina` regen while not sprinting |
| `entities/effect_momentum_boost.yaml` | `GE_MomentumBoost`: `+20%` offensive skill in the `Momentum` channel |
| `entities/effect_injury.yaml` | `GE_Injury`: timed physical debuff with a lowered `MaxStamina` ceiling |
| `entities/effect_shot_attempt.yaml` | `GE_ShotAttempt`: shot resolution via a custom `Execution` |
| `entities/ability_sprint.yaml` | `GA_Sprint`: hold to sprint, draining stamina; blocked while fatigued |
| `entities/ability_pass.yaml` | `GA_Pass`: play the ball to a team-mate; costs stamina |
| `entities/ability_shoot.yaml` | `GA_Shoot`: strike at goal; costs stamina, applies `GE_ShotAttempt` |
| `entities/ability_tackle.yaml` | `GA_Tackle`: challenge a hostile carrier; costs stamina, on cooldown |
| `entities/ability_skill_move.yaml` | `GA_SkillMove`: technical dribble; costs stamina, blocked while fatigued |
| `entities/input_actions.yaml` | Outfield input actions (Move, Look, Sprint, Pass, Shoot, Tackle, SkillMove) |
| `entities/input_action_set_outfield.yaml` | `Outfield`: the open-play action set |
| `entities/input_mapping_outfield_gamepad.yaml` | Console gamepad bindings for the outfield set |
| `entities/input_modifiers.yaml` | Reusable input modifiers (dead zone, radial scaling, trigger threshold) |
| `entities/gameplay_controller.yaml` | Worked example: a fatigued striker on a momentum surge |

## How to use

1. Read `spec.adoc` for the genre-specific design (especially the stamina-driven performance coupling
   and the team-momentum channel).
2. Copy the entity files in `entities/` into your project and adapt them — tune the athlete base
   values in `attribute_set.yaml`, adjust the `Coefficient` on the `GE_Fatigue` modifiers to set how
   steeply performance drops with fatigue, or wire the optional `ExecCalc_ShotResolution` hook in
   your engine.
3. They validate against the core `schemas/*.yaml`, so AI agents (e.g. the `ugas-schema-author`
   skill) can load and extend them directly.
4. Run `python scripts/validate_schema_examples.py` after changes.

## Published spec

<!-- Link to the built HTML once published, e.g. v<version>/genres/sports/index.html -->
