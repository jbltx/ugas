#!/usr/bin/env python3
"""UGAS Attribute Simulation Engine.

Simulates how attributes evolve over time under gameplay effects,
following the UGAS modifier pipeline (spec §5.3):

  CurrentValue = (BaseValue + Σ Add) × Π_channels (1 + Σ magnitudes) + Σ AddPost
  then apply Override, then clamp.

`Multiply` magnitudes are SIGNED BONUSES (+0.25 = +25%, -0.25 = -25%), not raw
factors. Modifiers sharing a Channel add their magnitudes into one factor;
distinct channels multiply. A modifier with no Channel is its own singleton.

Usage:
  python simulate.py --config config.yaml [--duration 20] [--timestep 0.1] [--output results.csv]
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml

# Schedule timestamps are quantised to the same precision as the simulation clock
# (`t = round(step * timestep, TIME_DP)`). Without this, accumulating a period of
# 0.1 reaches 0.30000000000000004, which compares greater than an `expire_at` of
# 0.3 and silently drops the execution landing exactly on the expiry boundary.
#
# The grid is absolute, so it only discriminates while one ulp stays below 1e-10 —
# i.e. for |t| below 2**20 (ulp(2**20) is already 2.3e-10). At or beyond that,
# `round(x, TIME_DP)` is an identity and the boundary-tick drift returns: an
# effect at `apply_at: 2**20` with period 0.1 and duration 0.3 fires 2 executions
# where the same effect near t=0 fires 3. That is ~12 simulated days, so it is far
# outside any plausible balance simulation, but it is reachable in ~1e6 steps
# rather than being numerically impossible — so it is a documented limit, not a
# guarantee. The tick loop separately refuses to spin when a schedule fails to
# advance at all, which is the failure mode that actually hangs a run.
TIME_DP = 10


def qtime(value: float) -> float:
    """Quantise a schedule timestamp onto the simulation clock's grid."""
    return round(value, TIME_DP)


@dataclass
class Modifier:
    attribute: str
    operation: str  # Add, Multiply, AddPost, Override
    value: float
    # Aggregation channel for Multiply modifiers. None = own implicit singleton channel.
    channel: Optional[str] = None


@dataclass
class ActiveEffect:
    # Unique per config entry. Modifier ownership is keyed on this rather than on
    # `name`, so two effects sharing a name stay independent.
    instance_id: int
    name: str
    duration_policy: str  # Instant, HasDuration, Infinite
    duration: float  # seconds, -1 for Infinite
    period: Optional[float]  # seconds between ticks, None for non-periodic
    execute_on_application: bool
    modifiers: List[Modifier]
    apply_at: float  # when to apply
    # Runtime state. Schedules are absolute simulation times derived from
    # `apply_at`, never running per-step accumulators — so an effect's lifetime
    # and tick cadence do not depend on `--timestep`.
    applied: bool = False
    expire_at: Optional[float] = None  # None for Infinite (never expires)
    next_tick_at: Optional[float] = None  # None for non-periodic


@dataclass
class AttributeState:
    base_value: float
    # Active modifiers from duration/infinite effects. Every entry carries the
    # `instance_id` of the effect that owns it, so expiry removes exactly that
    # effect's contributions regardless of what else was applied or removed in
    # between — and two effects sharing a `name` remain independent.
    # (owner_id, magnitude)
    add_modifiers: List[tuple] = field(default_factory=list)
    # (owner_id, channel, signed magnitude); channel None = own singleton channel
    multiply_modifiers: List[tuple] = field(default_factory=list)
    # (owner_id, magnitude)
    add_post_modifiers: List[tuple] = field(default_factory=list)
    # (owner_id, value); the most recently applied entry wins (§5.3 LIFO tie-break)
    override_entries: List[tuple] = field(default_factory=list)

    @property
    def override_value(self) -> Optional[float]:
        return self.override_entries[-1][1] if self.override_entries else None


@dataclass
class ClampRule:
    min_val: Optional[float | str] = None  # number or attribute reference
    max_val: Optional[float | str] = None


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


VALID_OPERATIONS = ("Add", "AddPost", "Multiply", "Override")
VALID_DURATION_POLICIES = ("Instant", "HasDuration", "Infinite")


class ConfigError(ValueError):
    """Raised when a simulation config is malformed."""


