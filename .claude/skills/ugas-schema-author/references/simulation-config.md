# Simulation Config Format

The simulation script accepts a YAML configuration file that describes the initial
state of attributes and a timeline of effect applications.

`operation` is **required** on every modifier and is matched case-sensitively against
`Add`, `AddPost`, `Multiply`, `Override`; `duration_policy` likewise against `Instant`,
`HasDuration`, `Infinite`. Anything else is rejected at parse time with an error naming
the effect and attribute. The script exits `2` without producing output rather than
silently no-opping the modifier — a dropped modifier would otherwise yield a
plausible-looking but wrong curve.

Also rejected: a missing effect `name`; a modifier targeting an attribute not listed
under `attributes`; a `period` that is zero, negative, or too small to advance the tick
schedule; a `period` on an `Instant` effect; a negative `duration` on `HasDuration` (use
`Infinite` for no expiry); and a non-numeric `period`, `duration`, or `apply_at` — note
that YAML parses `1.0e16` as a *string*, since its float pattern requires a signed
exponent, so write `1.0e+16`.

An attribute whose initial value falls outside its declared bounds is clamped once at
`t = 0`. Bounds that reference another attribute currently resolve against that
attribute's unclamped Current Value; see issue #104.

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
