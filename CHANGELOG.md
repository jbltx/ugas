# ugas

## 1.0.0-draft.3

### Minor Changes

- dc006b0: [Added] Input layer schemas (`input_action`, `input_action_set`, `input_mapping`, `input_modifier`) formalizing the pipeline from hardware device inputs through modifier processing to semantic actions and tag-driven action sets — with schema examples, genre templates, input entity files for all four genre packs (shooter, action, racing, RPG), an `ActiveActionSets` field on the Gameplay Controller, and a full rewrite of spec section 11 (#52).

## 1.0.0-draft.2

### Minor Changes

- 0ef963c: [Added] Action / Action-Adventure genre pack (`genres/action/`): an additive platformer specification plus a schema-conformant template — `PlatformerMovementSet`, an action tag taxonomy, a tag-driven movement state machine (grounded / in-air / coyote time) with effect-owned transitions, a variable-height `GA_Jump` and `GA_GroundPound`, power-up effects (super mushroom, invincibility star) using the size/speed channels, and a worked "Super" hero controller. Seeds the Platformer case study (§15.1) as a ready-to-extend pack (#32).
- 840a579: [Added] Racing genre pack (`genres/racing/`): an additive Forza-style racing specification plus a schema-conformant template — `VehiclePerformanceSet`, a racing tag taxonomy, a two-channel traction pipeline (Surface / Upgrades) with surface and tuning effects, nitro-boost and drift abilities, an `ExecutionCalculation` traction recompute, and a worked tuned-Sport-car controller. Seeds the Racing case study (§15.2) as a ready-to-extend pack (#37).
- 31b1cdc: [Added] RPG genre pack (`genres/rpg/`): an additive Role-Playing specification plus a schema-conformant template — `RPGCoreAttributes`, an RPG tag taxonomy, damage-bucket effects (MainStat / DamageBonuses channels), basic-attack and Whirlwind abilities, and a worked Diablo-style hero controller. Seeds the ARPG case study (§15.3) as a ready-to-extend pack (#34).
- 42f8589: [Added] Shooter genre pack (`genres/shooter/`): an additive first/third-person shooter specification plus a schema-conformant template — `ShooterCombatSet` (survivability with regenerating shields, weapon-handling feel stats, magazine + reserve ammo economy), a shooter tag taxonomy (weapon loadout, hitzones, teams), a fire/reload/aim gunplay loop with cost-gated and rate-paced firing, two-channel accuracy aggregation (Aim × Attachments), custom Executions for stateful reload and hit resolution (shields, headshot multiplier, range falloff), and a worked aiming-soldier controller. Designed from first principles as a ready-to-extend pack (#33).
- 30618e5: [Added] Genre pack structure: `genres/` directory with a copyable `_template/` skeleton (additional `spec.adoc` + schema-conformant `entities/`) and an authoring/convention guide. Schema validation now scans `genres/`, and the docs workflows build each `genres/<genre>/spec.adoc` to its own page.
- 2298cc1: [Added] Task tick budgeting: `TickInterval` and `Priority` fields on ability task entries, per-frame tick budget mechanism, and profiling hooks (§10.6)

### Patch Changes

- 9c2f065: [Added] `gameplay-creator-assistant` skill — genre-first, whole-game scaffolding for projects that consume UGAS. It fetches the canonical spec, JSON schemas, and genre template packs from the published docs site (version-pinned), loads a chosen pack's template entities as the base, and scaffolds the four pillars plus a Gameplay Controller into the user's own project; runs guided (interactive Q&A) or one-shot (a genre + brief in, a full schema-valid game definition out), delegating per-entity authoring to `ugas-schema-author` (#29). Also documents how users and AI agents consume a pack — the manual copy-and-extend path and the skill-driven path — in both `genres/README.md` and the published `genres/index.adoc` (#28).
- fa90b84: [Added] Genre taxonomy reference (`genres/taxonomy.adoc`): a non-normative, published map of video game genres/subgenres that scopes the genre-pack work and positions the ten prioritized packs within the broader space (#28). The docs workflows now build it to `genres/taxonomy.html`.
- 9a07613: [Added] Genre pack discoverability from the published docs root: a rendered genre-packs landing page (`genres/index.adoc` → `genres/index.html`) linked from the docs README version table, a "Genre Packs (templates)" section in `llms.txt`, and the pack template entities appended to `llms-full.txt` (#28).
- 6612c9a: [Added] LLM discoverability: `llms.txt`, `SPEC.md` (Markdown via Pandoc), and `llms-full.txt` (complete spec + schemas + examples) generated in CI and published alongside HTML docs

## 1.0.0-draft.1

Initial draft release.

- [Added] Universal Gameplay Ability System specification (`SPEC.adoc` and modular `spec/` include tree).
- [Added] JSON and YAML schemas for Attributes, Attribute Sets, Gameplay Effects, Gameplay Abilities, Gameplay Tags, and Gameplay Controllers.
- [Added] Schema examples and Python validation scripts.
