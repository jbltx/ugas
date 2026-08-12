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
import heapq
import math
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
# Quantising is not a proof of exactness, only a normalisation: `round(x, TIME_DP)`
# stops changing anything once one ulp exceeds the grid step (from |t| = 2**19),
# and an `apply_at` carrying full float precision can leave a residue larger than
# the grid at magnitudes as low as a few hundred. So the boundary comparison uses
# `at_or_before` rather than a bare `<=`, which is what actually makes an execution
# landing on the expiry instant reliable.
TIME_DP = 10

# Half a grid step. Two schedule timestamps closer than this are the same instant
# as far as the clock can express.
TIME_EPS = 0.5 * 10 ** -TIME_DP


def qtime(value: float) -> float:
    """Quantise a schedule timestamp onto the simulation clock's grid."""
    return round(value, TIME_DP)


def at_or_before(a: float, b: float) -> bool:
    """Is schedule time `a` at or before `b`, treating near-equal as equal?

    Uses a relative tolerance so it holds at large `t`, where one ulp is itself
    wider than the quantisation grid, plus an absolute floor for times near zero.
    """
    return a <= b or math.isclose(a, b, rel_tol=1e-12, abs_tol=TIME_EPS)


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

# Closed key sets. Every mapping this script reads keys out of gets one, and this
# script validates nothing it does not read — an unknown key would otherwise mean
# "take the default", which is how a single typo turns into a plausible but wrong
# curve (`execute_on_aplication:` silently becomes False and the effect stops
# executing on application while the run still reports it applied).
TOP_LEVEL_KEYS = ("attributes", "clamping", "effects", "simulation")
SIMULATION_KEYS = ("duration", "timestep")
EFFECT_KEYS = ("name", "duration_policy", "duration", "period",
               "execute_on_application", "apply_at", "modifiers")
MODIFIER_KEYS = ("attribute", "operation", "value", "channel")

# Fields of the full GameplayEffect schema that this simplified format does not
# model, in canonical form. A config adapted from a genre-pack entity file carries
# them wholesale, so the error should say they are unsupported rather than typos.
SPEC_ONLY_EFFECT_KEYS = frozenset({
    "executionpolicy", "priority", "executions", "grantedtags",
    "applicationrequiredtags", "grantedabilities", "gameplaycues", "area",
    "$schema",
})


class ConfigError(ValueError):
    """Raised when a simulation config is malformed."""


def canon(key: Any) -> Optional[str]:
    """Case- and underscore-insensitive form of a key, for hint matching only.

    `schemas/gameplay_effect.json` and the genre packs write keys in PascalCase
    (`DurationPolicy`, `Attribute`, `Magnitude`), so a config copied from either
    arrives with every key unknown; canonicalising both sides lets the error say
    why. Stripping underscores is what makes it work — `"DurationPolicy".lower()`
    is not `"duration_policy"`. Non-string keys canonicalise to None, because
    `.lower()` on a raw YAML key crashes on `1:` or a bare `no:`.
    """
    return key.lower().replace("_", "") if isinstance(key, str) else None


def unknown_keys(mapping: Dict[Any, Any], allowed: Iterable[str]) -> tuple:
    """Unknown keys of `mapping`, as (list, display string).

    Sorts by `repr` and joins the reprs directly. Both matter: YAML keys are not
    necessarily strings — `1:` is an int and YAML 1.1 reads a bare `no:` as False —
    so `sorted` on the raw keys raises TypeError on mixed types; and formatting a
    list of repr-strings would repr each one a second time, printing an int key 1 as
    '1', which is the notation for the string "1", i.e. exactly backwards.
    """
    known = tuple(allowed)
    unknown = sorted((k for k in mapping if k not in known), key=repr)
    return unknown, ", ".join(repr(k) for k in unknown)


def casing_hint(unknown: List[Any], allowed: Iterable[str]) -> Optional[str]:
    """A hint for keys that are only a casing/underscore variant of a real one.

    Deliberately does not name the GameplayEffect schema: this fires for the
    top-level and `simulation` keys too, and those have no counterpart there.
    """
    allowed = tuple(allowed)
    wanted = {canon(a): a for a in allowed}
    hits = [k for k in unknown if canon(k) in wanted]
    if not hits:
        return None
    example = f" — e.g. {hits[0]!r} is {wanted[canon(hits[0])]!r}"
    return (f"keys here are lowercase snake_case, unlike the PascalCase the spec's "
            f"schemas use{example}")