def require_number(value: Any, label: str, effect_name: str) -> float:
    """Coerce a config field to float, rejecting non-numbers loudly.

    YAML readily yields strings and bools where a number was meant — notably
    `1.0e16`, which PyYAML's float pattern rejects (it requires a signed
    exponent) and hands back as a string. Comparing that against a number later
    raises a bare TypeError traceback, so it is caught here instead.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(
            f"effect {effect_name!r}: {label} must be a number, got {value!r}"
        )
    return float(value)


def parse_effects(effect_defs: List[Dict[str, Any]]) -> List[ActiveEffect]:
    """Parse effect definitions, rejecting anything that would silently no-op.

    Operations are matched case-sensitively against the four spec operations and
    are required — silently defaulting or ignoring an unrecognised operation
    would produce a plausible-looking but wrong curve, and §5.2 requires that an
    implementation MUST NOT silently drop any operation.
    """
    effects = []
    for index, edef in enumerate(effect_defs):
        if "name" not in edef:
            raise ConfigError(f"effect #{index}: missing required 'name'")
        name = edef["name"]

        policy = edef.get("duration_policy", "Instant")
        if policy not in VALID_DURATION_POLICIES:
            raise ConfigError(
                f"effect {name!r}: duration_policy {policy!r} is not one of "
                f"{list(VALID_DURATION_POLICIES)}"
            )

        # A non-positive period would never advance the tick schedule, hanging the
        # run; a negative duration would expire the effect before it applied.
        period = edef.get("period")
        if period is not None:
            if policy == "Instant":
                raise ConfigError(
                    f"effect {name!r}: 'period' is meaningless on an Instant effect "
                    f"(use duration_policy HasDuration or Infinite)"
                )
            period = require_number(period, "period", name)
            if period <= 0:
                raise ConfigError(
                    f"effect {name!r}: period must be > 0, got {period!r}"
                )
        duration = require_number(edef.get("duration", 0.0), "duration", name)
        apply_at = require_number(edef.get("apply_at", 0.0), "apply_at", name)
        if policy == "HasDuration" and duration < 0:
            raise ConfigError(
                f"effect {name!r}: duration must be >= 0 for HasDuration, got "
                f"{duration!r} (use duration_policy Infinite for no expiry)"
            )

        modifiers = []
        for mdef in edef.get("modifiers", []):
            if "operation" not in mdef:
                raise ConfigError(
                    f"effect {name!r}: modifier on {mdef.get('attribute')!r} has no "
                    f"'operation'; expected one of {list(VALID_OPERATIONS)}"
                )
            operation = mdef["operation"]
            if operation not in VALID_OPERATIONS:
                raise ConfigError(
                    f"effect {name!r}: operation {operation!r} on "
                    f"{mdef.get('attribute')!r} is not one of "
                    f"{list(VALID_OPERATIONS)} (matching is case-sensitive; there "
                    f"is no Divide — use Multiply with a negative magnitude)"
                )
            for key in ("attribute", "value"):
                if key not in mdef:
                    raise ConfigError(
                        f"effect {name!r}: modifier is missing required {key!r} "
                        f"(got keys {sorted(mdef)})"
                    )
            modifiers.append(
                Modifier(
                    attribute=mdef["attribute"],
                    operation=operation,
                    value=require_number(
                        mdef["value"], f"modifier value on {mdef['attribute']!r}", name
                    ),
                    channel=mdef.get("channel"),
                )
            )

        effects.append(
            ActiveEffect(
                instance_id=index,
                name=edef["name"],
                duration_policy=policy,
                duration=duration,
                period=period,
                execute_on_application=edef.get("execute_on_application", False),
                modifiers=modifiers,
                apply_at=apply_at,
            )
        )
    return effects


def parse_clamping(
    clamp_defs: Dict[str, Any],
) -> Dict[str, ClampRule]:
    rules = {}
    for attr_name, rule in clamp_defs.items():
        min_val = rule.get("min")
        max_val = rule.get("max")
        rules[attr_name] = ClampRule(min_val=min_val, max_val=max_val)
    return rules


def resolve_clamp_value(
    val: Optional[float | str],
    attributes: Dict[str, AttributeState],
) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    # Attribute reference
    if val in attributes:
        return compute_current(attributes[val])
    return None


def compute_current(state: AttributeState) -> float:
    """Apply the UGAS modifier pipeline."""
    # Step 1: Base
    result = state.base_value

    # Step 2: Add modifiers (pre-multiply)
    result += sum(magnitude for _owner, magnitude in state.add_modifiers)

    # Step 3: group Multiply modifiers by Channel. Each channel's effective factor is
    # (1 + Σ magnitudes) — magnitudes are SIGNED BONUSES (+0.25 = +25%, -0.25 = -25%),
    # not raw factors. A modifier with no Channel is its own implicit singleton channel,
    # contributing (1 + magnitude) independently of every other modifier.
    channel_sums: Dict[Any, float] = {}
    for i, (_owner, channel, magnitude) in enumerate(state.multiply_modifiers):
        key = channel if channel is not None else ("<singleton>", i)
        channel_sums[key] = channel_sums.get(key, 0.0) + magnitude

    # Step 4: multiply all channel factors together
    for channel_total in channel_sums.values():
        result *= 1.0 + channel_total

    # Step 5: AddPost
    result += sum(magnitude for _owner, magnitude in state.add_post_modifiers)

    # Step 6: Override
    if state.override_value is not None:
        result = state.override_value

    # Step 7 (clamping) is applied by the caller against the attribute's ClampRule.
    return result


def apply_instant_modifiers(
    modifiers: List[Modifier],
    attributes: Dict[str, AttributeState],
) -> List[str]:
    """Instant effects permanently change the base value.

    Returns the attributes whose Base Value was written, in authored write order
    and without duplicates, so the caller can clamp exactly those. The order is
    deliberate: clamping is order-sensitive when one attribute's bound references
    another, and a set would make results depend on the hash seed and so differ
    between runs of the same config.
    """
    written: List[str] = []
    for mod in modifiers:
        if mod.attribute not in attributes:
            continue
        state = attributes[mod.attribute]
        if mod.attribute not in written:
            written.append(mod.attribute)
        if mod.operation == "Add":
            state.base_value += mod.value
        elif mod.operation == "Multiply":
            # Spec §5.2: an Instant Multiply scales the Base Value by (1 + magnitude),
            # the same signed-bonus convention the Current-Value pipeline uses. Channel
            # grouping does not apply to a Base-Value write; each Instant Multiply scales
            # independently in authored order. Magnitude 0 is therefore the identity.
            state.base_value *= 1.0 + mod.value
        elif mod.operation == "Override":
            state.base_value = mod.value
        elif mod.operation == "AddPost":
            state.base_value += mod.value
    return written


def apply_periodic_modifiers(
    modifiers: List[Modifier],
    attributes: Dict[str, AttributeState],
) -> List[str]:
    """Apply one periodic execution of a durational effect to the Base Value.

    Spec §5.2: a periodic execution applies only `Add` / `AddPost` / `Override` to
    the Base Value. `Multiply` is deliberately skipped here — a periodic
    Multiply-to-base would compound every tick and double-count against the effect's
    own Current-Value contribution. That Current-Value contribution is registered
    separately at application time (see the periodic branch in `run_simulation`), so
    skipping it here drops it from the base write only, not from the pipeline.
    """
    base_writes = [m for m in modifiers if m.operation != "Multiply"]
    return apply_instant_modifiers(base_writes, attributes)


def add_duration_modifiers(
    owner_id: int,
    modifiers: List[Modifier],
    attributes: Dict[str, AttributeState],
) -> None:
    """Duration/Infinite effects add temporary modifiers to CurrentValue.

    Each entry is tagged with the owning effect's `instance_id`; removal filters
    on that id, so stacked effects on one attribute can expire in any order even
    if they share a name.
    """
    for mod in modifiers:
        if mod.attribute not in attributes:
            continue
        state = attributes[mod.attribute]
        if mod.operation == "Add":
            state.add_modifiers.append((owner_id, mod.value))
        elif mod.operation == "Multiply":
            state.multiply_modifiers.append((owner_id, mod.channel, mod.value))
        elif mod.operation == "AddPost":
            state.add_post_modifiers.append((owner_id, mod.value))
        elif mod.operation == "Override":
            state.override_entries.append((owner_id, mod.value))


def remove_duration_modifiers(
    owner_id: int,
    attributes: Dict[str, AttributeState],
) -> None:
    """Remove every modifier owned by an expiring effect instance."""
    for state in attributes.values():
        state.add_modifiers = [e for e in state.add_modifiers if e[0] != owner_id]
        state.multiply_modifiers = [
            e for e in state.multiply_modifiers if e[0] != owner_id
        ]
        state.add_post_modifiers = [
            e for e in state.add_post_modifiers if e[0] != owner_id
        ]
        state.override_entries = [
            e for e in state.override_entries if e[0] != owner_id
        ]


def clamp_base_values(
    attr_names: Iterable[str],
    attributes: Dict[str, AttributeState],
    clamp_rules: Dict[str, ClampRule],
) -> None:
    """Clamp the Base Value of attributes that were just written.

    Only called immediately after a base write (an Instant application or a
    periodic execution), and only for the attributes that write touched. §5.2
    permits Base Values to change only through those paths, so clamping every
    attribute's base on every step would let a *temporary* Current-Value debuff
    on a referenced bound (e.g. `max: MaxHealth`) write through and permanently
    destroy the dependent attribute's base. Clamping of the Current Value is a
    read-time concern — §5.3's formula wraps the result in min/max, and §5.4
    resolves an attribute-reference bound against that attribute's Current Value.
    """
    for attr_name in attr_names:
        rule = clamp_rules.get(attr_name)
        if rule is None or attr_name not in attributes:
            continue
        state = attributes[attr_name]
        min_v = resolve_clamp_value(rule.min_val, attributes)
        max_v = resolve_clamp_value(rule.max_val, attributes)
        if min_v is not None and state.base_value < min_v:
            state.base_value = min_v
        if max_v is not None and state.base_value > max_v:
            state.base_value = max_v


def simulate(
    config: Dict[str, Any],
    duration: float,
    timestep: float,
) -> List[Dict[str, Any]]:
    """Run the simulation and return time-series data."""

    # Initialize attributes
    attr_defs = config.get("attributes", {})
    attributes: Dict[str, AttributeState] = {}
    for name, base_val in attr_defs.items():
        attributes[name] = AttributeState(base_value=float(base_val))

    # Parse clamping
    clamp_rules = parse_clamping(config.get("clamping", {}))

    # Parse effects
    effects = parse_effects(config.get("effects", []))

    # A modifier naming an attribute that does not exist would silently no-op
    # while the run still reported the effect as applied.
    for effect in effects:
        for mod in effect.modifiers:
            if mod.attribute not in attributes:
                raise ConfigError(
                    f"effect {effect.name!r}: modifier targets unknown attribute "
                    f"{mod.attribute!r}; declared attributes are "
                    f"{sorted(attributes)}"
                )

    # Normalise any initial state that starts outside its declared bounds. Done
    # once, before any effect is active, so no temporary Current-Value modifier
    # can leak into a Base Value here (the bug §5.2 forbids).
    clamp_base_values(sorted(attributes), attributes, clamp_rules)

    active_effects: List[ActiveEffect] = []

    attr_names = sorted(attributes.keys())
    results: List[Dict[str, Any]] = []

    total_steps = int(round(duration / timestep))
    for step in range(total_steps + 1):
        t = round(step * timestep, 10)
        events = []

        # Apply effects that should activate at this time
        for effect in effects:
            if not effect.applied and t >= effect.apply_at:
                effect.applied = True
                events.append(f"apply:{effect.name}")

                if effect.duration_policy == "Instant":
                    written = apply_instant_modifiers(effect.modifiers, attributes)
                    clamp_base_values(written, attributes, clamp_rules)
                else:
                    # Schedules are absolute and derived from the authored `apply_at`,
                    # not from the step the effect happened to be noticed on, so they
                    # are independent of `--timestep`. Infinite effects never expire.
                    if effect.duration_policy == "HasDuration":
                        effect.expire_at = qtime(effect.apply_at + effect.duration)
                    active_effects.append(effect)

                    if effect.period is None:
                        # Non-periodic durational: every modifier is a Current-Value
                        # modifier for the effect's lifetime.
                        add_duration_modifiers(
                            effect.instance_id, effect.modifiers, attributes
                        )
                    else:
                        # Periodic durational (§5.2): the effect's `Multiply` modifiers
                        # remain Current-Value modifiers for its whole lifetime, while
                        # Add/AddPost/Override are written to the Base Value on each
                        # execution. Registering the Multiply subset here is what keeps
                        # it from being dropped entirely — expiry removes it by id.
                        add_duration_modifiers(
                            effect.instance_id,
                            [m for m in effect.modifiers if m.operation == "Multiply"],
                            attributes,
                        )

                        # The first execution lands at `apply_at` when the effect
                        # executes on application, otherwise one full period later.
                        effect.next_tick_at = qtime(effect.apply_at + effect.period)
                        if effect.execute_on_application:
                            written = apply_periodic_modifiers(
                                effect.modifiers, attributes
                            )
                            clamp_base_values(written, attributes, clamp_rules)
                            events.append(f"tick:{effect.name}")

        # Process periodic executions, then expiries — so an execution falling
        # exactly on the expiry boundary still runs while the effect is active.
        expired = []
        for effect in active_effects:
            if effect.period is not None and effect.next_tick_at is not None:
                while t >= effect.next_tick_at and (
                    effect.expire_at is None or effect.next_tick_at <= effect.expire_at
                ):
                    # Each periodic execution writes the Base Value (§5.2: Add/AddPost/
                    # Override only — Multiply is skipped so it cannot compound per tick)
                    written = apply_periodic_modifiers(effect.modifiers, attributes)
                    clamp_base_values(written, attributes, clamp_rules)
                    events.append(f"tick:{effect.name}")
                    # A positive period is not sufficient for progress: quantising
                    # onto the TIME_DP grid can round the advance away entirely if
                    # the period is tiny, and at very large `t` the float addition
                    # itself is a no-op. Either way the loop would spin forever, so
                    # fail loudly instead of hanging.
                    advanced = qtime(effect.next_tick_at + effect.period)
                    if advanced <= effect.next_tick_at:
                        raise ConfigError(
                            f"effect {effect.name!r}: period {effect.period!r} does "
                            f"not advance the tick schedule at t="
                            f"{effect.next_tick_at!r} (schedules are quantised to "
                            f"{TIME_DP} decimal places); use a larger period"
                        )
                    effect.next_tick_at = advanced

            if effect.expire_at is not None and t >= effect.expire_at:
                events.append(f"expire:{effect.name}")
                remove_duration_modifiers(effect.instance_id, attributes)
                expired.append(effect)

        for e in expired:
            active_effects.remove(e)

        # Record state
        row: Dict[str, Any] = {"time": round(t, 4)}
        for name in attr_names:
            current = compute_current(attributes[name])
            # Apply clamping to current value display
            if name in clamp_rules:
                min_v = resolve_clamp_value(clamp_rules[name].min_val, attributes)
                max_v = resolve_clamp_value(clamp_rules[name].max_val, attributes)
                if min_v is not None:
                    current = max(current, min_v)
                if max_v is not None:
                    current = min(current, max_v)
            row[name] = round(current, 4)
        row["events"] = "; ".join(events) if events else ""
        results.append(row)

    return results


def format_table(results: List[Dict[str, Any]], attr_names: List[str]) -> str:
    """Format results as a readable ASCII table."""
    headers = ["time"] + attr_names + ["events"]
    col_widths = {h: len(h) for h in headers}

    for row in results:
        for h in headers:
            val = str(row.get(h, ""))
            col_widths[h] = max(col_widths[h], len(val))

    # Header
    lines = []
    header_line = " | ".join(h.rjust(col_widths[h]) for h in headers)
    lines.append(header_line)
    lines.append("-+-".join("-" * col_widths[h] for h in headers))

    # Only show rows where something happens or at regular intervals
    for i, row in enumerate(results):
        events = row.get("events", "")
        time_val = row["time"]
        # Show row if: has events, is first/last, or at 1-second intervals
        show = bool(events) or i == 0 or i == len(results) - 1
        if not show and time_val == int(time_val):
            show = True
        if show:
            values = []
            for h in headers:
                val = row.get(h, "")
                values.append(str(val).rjust(col_widths[h]))
            lines.append(" | ".join(values))

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="UGAS Attribute Simulator")
    parser.add_argument("--config", required=True, help="Path to simulation config YAML")
    parser.add_argument("--duration", type=float, help="Override simulation duration")
    parser.add_argument("--timestep", type=float, help="Override timestep")
    parser.add_argument("--output", help="Output CSV file path (default: print table)")
    args = parser.parse_args()

    config = load_config(Path(args.config))

    sim_config = config.get("simulation", {})
    duration = args.duration or sim_config.get("duration", 20.0)
    timestep = args.timestep or sim_config.get("timestep", 0.1)

    try:
        results = simulate(config, duration, timestep)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    attr_names = sorted(config.get("attributes", {}).keys())

    if args.output:
        output_path = Path(args.output)
        headers = ["time"] + attr_names + ["events"]
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)
        print(f"Results written to {output_path}")
    else:
        print(format_table(results, attr_names))

    return 0


if __name__ == "__main__":
    sys.exit(main())
