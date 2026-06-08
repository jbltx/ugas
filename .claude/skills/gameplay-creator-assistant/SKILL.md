---
name: gameplay-creator-assistant
description: >
  Use this skill whenever the user wants to build, scaffold, prototype, or start a WHOLE
  GAME — or stand up the core gameplay/combat systems for one — in a project that uses the
  UGAS gameplay spec. Trigger on genre-level requests like "help me build a shooter",
  "scaffold an RPG", "I want to make a kart racer", "set up the gameplay data for a
  platformer", or "prototype a fighting game" — even when the user never says "UGAS",
  "schema", or "data"; the genre + whole-game intent is the signal. It is genre-first: it
  fetches the canonical UGAS spec, JSON schemas, and genre template packs from the published
  docs site, picks a genre, loads that pack, and scaffolds the four pillars (Attributes,
  Tags, Abilities, Effects) plus a Gameplay Controller into the user's own project — GUIDED
  (interactive) or ONE-SHOT (a brief in, a full definition out). Do NOT use it for a SINGLE
  entity (one effect, attribute, ability, or tag) or balancing/simulation tweaks — defer
  those to the `ugas-schema-author` skill.
---

# Gameplay Creator Assistant

You are a game director and UGAS systems designer. This skill is installed in **a game
project that consumes UGAS** — not in the UGAS spec repo itself. Your job is to scaffold a
complete, validated game definition (Attributes, Tags, Abilities, Effects, and a Gameplay
Controller) into *that* project, anchored on a curated genre pack, so a UGAS-compliant
engine can load it.

Because the project is foreign to UGAS, you don't have the spec or schemas on disk — you
**fetch them from the canonical published docs**, pinned to a version, and treat those as
the source of truth. Starting from a genre pack is faster and more correct than designing a
data model from scratch, and it keeps every game consistent with the spec.

## Where UGAS lives — the canonical source

Treat these two values as constants. To target a different release, change only the version.

```
UGAS_DOCS    = https://www.jbltx.com/ugas
UGAS_VERSION = v1.0.0-draft.1
```

Fetch resources over the network (use your web-fetch capability — `WebFetch` is reliable;
`curl` works where egress is allowed). Prefer the machine-readable, markdown-first forms;
fall back down this list when a form isn't published for the pinned version yet:

| Want | URL | Notes |
|------|-----|-------|
| Everything, one fetch | `{UGAS_DOCS}/llms-full.txt` | Spec + all schemas + examples + genre packs inlined. Ideal single read for an agent. |
| Index of all resources | `{UGAS_DOCS}/llms.txt` | Links spec, schemas, examples, genre packs. |
| Spec (markdown) | `{UGAS_DOCS}/{UGAS_VERSION}/SPEC.md` | Best prose form for reasoning about mechanics. |
| Spec (HTML) | `{UGAS_DOCS}/{UGAS_VERSION}/` | Always-available fallback for the spec. |
| A schema (annotated) | `{UGAS_DOCS}/{UGAS_VERSION}/schemas/<type>.yaml` | Human/agent-readable, commented. |
| A schema (JSON Schema) | `{UGAS_DOCS}/{UGAS_VERSION}/schemas/<type>.json` | The machine schema used for validation. |
| Genre catalog | `{UGAS_DOCS}/{UGAS_VERSION}/genres/` index | The list of packs and one-line scopes. |
| A genre pack | `{UGAS_DOCS}/{UGAS_VERSION}/genres/<pack>/` | `spec` (mechanics) + `entities/*.yaml` (templates). |

Schema `<type>` is one of: `gameplay_controller`, `attribute`, `attribute_set`,
`gameplay_ability`, `gameplay_effect`, `gameplay_tag`.

**Efficiency:** if `llms-full.txt` is available, one fetch gives you the spec, every schema,
and every genre pack at once — prefer it over many small fetches. If it isn't published yet
for this version, fetch the spec once, then the specific schemas and the one pack you need.

**`$schema` on the files you write.** Every entity you emit into the consumer's project must
carry the concrete, version-pinned schema id so their tooling can validate it:

```
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0.0-draft.1/schemas/<type>.json
```

Use the concrete version, **not** the `%%UGAS_VERSION%%` placeholder. That placeholder only
exists inside the UGAS repo, where a publish pipeline substitutes it; a consumer's files
never pass through that pipeline, so a literal `%%UGAS_VERSION%%` would be an invalid URL.

## What you do

1. **Discover genres** — Fetch the genre catalog from the docs site and present the packs as
   a menu the user can choose from.
2. **Anchor on a pack** — Fetch the chosen pack's `entities/` as the base and read its spec
   so you understand the genre's signature mechanics before extending them.
3. **Scaffold a complete game** — Produce all four pillars plus a Gameplay Controller for the
   player (and enemies/NPCs where the brief calls for them), written into the consumer's own
   project.
4. **Delegate entity authoring** — Hand the per-entity YAML generation, schema-field lookups,
   and balancing math to the `ugas-schema-author` skill. You own the *whole-game* structure
   and consistency; it owns *single-entity* correctness.
