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
import io
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class Modifier:
    attribute: str
    operation: str  # Add, Multiply, AddPost, Override
    value: float
    # Aggregation channel for Multiply modifiers. None = own implicit singleton channel.
    channel: Optional[str] = None


@dataclass
class ActiveEffect:
    name: str
    duration_policy: str  # Instant, HasDuration, Infinite
    duration: float  # seconds, -1 for Infinite
    period: Optional[float]  # seconds between ticks, None for non-periodic
    execute_on_application: bool
    modifiers: List[Modifier]
    apply_at: float  # when to apply
    # Runtime state
    applied: bool = False
    time_remaining: float = 0.0
    time_since_last_tick: float = 0.0
    first_tick_done: bool = False


@dataclass
class AttributeState:
    base_value: float
    # Active modifiers from duration/infinite effects. Every entry carries the name of
    # the effect that owns it, so expiry removes exactly that effect's contributions
    # regardless of what else was applied or removed in between.
    # (effect_name, magnitude)
    add_modifiers: List[tuple] = field(default_factory=list)
    # (effect_name, channel, signed magnitude); channel None = own singleton channel
    multiply_modifiers: List[tuple] = field(default_factory=list)
    # (effect_name, magnitude)
    add_post_modifiers: List[tuple] = field(default_factory=list)
    # (effect_name, value); the most recently applied entry wins (§5.2 LIFO tie-break)
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


def parse_effects(effect_defs: List[Dict[str, Any]]) -> List[ActiveEffect]:
    effects = []
    for edef in effect_defs:
        modifiers = []
        for mdef in edef.get("modifiers", []):
            modifiers.append(
                Modifier(
                    attribute=mdef["attribute"],
                    operation=mdef.get("operation", "Add"),
                    value=mdef["value"],
                    channel=mdef.get("channel"),
                )
            )
        effects.append(
            ActiveEffect(
                name=edef["name"],
                duration_policy=edef.get("duration_policy", "Instant"),
                duration=edef.get("duration", 0.0),
                period=edef.get("period"),
                execute_on_application=edef.get("execute_on_application", False),
                modifiers=modifiers,
                apply_at=edef.get("apply_at", 0.0),
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
) -> None:
    """Instant effects permanently change the base value."""
    for mod in modifiers:
        if mod.attribute not in attributes:
            continue
        state = attributes[mod.attribute]
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


def apply_periodic_modifiers(
    modifiers: List[Modifier],
    attributes: Dict[str, AttributeState],
) -> None:
    """Apply one periodic execution of a durational effect to the Base Value.

    Spec §5.2: a periodic execution applies only `Add` / `AddPost` / `Override` to
    the Base Value. `Multiply` is deliberately skipped — a periodic Multiply-to-base
    would compound every tick and double-count against the effect's own Current-Value
    contribution.
    """
    base_writes = [m for m in modifiers if m.operation != "Multiply"]
    apply_instant_modifiers(base_writes, attributes)


def add_duration_modifiers(
    effect_name: str,
    modifiers: List[Modifier],
    attributes: Dict[str, AttributeState],
) -> None:
    """Duration/Infinite effects add temporary modifiers to CurrentValue.

    Each entry is tagged with the owning effect's name; removal filters on that
    name, so stacked effects on one attribute can expire in any order.
    """
    for mod in modifiers:
        if mod.attribute not in attributes:
            continue
        state = attributes[mod.attribute]
        if mod.operation == "Add":
            state.add_modifiers.append((effect_name, mod.value))
        elif mod.operation == "Multiply":
            state.multiply_modifiers.append((effect_name, mod.channel, mod.value))
        elif mod.operation == "AddPost":
            state.add_post_modifiers.append((effect_name, mod.value))
        elif mod.operation == "Override":
            state.override_entries.append((effect_name, mod.value))


def remove_duration_modifiers(
    effect_name: str,
    attributes: Dict[str, AttributeState],
) -> None:
    """Remove every modifier owned by an expiring effect.

    Filtering by owner name (rather than by the index recorded at application
    time) keeps this correct when several effects modify the same attribute and
    expire out of order.
    """
    for state in attributes.values():
        state.add_modifiers = [e for e in state.add_modifiers if e[0] != effect_name]
        state.multiply_modifiers = [
            e for e in state.multiply_modifiers if e[0] != effect_name
        ]
        state.add_post_modifiers = [
            e for e in state.add_post_modifiers if e[0] != effect_name
        ]
        state.override_entries = [
            e for e in state.override_entries if e[0] != effect_name
        ]


def apply_clamping(
    attributes: Dict[str, AttributeState],
    clamp_rules: Dict[str, ClampRule],
) -> None:
    """Apply clamping rules to base values."""
    for attr_name, rule in clamp_rules.items():
        if attr_name not in attributes:
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
                    apply_instant_modifiers(effect.modifiers, attributes)
                    apply_clamping(attributes, clamp_rules)
                else:
                    effect.time_remaining = effect.duration
                    effect.time_since_last_tick = 0.0
                    effect.first_tick_done = False
                    active_effects.append(effect)

                    # Non-periodic duration/infinite: add modifiers immediately
                    if effect.period is None:
                        add_duration_modifiers(
                            effect.name, effect.modifiers, attributes
                        )

                    # Periodic with execute_on_application
                    if effect.period is not None and effect.execute_on_application:
                        apply_periodic_modifiers(effect.modifiers, attributes)
                        apply_clamping(attributes, clamp_rules)
                        effect.first_tick_done = True
                        events.append(f"tick:{effect.name}")

        # Process periodic ticks for active effects
        expired = []
        for effect in active_effects:
            if effect.period is not None:
                effect.time_since_last_tick += timestep
                while effect.time_since_last_tick >= effect.period:
                    effect.time_since_last_tick -= effect.period
                    # Each periodic execution writes the Base Value (§5.2: Add/AddPost/
                    # Override only — Multiply is skipped so it cannot compound per tick)
                    apply_periodic_modifiers(effect.modifiers, attributes)
                    apply_clamping(attributes, clamp_rules)
                    events.append(f"tick:{effect.name}")

            # Reduce remaining time
            if effect.duration_policy == "HasDuration":
                effect.time_remaining -= timestep
                if effect.time_remaining <= 0:
                    events.append(f"expire:{effect.name}")
                    remove_duration_modifiers(effect.name, attributes)
                    expired.append(effect)

        for e in expired:
            active_effects.remove(e)

        # Apply clamping
        apply_clamping(attributes, clamp_rules)

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

    results = simulate(config, duration, timestep)

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
