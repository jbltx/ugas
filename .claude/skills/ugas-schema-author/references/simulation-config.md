# Simulation Config Format

The simulation script accepts a YAML configuration file that describes the initial
state of attributes and a timeline of effect applications.

`operation` is **required** on every modifier and is matched case-sensitively against
`Add`, `AddPost`, `Multiply`, `Override`; `duration_policy` likewise against `Instant`,
`HasDuration`, `Infinite`. Anything else is rejected at parse time with an error naming
the effect and attribute. The script exits `2` without producing output rather than
silently no-opping the modifier — a dropped modifier would otherwise yield a
plausible-looking but wrong curve.

Also rejected: a missing effect `name`; a modifier that is not a mapping, or is
missing `attribute` or `value`, or whose `value` is not a number or whose `channel` is
not a string; a modifier targeting an attribute not listed under
`attributes`; a `period` that is zero, negative, or too small to advance the tick
schedule; a `period` on an `Instant` effect; a negative `duration` on `HasDuration` (use
`Infinite` for no expiry); and a non-numeric `period`, `duration`, or `apply_at` — note
that YAML parses `1.0e16` as a *string*, since its float pattern requires a signed
exponent, so write `1.0e+16`.

Clamp rules are validated too: a rule keyed on an undeclared attribute, a bound referencing
one, and a circular set of bound references (`A max: B`, `B max: A`, or a self-reference) are
all rejected, the last with the full cycle path. So are malformed shapes — a non-mapping
`clamping` block or rule, a bound that is neither a number nor an attribute name, and
unknown keys inside a rule.

**Unknown keys are rejected at every level** — top-level, inside an effect, inside a
modifier, and inside `simulation`. An unknown key previously meant "take the default", so
`execute_on_aplication:` silently became `false` and the effect stopped executing on
application while the run still reported it applied; `efects:` produced an empty run that
reads as "your design does nothing"; `timestap:` quietly changed the whole x-axis. This is
**breaking** for configs that carried extra keys — annotations must move into YAML comments.

Malformed shapes now produce a message and exit `2` instead of a traceback and exit `1`: an
`effects` block that is not a list, an effect or modifier that is not a mapping, a
non-mapping `attributes` block, a non-string attribute name, a non-numeric initial value
(including a YAML bool, since `yes` would otherwise become `1.0`), and an empty config file
(which loads as `None`).

Note the key conventions here, because two of them differ from the spec:

- Bound keys are lowercase `min`/`max`. The spec's §5.4 *entity* examples use capitalised
  `Min:`/`Max:`; copying that form is an error rather than silently leaving the attribute
  unbounded.
- Every key is lowercase snake_case and the modifier magnitude key is `value`. The full
  `GameplayEffect` schema and the genre packs use PascalCase (`DurationPolicy`, `Attribute`,
  `Magnitude`) plus fields this simplified format does not model (`Priority`, `GrantedTags`,
  `Executions`, …). Copying one in is an error with a hint naming the difference.

An attribute whose initial value falls outside its declared bounds is clamped once at
`t = 0`. A bound that references another attribute resolves against that attribute's
**clamped** Current Value (§5.4), so a dependent attribute can never exceed the bound it
references — if `MaxHealth` is capped at 200 and buffed to 700, `Health` bounded by
`max: MaxHealth` is limited to 200. Two consequences worth knowing:

- Because a Current Value includes active modifiers, a referenced bound is temporary when
  they are. An `Instant` effect writing a Base Value while the bound is temporarily reduced
  is clamped to the reduced bound, and that write is permanent.
- Where a resolved `min` exceeds a resolved `max`, `min` wins, per §5.3's formula.

Bound references may chain to any depth — `A max: B`, `B max: C`, and so on — and several
attributes may reference a shared set. Only cycles are rejected. Deep chains and wide
reference lattices resolve in near-linear time; they previously raised a `RecursionError`
past a few hundred links, or took exponential time.

Timing (`apply_at`, `duration`, `period`) is evaluated on absolute simulation time, so
results do not depend on `--timestep`; a finer timestep only adds resolution.

## Config Schema

```yaml
# Initial attribute values
attributes:
  Health: 100.0
  MaxHealth: 100.0
  Mana: 50.0
  Armor: 20.0

# Clamping rules (optional)
clamping:
  Health:
    min: 0
    max: MaxHealth   # Can reference other attributes
  Mana:
    min: 0

# Effects to simulate
# Each effect follows a simplified version of the UGAS GameplayEffect schema
effects:
  - name: PoisonDOT
    apply_at: 0.0          # Time in seconds when the effect is applied
    duration_policy: HasDuration
    duration: 10.0         # Duration in seconds
    period: 1.0            # Periodic tick interval
    execute_on_application: false
    modifiers:
      - attribute: Health
        operation: Add
        value: -5.0        # Applied each tick

  - name: HealOverTime
    apply_at: 3.0
    duration_policy: HasDuration
    duration: 8.0
    period: 2.0
    execute_on_application: true
    modifiers:
      - attribute: Health
        operation: Add
        value: 10.0

  - name: ArmorBuff
    apply_at: 0.0
    duration_policy: HasDuration
    duration: 15.0
    modifiers:
      - attribute: Armor
        operation: Multiply
        value: 0.5          # signed bonus: +50% more armor
        channel: Buffs      # optional; omit for an isolated singleton channel

  - name: BigHit
    apply_at: 5.0
    duration_policy: Instant
    modifiers:
      - attribute: Health
        operation: Add
        value: -40.0

# Simulation parameters (can also be passed as CLI args)
simulation:
  duration: 20.0     # Total time to simulate in seconds
  timestep: 0.1      # Resolution of the simulation in seconds
```

## Operations

The simulation applies modifiers following the UGAS pipeline:

- **Add**: Flat additive, applied before the multiply steps
- **Multiply**: Signed bonus, aggregated per `Channel` as `(1 + Σ magnitudes)` — use `0.5`
  for +50% and `-0.5` for −50%. Modifiers sharing a channel add their magnitudes; distinct
  channels multiply. A modifier with no channel is its own singleton.

  On an **`Instant`** effect, `Multiply` scales the *Base Value* by `(1 + value)` — the same
  signed-bonus convention, so `0` is the identity and `-0.5` halves the base. Channel
  grouping does **not** apply to a Base-Value write: each Instant `Multiply` scales
  independently, in authored order, so two `+0.5` modifiers in one Instant effect give ×2.25,
  not the ×2.0 the same two produce as duration modifiers sharing a channel.

  On a **periodic** effect, `Multiply` is never written to the base — it would compound every
  tick. It acts as a Current-Value modifier for the effect's lifetime instead (§5.2).
- **AddPost**: Flat additive applied after the multiply steps (rare)
- **Override**: Replaces the computed value entirely

## Output

The script outputs a CSV with columns:

```
time, attribute1, attribute2, ..., events
```

The `events` column logs what happened at each timestep (effect applied, tick fired,
effect expired, etc.).

## Usage

```bash
# Basic simulation
python .claude/skills/ugas-schema-author/scripts/simulate.py \
  --config path/to/config.yaml \
  --duration 20 \
  --timestep 0.1

# Output to CSV
python .claude/skills/ugas-schema-author/scripts/simulate.py \
  --config path/to/config.yaml \
  --output results.csv

# Print table to stdout (default)
python .claude/skills/ugas-schema-author/scripts/simulate.py \
  --config path/to/config.yaml
```