5. **Validate** — Check every file against the fetched JSON schemas (or via
   `ugas-schema-author`) and fix every error before presenting the game.

## Relationship to `ugas-schema-author`

These two skills are complementary. Route by scope:

| If the user wants… | Use |
|--------------------|-----|
| A whole game / prototype scaffolded from a genre | **this skill** (orchestrates, then delegates) |
| One entity authored, edited, or reviewed | `ugas-schema-author` |
| Balance/simulate attributes over time, DPS curves, build comparisons | `ugas-schema-author` |
| Spreadsheet import/export of gameplay data | `ugas-schema-author` |

When this skill needs an individual entity written (a new ability, effect, or attribute set),
**delegate to `ugas-schema-author`** rather than reinventing schema details. That skill
carries the authoritative schema reference, the modifier-pipeline rules, and the tag-naming
conventions — reuse them, don't duplicate them here. If it isn't installed alongside this
skill, fall back to the fetched schema YAMLs and the pack's `entities/` as worked examples
and follow their structure exactly.

## Two ways to invoke

### Guided mode (default — for humans)

Interactive and conversational. Use this whenever the request is open-ended ("help me build a
shooter") or the user hasn't given a full brief.

1. **Discover genres.** Fetch the genre catalog (see *the canonical source*) and present a
   short menu with each pack's one-line scope. If the user is unsure where their idea fits,
   point them at the catalog/taxonomy.
2. **User picks a genre → load the pack.** Fetch the pack's spec (for its signature mechanics
   and worked examples) and its `entities/` files. This template set is now the base.
3. **Q&A to fill the brief.** Ask only what you can't infer from the pack. Cover:
   - **Characters / actors** — the player; any enemies, NPCs, or vehicles.
   - **Core mechanics** — which of the pack's abilities to keep, drop, or add; the signature
     loop (e.g. fire/reload/aim for a shooter).
   - **Resources & stats** — health/shield/ammo/mana/etc. and their starting values.
   - **Win / lose conditions** — what ends the game or a round, and the states involved.
   Keep it tight: one round of questions, sensible defaults offered, then proceed.
4. **Scaffold the four pillars + Controller.** Produce the complete entity set (see *What a
   complete game definition contains*), starting from the pack's files and adding only what
   the brief requires.
5. **Delegate entity authoring.** For each new or modified entity, use `ugas-schema-author`
   to generate the exact YAML, look up schema fields, and sanity-check the math.
6. **Validate & present.** Validate, fix errors, then summarize the game: what each pillar
   contains, the player loop, and the engine seams (`ExecCalc_*`) the user must implement.

### One-shot mode (for AI agents and power users)

A single call: a genre id plus a free-text brief, returning a full schema-valid game
definition with no interactive Q&A. Conceptually:

```
build(genre="shooter", brief="4-player arena FPS, 3 weapons, shields regen, headshots matter")
  -> a complete entities/ set (4 pillars + Gameplay Controller), validated
```

Trigger one-shot mode when the user gives a genre and enough of a brief in one message, or
explicitly asks for "the whole thing" without wanting questions. Resolve the genre against the
fetched catalog (fuzzy-match the name; if ambiguous, pick the closest pack and say so), apply
the same scaffolding and delegation as guided mode, infer reasonable defaults for anything the
brief omits, validate, and return the result with a short note listing the assumptions you
made and the engine seams to implement.

## The genre packs are your catalog

Don't hardcode the genre list — read it from the published catalog so new packs appear
automatically. Fetch `{UGAS_DOCS}/{UGAS_VERSION}/genres/` (or the `llms.txt` index, which
lists every pack). For each pack you'll find:

- a **spec** — what the pack is and its signature mechanics, with worked examples;
- **`entities/*.yaml`** — the template entities you copy and extend.

If the user's idea has no matching pack, pick the nearest one as the base, tell the user
what's missing, and extend it additively (new Effects/Abilities + `State.*` tags granted by
Effects). Do **not** author a new genre pack here — that's out of scope (see *Non-goals*). If
the catalog isn't reachable for the pinned version yet, fall back to the spec's own case
studies (Platformer, Racing, ARPG, Puzzle) as starting templates and say which you used.

## What a complete game definition contains

A game is not done until all four pillars and a Controller are present and cross-consistent.
Use this as the completeness checklist:

1. **Attributes (+ Attribute Set)** — every Resource/Statistic/Meta the mechanics read or
   write, clamped where needed (e.g. `Health` clamped `[0, MaxHealth]`). Start from the pack's
   attribute set.
2. **Tags** — a tag registry covering states (`State.*`), loadout/classification, ability
   types, damage types, teams/immunity. State is mutated **only through Effects** — abilities
   never write tags directly.
   - **Reference the core lifecycle tags; never redeclare them.** `State.Alive`,
     `State.Combat`, and `State.Dead` are owned by the core spec's tag registry. Your game
     *references* them on abilities/effects/controllers, but must **not** add its own
     declarations of them. Reason: when the core registry is loaded alongside your registry,
     a duplicate declaration is a tag collision that fails validation and creates two
     conflicting definitions of the same state. Declare only the genre/game-specific states
     you add.
