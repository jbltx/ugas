# UGAS Genre Packs

The core [UGAS specification](../SPEC.adoc) is deliberately genre-agnostic. A **genre
pack** makes it practical to bootstrap a real game — by humans or AI agents — by bundling
two **additive** artifacts per genre:

1. an **additional spec** that extends (never replaces) the core spec with genre-specific
   Attributes, Tags, Abilities, and Effects; and
2. a **template**: ready-to-use, schema-conformant entity files.

See the [genre taxonomy](taxonomy.adoc) for the full map of genres/subgenres and how the
prioritized packs are positioned within the broader space.

## Layout contract

Each pack is one self-contained directory under `genres/`, named in kebab-case:

```
genres/
  README.md            <- this file (convention + index)
  _template/           <- copyable skeleton pack
  <genre>/
    spec.adoc          <- additional genre spec (extends the core spec)
    entities/
      *.yaml           <- template entities, each $schema-tagged with real values
    README.md          <- what the pack is + how to use it
```

## Rules

- **Additive only.** A genre `spec.adoc` MUST NOT redefine, override, or contradict any
  concept in [`SPEC.adoc`](../SPEC.adoc). It only adds genre-specific definitions and links
  back to core sections.
- **Entities must validate.** Every `.yaml`/`.json` under `genres/` must be a schema
  instance carrying a root `$schema` key that ends in one of the six core schemas
  (e.g. `…/schemas/attribute.json`). Use the version placeholder:
  `$schema: https://raw.githubusercontent.com/jbltx/ugas/%%UGAS_VERSION%%/schemas/<name>.json`.
  Only such entity files may live under `genres/` — `scripts/validate_schema_examples.py`
  validates the whole tree and fails on a missing/unknown `$schema`.
- **No placeholder scalars.** Use real values; tokens like `string` or `float` fail validation.
- **Consistent docs.** Reuse the core AsciiDoc header attributes (see `_template/spec.adoc`).
  Each `spec.adoc` is built to its own `genres/<genre>/index.html` by the docs workflows.

## Authoring a new pack

1. Copy `_template/` to `genres/<your-genre>/`.
2. Rename and fill in `spec.adoc`, the `entities/`, and `README.md`.
3. Run `python scripts/validate_schema_examples.py` — it must pass.

## Consuming a pack

A pack is meant to be a **starting point**, not a fixed library. Both humans and AI agents
consume packs the same two ways:

### Manual: copy and extend

1. Read the pack's `spec.adoc` to understand its Attributes, Tags, Abilities, and Effects
   (and its signature mechanic — e.g. the shooter's accuracy `Channel`s).
2. Copy the pack's `entities/` directory into your project as the base.
3. Keep, rename, or extend the entities. They are schema-conformant and validate against the
   same `schemas/*.json` as the core spec.
4. Extend **additively**: add new mechanics as Effects + Abilities, and new states as
   `State.*` tags **granted by Effects** (never mutate tags directly). Don't contradict the
   core spec or the pack's spec.
5. Implement the engine seams the pack names — its `ExecCalc_*` calculators — in your engine;
   everything else is data.
6. Run `python scripts/validate_schema_examples.py` before committing.

### Skill-driven: let an agent scaffold it

Two complementary skills make a pack agent-consumable:

- **`gameplay-creator-assistant`** — genre-first, **whole-game** scaffolding. It discovers
  the packs here, helps you pick one, loads its `entities/` as the base, and scaffolds the
  four pillars plus a Gameplay Controller into a working project. Runs **guided** (interactive
  Q&A) or **one-shot** (a genre + a brief in, a full game definition out). Best when you're
  starting a new game or prototype.
- **`ugas-schema-author`** — **single-entity** authoring, review, balancing, and simulation.
  Best when you already have a game and want to add or tune one ability/effect/attribute.

The two compose: `gameplay-creator-assistant` owns the whole-game structure and delegates
each entity's YAML to `ugas-schema-author`.

For fully machine consumption, the published site root also exposes `llms.txt` (a
discoverability index) and `llms-full.txt` (the complete context — the spec plus every
schema, example, and genre-pack entity in one file).

## Pack index

| Pack | Status | Spec |
|------|--------|------|
| `_template` | Skeleton (reference only) | [`_template/spec.adoc`](_template/spec.adoc) |
| `rpg` | Role-Playing (RPG) — seeded by the ARPG case study | [`rpg/spec.adoc`](rpg/spec.adoc) |
| `racing` | Racing (Forza-style) — seeded by the Racing case study | [`racing/spec.adoc`](racing/spec.adoc) |
| `action` | Action / Action-Adventure — seeded by the Platformer case study | [`action/spec.adoc`](action/spec.adoc) |
| `shooter` | Shooter (FPS/TPS) — gunplay, ammo economy, hit resolution | [`shooter/spec.adoc`](shooter/spec.adoc) |
| `combat` | Combat (fighting/brawler/hack-and-slash) — frame-data states, poise→stagger, guard channel | [`combat/spec.adoc`](combat/spec.adoc) |
| `strategy` | Strategy (RTS/4X/Tower Defense) — periodic economy, damage×armor matrix, tech upgrades | [`strategy/spec.adoc`](strategy/spec.adoc) |
| `sports` | Sports (sim/arcade) — stamina-driven performance coupling, team momentum | [`sports/spec.adoc`](sports/spec.adoc) |
| `puzzle` | Puzzle (tile-matching) — seeded by the Puzzle case study; combo×chain scoring + move economy | [`puzzle/spec.adoc`](puzzle/spec.adoc) |
| `casual` | Casual (idle/incremental) — multiplicative income channels, passive-income tick, energy gate | [`casual/spec.adoc`](casual/spec.adoc) |
