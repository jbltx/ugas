# Simulation Config Format

The simulation script accepts a YAML configuration file that describes the initial
state of attributes and a timeline of effect applications.

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
        value: 1.5          # 50% more armor

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

- **Add**: Flat additive, applied before multiplicative factors
- **Multiply**: Multiplicative factor (use 1.5 for +50%, 0.5 for -50%)
- **Override**: Replaces the computed value entirely
- **AddPost**: Flat additive applied after multiplicative (rare)

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