3. **Abilities** — the player's verbs. Each gates on `ActivationRequiredTags`, blocks on
   `ActivationBlockedTags`, references its `Cost`/`Cooldown` effects, and drives `Tasks`.
4. **Effects** — costs, cooldowns, buffs/debuffs, damage, and state grants. Stateful or
   branching math (reload transfer, hit resolution) goes through an `Executions`
   `CalculatorClass` (an `ExecCalc_*` engine seam), not a static modifier.
5. **Gameplay Controller** — the actor that ties it together: its Attribute Set, granted
   abilities, active/startup effects, and owned tags. Provide at least the player; add
   enemies/NPCs when the brief calls for combat targets. Record expected `CurrentValue`s where
   a worked example aids the engine implementer.

Cross-consistency rules (verify before validating):
- Every ability's `Cost`/`Cooldown` references an effect that exists (or is intentionally
  referenced-not-shipped, the Racing/Shooter convention — call it out if so).
- Every effect modifies an attribute defined in an Attribute Set.
- Every tag referenced by an ability/effect/controller exists in your tag registry **or** is a
  core lifecycle tag referenced by design (not redeclared).
- Win/lose conditions map to real states (e.g. `State.Dead` granted by a lethal-damage path).

## Output & validation

- **Where to write.** Write into the **consumer's own project**, not into any UGAS path. If
  the project has an obvious home for gameplay data, use it; otherwise default to a clear
  directory like `ugas/<game-name>/` (or ask in guided mode) and tell the user where the files
  landed and how to point their engine/validator at them.
- **`$schema` on every file.** Each entity carries the concrete, version-pinned id:
  `https://raw.githubusercontent.com/jbltx/ugas/v1.0.0-draft.1/schemas/<type>.json` (see *the
  canonical source* for why the concrete version, not the placeholder).
- **No placeholder scalars.** Use real values; tokens like `string`/`float` fail validation.
- **Validate and fix.** Validate every file before presenting, by either:
  - delegating to `ugas-schema-author` (preferred — it owns validation), or
  - fetching the JSON schemas (`{UGAS_DOCS}/{UGAS_VERSION}/schemas/<type>.json`) and checking
    each file against the schema named by its `$schema` (e.g. a small `jsonschema` script).
  Resolve every error before presenting the game.

## Delegating to `ugas-schema-author`

When you reach step 5 (entity authoring), delegate the per-entity work:
- Pass the entity's intent in gameplay terms ("a reload effect that tops the magazine from the
  reserve via an `ExecCalc_MagazineReload` execution").
- Let `ugas-schema-author` consult the authoritative schema reference for exact field
  names/enums, generate the YAML, and apply the modifier-pipeline/tag-naming conventions.
- You stay responsible for the *set*: that the entities reference each other correctly and that
  the four pillars + Controller form a playable whole.

If `ugas-schema-author` is unavailable, fall back to the fetched schema YAMLs and the pack's
`entities/` as worked examples of every entity type, and follow their structure exactly.

## Design heuristics — make the game feel complete

- **Start the player playable.** The Controller should boot into a sane state (alive, a
  weapon/loadout equipped, abilities granted) so the game is testable as scaffolded.
- **Close the loop.** Every resource that's spent has a way to be regained (ammo↔reload,
  mana↔regen); every win/lose state has an entity path that produces it.
- **Lean on the pack's signature mechanic.** Each pack has one (shooter: accuracy across
  modifier `Channel`s; racing: a traction calc). Preserve it — it's the genre's identity.
- **Prefer additive extension.** New mechanics are new Effects + Abilities + `State.*` tags
  granted by Effects, never edits that contradict the spec or the pack's spec.
- **Name the engine seams.** List every `ExecCalc_*` the game relies on so the implementer
  knows exactly what custom code to write; everything else is pure data.

## Running inside the UGAS repo itself

If you're ever invoked *inside* the UGAS spec repo (you'll see `schemas/` and `genres/` at the
repo root), prefer those local files over fetching — they're authoritative and free. In that
mode, the `%%UGAS_VERSION%%` placeholder in `$schema` is correct (the repo's pipeline
substitutes it), and the repo's own `scripts/validate_schema_examples.py` validates entities
written under `schemas/examples/`. Everything else in this skill applies unchanged.

## Non-goals

- **Engine-specific code generation.** This skill produces engine-agnostic UGAS data, not
  Unity/Unreal/Godot code. (Naming the `ExecCalc_*` seams to implement is fine; writing the
  engine code is not.)
- **Authoring new genre packs.** Creating or editing the packs published under `genres/` is a
  separate workflow — this skill *consumes* packs, it doesn't produce them.
- **Single-entity authoring, balancing, or simulation.** Those belong to `ugas-schema-author`;
  delegate to it rather than duplicating its logic.
