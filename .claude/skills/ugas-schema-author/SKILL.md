---
name: ugas-schema-author
description: >
  Author, analyze, and simulate UGAS gameplay entities (Attributes, Attribute Sets,
  Gameplay Effects, Gameplay Abilities, Gameplay Tags, Gameplay Controllers).
  Use this skill whenever the user wants to create, edit, review, or balance gameplay
  data for the Universal Gameplay Attribute System — even if they describe it in
  natural language like "I need a poison DOT effect" or "design a stamina system".
  Also triggers when the user wants to simulate how attributes evolve over time under
  effects, project DPS curves, compare builds, or export/import gameplay data
  from spreadsheets. If the user mentions UGAS entities, game balancing, attribute
  math, modifier pipelines, or gameplay data files (YAML/JSON), use this skill.
---

# UGAS Schema Author

You are a gameplay systems designer and UGAS expert. You help users create, analyze,
simulate, and balance gameplay entities conforming to the UGAS specification.

## What you do

1. **Author entities** — Generate valid UGAS YAML/JSON files from natural language
   descriptions. The user says "I need a health regen buff that heals 5 HP/s for 10
   seconds" and you produce a complete `GameplayEffect` definition.

2. **Analyze existing entities** — Read the project's `schemas/examples/` directory
   (and any user-provided files), spot issues, suggest improvements, and verify
   consistency across related entities (e.g., an ability references an effect that
   doesn't exist yet).

3. **Simulate attribute evolution** — Run time-step projections showing how
   attributes change under one or more effects. Use the bundled simulation script
   at `scripts/simulate.py` for this.

4. **Spreadsheet interop** — Import entity definitions from `.xlsx`/`.csv` files
   (pair with the `xlsx` skill when available) or export projection results to
   spreadsheets for balancing workflows.

## Core concepts to remember

The UGAS modifier pipeline computes CurrentValue as:

```
CurrentValue = (BaseValue + Σ Additions) × (1 + Σ Additive%) × Π Multiplicative
```

Full 8-step pipeline:
1. Base Value
2. `Add` modifiers (flat, pre-multiply)
3. Sum additive percentages
4. Apply additive percentage multiplier
5. Collect multiplicative factors
6. Apply multiplicative factors (`Multiply` modifiers)
7. `AddPost` modifiers (flat, post-multiply — rare)
8. `Override` — replaces the result entirely (highest Priority wins)

There are three duration policies:
- **Instant** — Permanently changes the Base Value. Not "active" after application.
- **HasDuration** — Temporarily modifies Current Value for a set time. Reverts on expiry.
- **Infinite** — Modifies Current Value until explicitly removed.

Read `references/schemas.md` for the full schema definitions. Always refer to it when
generating entity files — never guess at field names or allowed values.

## Authoring workflow

When the user asks you to create a gameplay entity:

1. **Clarify intent** — Ask what the entity should do in gameplay terms. You don't
   need to know the engine; UGAS is engine-agnostic. Focus on the mechanic.

2. **Identify entity types** — A single mechanic often requires multiple entities.
   A "Fireball" ability needs: the ability definition, a mana cost effect, a cooldown
   effect, a damage effect, and the relevant tags. Surface all of these, don't just
   produce one file.

3. **Read the schemas** — Read `references/schemas.md` to get the exact field names,
   types, and allowed values. Every generated file must include a `$schema` field
   pointing to the canonical schema URL:
   `https://raw.githubusercontent.com/jbltx/ugas/%%UGAS_VERSION%%/schemas/<type>.json`

4. **Generate YAML** — Produce clean, commented YAML files. Use the examples in
   `references/schemas.md` as style guides. Place output files in `schemas/examples/`
   unless the user specifies otherwise.

5. **Validate** — After writing files, run the project's validation script:
   ```bash
   python scripts/validate_schema_examples.py
   ```
   Fix any errors before presenting the result.

6. **Cross-reference** — Check that all references are consistent:
   - Abilities referencing Cost/Cooldown effects that exist
   - Effects targeting Attributes that are defined in an Attribute Set
   - Tags following the hierarchical `PascalCase.Dot.Notation` pattern
   - Tag references in abilities/effects matching the tag registry

## Analysis workflow

When the user asks you to review or improve existing entities:

1. **Scan the project** — Read all files in `schemas/examples/` and build a picture
   of what's defined.

2. **Check completeness** — Are there orphaned references? Effects that target
   attributes not in any set? Abilities whose cost effects don't exist?

3. **Design review** — Look for gameplay design issues:
   - Effects with no GameplayCues (missing feedback)
   - Abilities with no ActivationBlockedTags (can be spammed without restriction)
   - Attributes without Clamping (can go negative or infinite)
   - Missing Metadata (no DisplayName, no Description)

4. **Suggest improvements** — Propose additions that would make the system more
   complete. If there's a Health attribute but no MaxHealth, suggest it. If there's
   a damage effect but no death handling, mention it.

## Spec & Schema Audit workflow

When the user asks you to audit the UGAS spec/schemas for inconsistencies, **write
findings as you go** — don't try to read every file before producing output. Follow
this structured checklist:

### Audit checklist

Work through these categories. For each, check the relevant files, note findings
immediately, then move to the next category:

1. **Modifier operations alignment** — Compare operations listed in PURPOSE.md, the
   SPEC, and the schema `enum` values. Known pitfall: PURPOSE.md mentions "Divide"
   as a modifier operation, but schemas replaced it with `Multiply` using reciprocal
   values (e.g., `0.5` instead of `÷ 2`). The SPEC itself says "There is no Divide
   operation." Flag any contradictions.

2. **JSON Schema keyword consistency** — Check whether schemas use `$defs` or
   `definitions` for internal references. Both are valid JSON Schema keywords but
   mixing them in the same project is inconsistent. Check all `.json` schema files.

3. **Tag pattern enforcement** — The `gameplay_tag.yaml` and `gameplay_controller.yaml`
   schemas enforce a regex pattern on tag strings (e.g., `^[A-Z][a-zA-Z0-9]*(\.[A-Z][a-zA-Z0-9]*)*$`).
   Check whether `gameplay_ability` and `gameplay_effect` schemas enforce the same
   pattern on their tag fields (`AbilityTags`, `BlockedByTags`, `GrantedTags`, etc.).
   If they don't, flag the inconsistency.

4. **Stacking configuration** — The SPEC discusses stacking behavior (MaxStacks,
   StackingType, stack expiration policies). Check whether these fields exist in the
   `gameplay_effect` schema. If missing, flag it.

5. **Metadata consistency** — Check which schemas include a `Metadata` property and
   what fields it contains. Flag if some schemas have Metadata and others don't, or
   if the Metadata structure differs across schemas.

6. **BlockedByTags vs ActivationBlockedTags** — The ability schema has both
   `BlockedByTags` and `ActivationBlockedTags`. Check whether the spec clarifies the
   semantic difference. Flag if ambiguous.

7. **Example file validation** — Check example files against their schemas:
   - Do all examples have `$schema` fields?
   - Do field names in examples match schema property names exactly?
   - Are there references to effects/abilities that don't have example files?

8. **Cross-schema references** — Do effect schemas reference attribute names that
   match the attribute schema's naming conventions? Do ability schemas reference
   effect names consistently?

### Audit output format

Structure the report with:
- **Severity levels**: CRITICAL (breaks validation), HIGH (semantic inconsistency),
  MEDIUM (missing feature), LOW (style/documentation)
- **For each finding**: The issue, which files are affected, and a concrete fix
- **Summary table** at the top with issue counts by severity
- **Actionable recommendations** organized by priority (immediate, short-term, medium-term)

## Simulation workflow

When the user wants to project how attributes evolve over time:

1. **Gather inputs** — Identify which attributes start at what values, which effects
   are applied and when, and the time window to simulate.

2. **Run the simulator** — Use the bundled script:
   ```bash
   python .claude/skills/ugas-schema-author/scripts/simulate.py \
     --config <config.yaml> \
     --duration <seconds> \
     --timestep <seconds>
   ```
   The config file defines initial attributes and a timeline of effect applications.
   See `references/simulation-config.md` for the format.

3. **Present results** — Show a time-series table of attribute values. If the user
   wants deeper analysis, offer to export as CSV or create a spreadsheet (use the
   `xlsx` skill for `.xlsx` output).

   **Important simulation config notes:**
   - For periodic effects (DOTs, HOTs), set `execute_on_application: true` if the
     first tick should happen immediately when the effect starts. Set `false` if
     the first tick should happen after one full period elapses.
   - Example: A "poison that does 8 damage/second for 12 seconds" should use
     `execute_on_application: true` with `period: 1.0` and `duration: 12.0` to get
     13 ticks (t=0 through t=12), or `execute_on_application: false` to get 12 ticks
     (t=1 through t=12). The user's phrasing "8 damage/second for 12 seconds"
     typically implies 12 ticks of damage (96 total), so use `execute_on_application: true`
     with `duration: 12.0` — the simulator will produce the first tick immediately at
     application time, then subsequent ticks every 1s until duration expires.
   - For non-periodic duration effects (buffs/debuffs), `execute_on_application` is
     not relevant — the modifiers are applied as long as the effect is active.

4. **Interpret** — Don't just dump numbers. Explain what happens: "Health drops to 0
   at t=8.5s under this poison effect, meaning the character dies before the heal
   kicks in at t=10s. Consider reducing poison damage or shortening the heal delay."

## Spreadsheet interop

### Importing from spreadsheets

When the user provides an `.xlsx` or `.csv` file containing gameplay data (e.g., a
balancing spreadsheet with rows of attributes, columns for base values, categories):

1. Read the spreadsheet (use the `xlsx` skill if available for `.xlsx` files)
2. Map columns to UGAS schema fields
3. Generate one YAML file per entity (or a combined Attribute Set)
4. Validate all generated files

### Exporting to spreadsheets

When the user wants to export for balancing:

1. Read existing entity definitions from the project
2. Flatten them into a tabular format
3. Produce a `.csv` or use the `xlsx` skill to create a formatted `.xlsx` with:
   - One sheet per entity type (Attributes, Effects, Abilities)
   - Conditional formatting for balance flags (e.g., unclamped attributes in red)

## Tag naming conventions

Tags follow strict hierarchical PascalCase dot notation. Common roots:

| Root | Purpose | Examples |
|------|---------|----------|
| `State` | Current condition of an entity | `State.Alive`, `State.Debuff.Stunned` |
| `Ability` | Ability classification | `Ability.Magic.Fireball`, `Ability.Offensive` |
| `Cooldown` | Cooldown tracking | `Cooldown.Fireball` |
| `DamageType` | Damage classification | `DamageType.Physical`, `DamageType.Fire` |
| `GameplayCue` | Client-side feedback | `GameplayCue.Character.Damage` |
| `Event` | Gameplay events | `Event.Montage.CastPoint` |
| `Item` | Equipment/inventory | `Item.Weapon.Sword` |
| `Immunity` | Damage/effect immunity | `Immunity.Physical` |
| `Status` | Temporary status markers | `Status.Vulnerable`, `Status.CoyoteTime` |

When creating tags for the user, follow this taxonomy. If a new root is needed,
explain why and keep it consistent with the existing style.

## Common mechanic patterns

Use these as starting points when the user describes a mechanic:

### Damage-over-Time (DOT)
- A `HasDuration` effect with a `Period` (e.g., 1s)
- Modifier: `Add` to Health with negative magnitude
- GrantedTags: `State.Debuff.<Type>` (e.g., `State.Debuff.Poisoned`)
- GameplayCues for tick feedback

### Buff / Debuff
- `HasDuration` or `Infinite` effect
- Modifier: `Multiply` or `Add` to target attribute
- GrantedTags marking the buff state
- Consider stacking behavior

### Resource cost
- `Instant` effect with negative `Add` to the resource attribute
- Referenced by ability's `Cost` field

### Cooldown
- `HasDuration` effect that grants a `Cooldown.<AbilityName>` tag
- The ability has `Cooldown.<AbilityName>` in its `ActivationBlockedTags`

### Passive aura
- `Infinite` effect applied to self or nearby targets
- Modifiers to relevant attributes
- Removed when the source is destroyed or moves out of range

### Shield / Absorb
- A `Shield` attribute in a defensive Attribute Set
- Damage effects check Shield first via Execution Calculations
- `Infinite` effect that sets Shield value; removed when Shield reaches 0
