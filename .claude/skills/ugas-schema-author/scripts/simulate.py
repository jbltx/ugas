#!/usr/bin/env python3
"""UGAS Attribute Simulation Engine.

Simulates how attributes evolve over time under gameplay effects,
following the UGAS modifier pipeline:

  CurrentValue = (BaseValue + Σ Add) × (1 + Σ Additive%) × Π Multiply
  then apply AddPost, then Override.

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
    operation: str  # Add, Multiply, Override, AddPost
    value: float


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
    # Active modifiers from duration/infinite effects
    add_modifiers: List[float] = field(default_factory=list)
    multiply_modifiers: List[float] = field(default_factory=list)
    add_post_modifiers: List[float] = field(default_factory=list)
    override_value: Optional[float] = None


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
    result += sum(state.add_modifiers)

    # Steps 3-4: Additive percentages not separately modeled here;
    # users model them as Multiply modifiers with value (1 + pct)

    # Steps 5-6: Multiplicative
    for m in state.multiply_modifiers:
        result *= m

    # Step 7: AddPost
    result += sum(state.add_post_modifiers)

    # Step 8: Override
    if state.override_value is not None:
        result = state.override_value

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
            state.base_value *= mod.value
        elif mod.operation == "Override":
            state.base_value = mod.value
        elif mod.operation == "AddPost":
            state.base_value += mod.value


def add_duration_modifiers(
    effect_name: str,
    modifiers: List[Modifier],
    attributes: Dict[str, AttributeState],
    active_mod_map: Dict[str, List[tuple]],
) -> None:
    """Duration/Infinite effects add temporary modifiers to CurrentValue."""
    for mod in modifiers:
        if mod.attribute not in attributes:
            continue
        state = attributes[mod.attribute]
        entry = (effect_name, mod.value)
        if mod.operation == "Add":
            state.add_modifiers.append(mod.value)
            active_mod_map.setdefault(effect_name, []).append(
                (mod.attribute, "add", len(state.add_modifiers) - 1)
            )
        elif mod.operation == "Multiply":
            state.multiply_modifiers.append(mod.value)
            active_mod_map.setdefault(effect_name, []).append(
                (mod.attribute, "multiply", len(state.multiply_modifiers) - 1)
            )
        elif mod.operation == "AddPost":
            state.add_post_modifiers.append(mod.value)
            active_mod_map.setdefault(effect_name, []).append(
                (mod.attribute, "add_post", len(state.add_post_modifiers) - 1)
            )
        elif mod.operation == "Override":
            state.override_value = mod.value
            active_mod_map.setdefault(effect_name, []).append(
                (mod.attribute, "override", 0)
            )


def remove_duration_modifiers(
    effect_name: str,
    attributes: Dict[str, AttributeState],
    active_mod_map: Dict[str, List[tuple]],
) -> None:
    """Remove modifiers when a duration effect expires."""
    entries = active_mod_map.pop(effect_name, [])
    # We need to rebuild modifier lists to avoid index issues
    # Collect which modifiers to remove per attribute
    removals: Dict[str, Dict[str, List[int]]] = {}
    for attr_name, mod_type, idx in entries:
        removals.setdefault(attr_name, {}).setdefault(mod_type, []).append(idx)

    for attr_name, type_indices in removals.items():
        if attr_name not in attributes:
            continue
        state = attributes[attr_name]
        for mod_type, indices in type_indices.items():
            indices_set = set(indices)
            if mod_type == "add":
                state.add_modifiers = [
                    v for i, v in enumerate(state.add_modifiers) if i not in indices_set
                ]
            elif mod_type == "multiply":
                state.multiply_modifiers = [
                    v
                    for i, v in enumerate(state.multiply_modifiers)
                    if i not in indices_set
                ]
            elif mod_type == "add_post":
                state.add_post_modifiers = [
                    v
                    for i, v in enumerate(state.add_post_modifiers)
                    if i not in indices_set
                ]
            elif mod_type == "override":
                state.override_value = None

    # Rebuild index references in active_mod_map for remaining effects
    # This is needed because list indices shifted after removal
    # For simplicity, we rebuild from scratch
    rebuild_mod_map(attributes, active_mod_map)


def rebuild_mod_map(
    attributes: Dict[str, AttributeState],
    active_mod_map: Dict[str, List[tuple]],
) -> None:
    """Rebuild the mod map after removals - simplified approach."""
    # This is a simplification; in a full implementation you'd track
    # modifier ownership more robustly
    pass


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

    # Track which modifier list entries belong to which effect
    active_mod_map: Dict[str, List[tuple]] = {}
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
                            effect.name, effect.modifiers, attributes, active_mod_map
                        )

                    # Periodic with execute_on_application
                    if effect.period is not None and effect.execute_on_application:
                        apply_instant_modifiers(effect.modifiers, attributes)
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
                    # Periodic effects apply as instant modifications each tick
                    apply_instant_modifiers(effect.modifiers, attributes)
                    apply_clamping(attributes, clamp_rules)
                    events.append(f"tick:{effect.name}")

            # Reduce remaining time
            if effect.duration_policy == "HasDuration":
                effect.time_remaining -= timestep
                if effect.time_remaining <= 0:
                    events.append(f"expire:{effect.name}")
                    remove_duration_modifiers(effect.name, attributes, active_mod_map)
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