def join_hints(*hints: Optional[str]) -> str:
    """Render hints as a single trailing parenthetical, or nothing."""
    present = [h for h in hints if h]
    return f" ({'; '.join(present)})" if present else ""


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
    if not isinstance(effect_defs, list):
        raise ConfigError(
            f"effects must be a list of effect definitions, got {effect_defs!r}"
        )
    effects = []
    for index, edef in enumerate(effect_defs):
        if not isinstance(edef, dict):
            raise ConfigError(
                f"effect #{index}: each effect must be a mapping, got {edef!r}"
            )
        # Unknown keys first, before the missing-`name` check and before any `.get`:
        # a typo must be reported rather than replaced by a default, and an effect
        # copied from the spec schema has `Name:` rather than `name:` — reporting
        # "missing required 'name'" would send the reader looking for an absent field
        # instead of a mis-cased one, bypassing the hint that explains it. Falls back
        # to the index for the label, since `name` may be exactly what is missing.
        # Pre-rendered, so a name is quoted (`effect 'Poison':`) while the index
        # fallback is not (`effect #0:`), matching the other messages here.
        label = repr(edef["name"]) if "name" in edef else f"#{index}"
        unknown, shown = unknown_keys(edef, EFFECT_KEYS)
        if unknown:
            spec_only = (
                "these belong to the full GameplayEffect schema; the simulator "
                "config is a simplified format and does not model them"
                if any(canon(k) in SPEC_ONLY_EFFECT_KEYS for k in unknown)
                else None
            )
            raise ConfigError(
                f"effect {label}: unknown key(s) {shown}; expected keys are "
                f"{sorted(EFFECT_KEYS)}"
                f"{join_hints(casing_hint(unknown, EFFECT_KEYS), spec_only)}"
            )
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
        mod_defs = edef.get("modifiers", [])
        if not isinstance(mod_defs, list):
            raise ConfigError(
                f"effect {name!r}: modifiers must be a list of modifier mappings, "
                f"got {mod_defs!r}"
            )
        for mdef in mod_defs:
            if not isinstance(mdef, dict):
                raise ConfigError(
                    f"effect {name!r}: each modifier must be a mapping, got "
                    f"{mdef!r}"
                )
            # Before the required-key checks below: a modifier copied from the spec
            # schema has every key wrong, and "missing required 'value'" would send
            # the reader looking for a missing field instead of a renamed one. This
            # also keeps their `sorted(mdef)` away from mixed-type keys, which it
            # cannot sort.
            unknown, shown = unknown_keys(mdef, MODIFIER_KEYS)
            if unknown:
                renamed = (
                    "the magnitude key here is 'value', not the spec's 'Magnitude'"
                    if any(canon(k) == "magnitude" for k in unknown)
                    else None
                )
                raise ConfigError(
                    f"effect {name!r}: unknown modifier key(s) {shown}; expected "
                    f"keys are {sorted(MODIFIER_KEYS)}"
                    f"{join_hints(casing_hint(unknown, MODIFIER_KEYS), renamed)}"
                )
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
            # `channel` becomes a dict key when Multiply modifiers are grouped, so
            # an unhashable value would fail there instead of here.
            channel = mdef.get("channel")
            if channel is not None and not isinstance(channel, str):
                raise ConfigError(
                    f"effect {name!r}: channel on {mdef['attribute']!r} must be a "
                    f"string or omitted, got {channel!r}"
                )
            modifiers.append(
                Modifier(
                    attribute=mdef["attribute"],
                    operation=operation,
                    value=require_number(
                        mdef["value"], f"modifier value on {mdef['attribute']!r}", name
                    ),
                    channel=channel,
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


def bound_references(rule: ClampRule) -> List[str]:
    """The attribute names a rule's bounds reference (non-numeric min/max)."""
    return [
        v
        for v in (rule.min_val, rule.max_val)
        if v is not None and not isinstance(v, (int, float))
    ]


def parse_clamping(
    clamp_defs: Dict[str, Any],
    attribute_names: Iterable[str],
) -> Dict[str, ClampRule]:
    """Parse clamp rules, rejecting unknown names and circular references.

    A rule keyed on an undeclared attribute, or a bound referencing one, would
    silently mean "no bound" — the same silent-typo class #103 closed for
    modifier attribute names. Circular bound references are illegal per §5.4 and
    have no defined resolution, so they are rejected here with the full cycle path.
    """
    if not isinstance(clamp_defs, dict):
        raise ConfigError(
            f"clamping must be a mapping of attribute name to bounds, got "
            f"{clamp_defs!r}"
        )
    known = set(attribute_names)
    rules: Dict[str, ClampRule] = {}
    for attr_name, rule in clamp_defs.items():
        if attr_name not in known:
            raise ConfigError(
                f"clamping: rule for unknown attribute {attr_name!r}; "
                f"declared attributes are {sorted(known)}"
            )
        if not isinstance(rule, dict):
            raise ConfigError(
                f"clamping for {attr_name!r}: bounds must be a mapping with 'min' "
                f"and/or 'max', got {rule!r}"
            )
        # Unknown keys would silently mean "no bound". The trap is real: the spec's
        # own §5.4 examples write `Min:`/`Max:` capitalised, while this config
        # format is lowercase, so copying one in would remove the bound with no
        # signal — the same silent-typo class the reference-name check closes.
        # `unknown_keys` carries the repr handling this needs: YAML keys are not
        # necessarily strings, so neither `sorted` on mixed types nor `.lower()` is
        # safe on the raw keys, and reprs must be joined rather than formatted as a
        # list. It lives in one place so all five key checks share one implementation.
        unknown, shown = unknown_keys(rule, ("min", "max"))
        if unknown:
            hint = (
                " (bounds are lowercase 'min'/'max' here, unlike the capitalised"
                " form in the spec's entity examples)"
                if any(canon(k) in ("min", "max") for k in unknown)
                else ""
            )
            raise ConfigError(
                f"clamping for {attr_name!r}: unknown bound key(s) {shown}; "
                f"expected 'min' and/or 'max'{hint}"
            )
        min_val = rule.get("min")
        max_val = rule.get("max")
        parsed = ClampRule(min_val=min_val, max_val=max_val)
        for label, ref in (("min", min_val), ("max", max_val)):
            if ref is None:
                continue
            # `bool` is an int subclass; a YAML `max: true` would otherwise become
            # a silent ceiling of 1.0, which `require_number` rejects everywhere else.
            if isinstance(ref, bool) or not isinstance(ref, (int, float, str)):
                raise ConfigError(
                    f"clamping for {attr_name!r}: {label} must be a number or an "
                    f"attribute name, got {ref!r}"
                )
            if isinstance(ref, str) and ref not in known:
                raise ConfigError(
                    f"clamping for {attr_name!r}: {label} references unknown "
                    f"attribute {ref!r}; declared attributes are {sorted(known)}"
                )
        rules[attr_name] = parsed

    # Cycle detection (§5.4: circular dependencies MUST NOT be created). Iterative
    # white/grey/black DFS on an explicit ENTER/EXIT stack. Recursing here was half
    # of #107: a legal 1000-long reference chain overflowed the interpreter stack
    # while merely VALIDATING, and because the recursive version re-walked every
    # path from every rule it also enumerated paths rather than nodes, which made a
    # 20-level diamond lattice take ~13s to accept and a 30-level one never finish.
    #
    # `colour` is shared across roots — that sharing is what collapses the lattice.
    #   absent = white (unvisited)
    #   False  = grey  (on the chain currently being explored)
    #   True   = black (already proven acyclic)
    # A black node must be SKIPPED, not reported: two rules legitimately referencing
    # one attribute (a diamond) would otherwise be rejected as a cycle. `path`
    # mirrors the grey chain so a back edge can still name the full cycle.
    colour: Dict[str, bool] = {}
    for root in rules:
        if root in colour:
            continue
        stack: List[tuple] = [(root, False)]  # (name, leaving)
        path: List[str] = []
        while stack:
            name, leaving = stack.pop()
            if leaving:
                colour[name] = True
                path.pop()
                continue
            state = colour.get(name)
            if state is True:
                continue
            if state is False:
                cycle = path[path.index(name):] + [name]
                raise ConfigError(
                    "clamping: circular bound reference: "
                    + " -> ".join(cycle)
                    + " (bounds must not form a cycle; see spec 5.4)"
                )
            colour[name] = False
            path.append(name)
            stack.append((name, True))
            rule = rules.get(name)
            if rule is not None:
                # Reversed, so `min` is explored before `max` as the recursive walk
                # did — a reported cycle path must not depend on this rewrite.
                for ref in reversed(bound_references(rule)):
                    stack.append((ref, False))
    return rules


def apply_bounds(
    value: float, min_v: Optional[float], max_v: Optional[float]
) -> float:
    """§5.3's clamp: max(V_min, min(V_max, value)) — min wins if min > max."""
    if max_v is not None:
        value = min(value, max_v)
    if min_v is not None:
        value = max(value, min_v)
    return value


def bound_from_resolved(
    val: Optional[float | str], resolved: Dict[str, float]
) -> Optional[float]:
    """One bound whose references are already resolved: a number stands alone, a
    name reads the referenced attribute's clamped Current Value out of `resolved`."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    return resolved[val]


def resolve_clamp_value(
    val: Optional[float | str],
    attributes: Dict[str, AttributeState],
    clamp_rules: Dict[str, ClampRule],
    memo: Optional[Dict[str, float]] = None,
) -> Optional[float]:
    """Resolve one bound: a number stands alone; a name is the referenced
    attribute's clamped Current Value (§5.4 rule 1 + §5.3's definition)."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    # Attribute reference; unknown names were rejected in parse_clamping.
    if val not in attributes:
        raise ConfigError(
            f"clamping: bound references unknown attribute {val!r}"
        )
    return clamped_current(val, attributes, clamp_rules, memo)


def clamped_current(
    name: str,
    attributes: Dict[str, AttributeState],
    clamp_rules: Dict[str, ClampRule],
    memo: Optional[Dict[str, float]] = None,
) -> float:
    """The attribute's Current Value per §5.3 — pipeline result, clamped.

    This is the single definition of a clamped Current Value: the display path
    and attribute-reference bound resolution (§5.4) both come through here.

    The walk down the bound-reference graph is iterative, resolving referenced
    attributes before their dependents. Mutual recursion with `resolve_clamp_value`
    was #107: a legal 1000-long reference chain raised an uncaught RecursionError —
    a multi-thousand-frame traceback and exit 1 where every other malformed config
    gets a message and exit 2 — and re-walking a shared reference once per PATH
    rather than once per NODE made a 20-level diamond lattice take ~13s and a
    30-level one hang. The explicit stack fixes the depth; `memo`, which doubles as
    this walk's resolved-value table, fixes the work.

    `memo` caches clamped Current Values for the span of ONE consistent read — a
    span in which no Base Value and no modifier list changes. `clamped_current` is
    pure in `(attributes, clamp_rules)`, so within such a span the cached float is
    bit-identical to a fresh computation. The display loop shares one memo per row
    (nothing mutates between a row's reads, and sharing it is what stops each of N
    attributes re-walking the same chain); `clamp_base_values` passes a fresh one
    per written attribute, because its loop writes a Base Value between iterations.
    Never store a memo on anything longer-lived than one such span.

    The grey-set check guards cycles ONLY, and is unreachable: `parse_clamping`
    rejects them, so hitting one means a validation bug — fail loudly with the chain
    instead of looping. Depth needs no guard now that the walk is iterative.
    """
    if memo is None:
        memo = {}
    if name in memo:
        return memo[name]
    stack: List[tuple] = [(name, False)]  # (attribute, leaving)
    on_path: List[str] = []               # grey chain, for the error message
    grey: set = set()                     # same members, O(1) membership
    while stack:
        node, leaving = stack.pop()
        if leaving:
            # Every reference of `node` is in `memo` by now: LIFO drains all of its
            # ENTER frames — each either already memoised or fully resolved — before
            # this EXIT frame is reached.
            value = compute_unclamped(attributes[node])
            rule = clamp_rules.get(node)
            if rule is not None:
                min_v = bound_from_resolved(rule.min_val, memo)
                max_v = bound_from_resolved(rule.max_val, memo)
                value = apply_bounds(value, min_v, max_v)
            memo[node] = value
            # Keeps `grey` exactly equal to the contents of `on_path`. On its own
            # this line cannot change an outcome — a resolved node is in `memo`, and
            # the ENTER branch below tests `memo` before `grey`, so it never reaches
            # the grey check. It is here so the invariant holds if that order ever
            # changes, not as live cycle protection.
            grey.discard(node)
            on_path.pop()
            continue
        if node in memo:
            continue
        # `parse_clamping` rejects a bound naming an undeclared attribute, so this is
        # unreachable through a parsed config. It matters for a caller that builds
        # `ClampRule`s directly (the test suite does): without it, a reference two or
        # more hops from the entry point surfaces as a bare `KeyError` from the memo
        # lookup at EXIT rather than as a ConfigError.
        if node not in attributes:
            raise ConfigError(
                f"clamping: bound references unknown attribute {node!r}"
                + (f" (via {' -> '.join(on_path)})" if on_path else "")
            )
        if node in grey:
            raise ConfigError(
                "clamping: circular bound reference during resolution: "
                + " -> ".join(on_path + [node])
            )
        grey.add(node)
        on_path.append(node)
        stack.append((node, True))
        rule = clamp_rules.get(node)
        if rule is not None:
            # Reversed so `min` resolves before `max`, matching the recursion this
            # replaces; a duplicate or already-resolved reference is skipped at its
            # own ENTER frame.
            for ref in reversed(bound_references(rule)):
                if ref not in memo:
                    stack.append((ref, False))
    return memo[name]


def compute_unclamped(state: AttributeState) -> float:
    """Run the modifier pipeline, steps 1-6 — WITHOUT clamping.

    This is not a Current Value: §5.3 puts the clamp inside that definition
    (step 7). Use `clamped_current` for anything that needs a Current Value,
    including resolving an attribute-reference bound (§5.4).
    """
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


def parse_simulation(sim_def: Any) -> Dict[str, float]:
    """Validate the `simulation` block and return it.

    Called from both `simulate()` and `main()`. `main()` needs it because the CLI
    flags fall back to this block, and `simulate()` needs it so a direct library
    caller — the test suite, or a consuming skill importing this module — gets the
    same rejection rather than a silently substituted default. A typo'd `timestap`
    would otherwise simulate at the default resolution and quietly change the whole
    x-axis of the result.
    """
    # A present-but-empty `simulation:` is read as absent rather than rejected, unlike
    # `attributes:`. The asymmetry is deliberate: every key here is optional and has
    # both a default and a CLI override, so an empty block loses nothing, whereas an
    # empty `attributes:` describes a world with nothing in it to simulate.
    if sim_def is None:
        sim_def = {}
    if not isinstance(sim_def, dict):
        raise ConfigError(
            f"simulation must be a mapping with 'duration' and/or 'timestep', got "
            f"{sim_def!r}"
        )
    unknown, shown = unknown_keys(sim_def, SIMULATION_KEYS)
    if unknown:
        raise ConfigError(
            f"simulation: unknown key(s) {shown}; expected keys are "
            f"{sorted(SIMULATION_KEYS)}"
            f"{join_hints(casing_hint(unknown, SIMULATION_KEYS))}"
        )
    for key in SIMULATION_KEYS:
        if key in sim_def:
            value = sim_def[key]
            # `bool` is an int subclass, so a YAML `duration: yes` would otherwise
            # simulate exactly one second.
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ConfigError(
                    f"simulation: {key} must be a number, got {value!r}"
                )
    # A zero or negative timestep divides by zero when the step count is computed —
    # the same never-advances class as `period: 0`, which is already rejected, and
    # the last remaining traceback-and-exit-1 path reachable from a plausible typo.
    if "timestep" in sim_def and sim_def["timestep"] <= 0:
        raise ConfigError(
            f"simulation: timestep must be > 0, got {sim_def['timestep']!r}"
        )
    if "duration" in sim_def and sim_def["duration"] < 0:
        raise ConfigError(
            f"simulation: duration must be >= 0, got {sim_def['duration']!r}"
        )
    return sim_def


def transitive_references(name: str, clamp_rules: Dict[str, ClampRule]) -> set:
    """All attributes reachable from `name` via clamp-bound references."""
    seen: set = set()
    stack = [name]
    while stack:
        rule = clamp_rules.get(stack.pop())
        if rule is None:
            continue
        for ref in bound_references(rule):
            if ref not in seen:
                seen.add(ref)
                stack.append(ref)
    return seen


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
    # Clamp in dependency order — a referenced attribute before its dependents —
    # with the incoming (authored) order as the tiebreak among independents.
    # Clamping a referenced attribute's base changes its clamped Current Value,
    # so the order among interdependent attributes changes the result; the
    # reference graph is a DAG (parse_clamping rejects cycles), so dependency
    # order gives the unique fixed answer.
    # Kahn's algorithm, keyed on the authored index so ties break as they did when
    # this was a scan for the first ready attribute. That scan emitted the same
    # sequence — `remaining` preserved authored relative order, so "first ready
    # element" is "authored-earliest ready element", and on a DAG an attribute never
    # reaches itself, which made the old self-excluding slice a no-op — but it
    # rebuilt a candidate set per scan step. That is cubic in the batch size: timed
    # in isolation on a 1000-attribute reference chain it took 6.2s, so it would
    # have become #107's remaining bottleneck the moment resolution went linear.
    remaining = [n for n in attr_names if n in attributes]
    # Transitive, not direct: with `A max: C`, `C max: B` and a batch writing {A, B}
    # but not C, A still depends on B through C.
    reach = {n: transitive_references(n, clamp_rules) for n in remaining}
    member = set(remaining)
    blockers = {n: reach[n] & member for n in remaining}
    dependents: Dict[str, List[str]] = {n: [] for n in remaining}
    for n in remaining:
        for b in blockers[n]:
            dependents[b].append(n)
    index_of = {n: i for i, n in enumerate(remaining)}
    ready = [i for i, n in enumerate(remaining) if not blockers[n]]
    heapq.heapify(ready)
    ordered: List[str] = []
    while ready:
        name = remaining[heapq.heappop(ready)]
        ordered.append(name)
        for dep in dependents[name]:
            blockers[dep].discard(name)
            if not blockers[dep]:
                heapq.heappush(ready, index_of[dep])
    if len(ordered) != len(remaining):  # unreachable: cycles rejected at parse time
        stuck = [n for n in remaining if blockers[n]]
        raise ConfigError(
            f"clamping: could not order base clamp for {stuck!r}"
        )

    for attr_name in ordered:
        rule = clamp_rules.get(attr_name)
        if rule is None:
            continue
        state = attributes[attr_name]
        # A fresh memo per attribute, shared only between this rule's two bounds —
        # no write happens between them. It must NOT span the loop: the write below
        # changes this attribute's clamped Current Value, and the dependency ordering
        # above exists precisely so each later clamp sees the earlier ones' writes.
        # (That ordering does in fact mean a batch-wide memo would happen to be
        # correct today, since any reader of a batch member is ordered after it. But
        # that rides on an invariant of the code above; scoping the memo to one
        # iteration is correct by construction, costs nothing measurable, and will
        # not turn a future ordering bug into silently wrong numbers.)
        memo: Dict[str, float] = {}
        min_v = resolve_clamp_value(rule.min_val, attributes, clamp_rules, memo)
        max_v = resolve_clamp_value(rule.max_val, attributes, clamp_rules, memo)
        state.base_value = apply_bounds(state.base_value, min_v, max_v)


def simulate(
    config: Dict[str, Any],
    duration: float,
    timestep: float,
) -> List[Dict[str, Any]]:
    """Run the simulation and return time-series data."""

    # An empty YAML file loads as None, which used to traceback in main() before the
    # ConfigError handler could turn it into a message.
    if not isinstance(config, dict):
        raise ConfigError(
            f"config must be a mapping with keys {sorted(TOP_LEVEL_KEYS)}, got "
            f"{config!r}"
        )
    unknown, shown = unknown_keys(config, TOP_LEVEL_KEYS)
    if unknown:
        raise ConfigError(
            f"config: unknown top-level key(s) {shown}; expected keys are "
            f"{sorted(TOP_LEVEL_KEYS)}"
            f"{join_hints(casing_hint(unknown, TOP_LEVEL_KEYS))}"
        )
    # Validated here as well as in main(), so importing callers get the same errors.
    parse_simulation(config.get("simulation", {}))

    # Initialize attributes
    # A present-but-empty `attributes:` is rejected, not read as {}. YAML gives None
    # there, and treating that as "no attributes" would be both a silent acceptance
    # of a config that can simulate nothing and inconsistent with `clamping:` and
    # `effects:`, which reject a null block. It also kept main()'s own
    # `config.get("attributes", {})` — which sees the raw None, not this default —
    # crashing with an AttributeError after simulate() had already succeeded.
    attr_defs = config.get("attributes", {})
    if not isinstance(attr_defs, dict):
        raise ConfigError(
            f"attributes must be a mapping of attribute name to initial value, got "
            f"{attr_defs!r}"
        )
    attributes: Dict[str, AttributeState] = {}
    for name, base_val in attr_defs.items():
        # A non-string name crashes the `sorted(attributes)` used for the CSV header
        # and the error messages; `float(True)` would silently make a YAML
        # `Health: yes` an attribute worth 1.0.
        if not isinstance(name, str):
            raise ConfigError(
                f"attributes: attribute name must be a string, got {name!r}"
            )
        if isinstance(base_val, bool) or not isinstance(base_val, (int, float)):
            raise ConfigError(
                f"attribute {name!r}: initial value must be a number, got "
                f"{base_val!r}"
            )
        attributes[name] = AttributeState(base_value=float(base_val))

    # Parse clamping (validates rule keys, bound references, and acyclicity)
    clamp_rules = parse_clamping(config.get("clamping", {}), attributes)

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
                    effect.expire_at is None
                    or at_or_before(effect.next_tick_at, effect.expire_at)
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
        # One memo per row. Nothing mutates between a row's reads — application,
        # ticking and expiry all happened above, and the next step's mutations happen
        # after the row is recorded — so sharing it across the row's attributes is
        # exact. It is also the other half of #107's cost: without it, each of N
        # attributes re-walks the same reference chain, which is what made a
        # 400-attribute chain take 0.6s for a zero-duration run.
        memo: Dict[str, float] = {}
        for name in attr_names:
            row[name] = round(clamped_current(name, attributes, clamp_rules, memo), 4)
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

    # Inside the try: reading the `simulation` block can itself fail (a non-mapping
    # block, or an empty file that loaded as None), and that has to surface as
    # `error: …` with exit 2 like every other malformed config, not as a traceback.
    try:
        sim_config = (
            parse_simulation(config.get("simulation", {}))
            if isinstance(config, dict) else {}
        )
        # `is None`, not `or`: 0 is falsy, so `--duration 0` used to fall through to
        # the config value and silently run the full simulation the user was trying
        # to shorten.
        duration = (
            args.duration if args.duration is not None
            else sim_config.get("duration", 20.0)
        )
        timestep = (
            args.timestep if args.timestep is not None
            else sim_config.get("timestep", 0.1)
        )
        # The flags bypass parse_simulation, so they need the same bounds. Without
        # this, `--timestep 0` is a ZeroDivisionError traceback.
        if timestep <= 0:
            raise ConfigError(f"--timestep must be > 0, got {timestep!r}")
        if duration < 0:
            raise ConfigError(f"--duration must be >= 0, got {duration!r}")
        results = simulate(config, duration, timestep)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # `or {}` rather than a `.get` default: a present-but-null `attributes:` yields
    # None, which has no `.keys()`. simulate() rejects that case now, so this is
    # belt-and-braces against main() ever reading the raw config where simulate()
    # reads a validated copy.
    attr_names = sorted((config.get("attributes") or {}).keys())

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
