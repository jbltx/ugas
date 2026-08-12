#!/usr/bin/env python3
"""Regression tests for the simulator's clamping and modifier pipeline.

Standalone by design — no pytest dependency, matching the plain-script style of
`scripts/`. Run it directly:

    python .claude/skills/ugas-schema-author/tests/test_simulate.py

Exits 0 when every case passes, 1 otherwise. Cases are drawn from the bugs found
in issues #99, #100, #101 and #104; each asserts a specific number so a
regression names itself rather than just failing.

TWO TRAPS when adding cases here, both of which produced tests that passed for the
wrong reason during review:

1. **Read-time clamping hides the Base Value.** A displayed value is clamped on
   read, so asserting it tells you nothing about what was written to the base. To
   test a base write, either assert `base_value` directly, or let the bound recover
   afterwards and assert a value that could only follow from a correct base.

2. **Ordering only matters when the referenced attribute's clamped value can
   change.** If a referenced attribute already sits below its own bound, its
   clamped Current Value is identical before and after its base is clamped, so
   every ordering agrees and the case proves nothing. Give it a live modifier, or
   start it above its bound.

The suite is checked by mutation rather than by counting checks: apply one
behaviour-changing edit to `scripts/simulate.py` and confirm a case fails. Several
natural-looking assertions here survive that test.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import simulate as S

PASS = 0
FAIL = 0

def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS {label}")
    else:
        FAIL += 1
        print(f"  FAIL {label} {detail}")

def run(cfg, duration=10, timestep=1.0):
    return S.simulate(cfg, duration, timestep)

def col(rows, t, name):
    for r in rows:
        if abs(r["time"] - t) < 1e-9:
            return r[name]
    raise KeyError(t)

def expect_error(label, cfg, *needles):
    try:
        run(cfg)
    except S.ConfigError as e:
        msg = str(e)
        check(label, all(n in msg for n in needles), f"got: {msg}")
    else:
        check(label, False, "no ConfigError raised")

print("== 1. Issue repro: display bound uses clamped current ==")
# MaxHealth base 100, static max 200; +500 buff -> unclamped 700, displayed 200.
# Instant +600 Health at t=2 -> Health must display 200, not 700.
cfg = {
    "attributes": {"Health": 100.0, "MaxHealth": 100.0},
    "clamping": {"Health": {"min": 0, "max": "MaxHealth"},
                 "MaxHealth": {"max": 200}},
    "effects": [
        {"name": "MaxBuff", "apply_at": 0.0, "duration_policy": "HasDuration",
         "duration": 5.0,
         "modifiers": [{"attribute": "MaxHealth", "operation": "Add", "value": 500.0}]},
        {"name": "BigHeal", "apply_at": 2.0, "duration_policy": "Instant",
         "modifiers": [{"attribute": "Health", "operation": "Add", "value": 600.0}]},
    ],
}
rows = run(cfg)
check("Health displayed 200 at t=2 (was 700)", col(rows, 2.0, "Health") == 200.0,
      f"got {col(rows, 2.0, 'Health')}")
check("MaxHealth displayed 200 while buffed", col(rows, 2.0, "MaxHealth") == 200.0)

print("== 2. Base corruption: the stored Base Value itself, not the display ==")
# The display CANNOT distinguish base 200 from base 700 here: MaxHealth is capped at
# 200, so min(base, <=200) is <=200 either way. Assert the Base Value directly.
#
# MaxHealth: base 100, static max 200, carrying a +500 modifier -> unclamped current
# 600, clamped current 200. An Instant +600 to Health must clamp the WRITE to the
# clamped bound (200), not the unclamped one (600).
attrs2 = {"Health": S.AttributeState(100.0), "MaxHealth": S.AttributeState(100.0)}
rules2 = S.parse_clamping(
    {"Health": {"min": 0, "max": "MaxHealth"}, "MaxHealth": {"max": 200}}, attrs2
)
S.add_duration_modifiers(0, [S.Modifier("MaxHealth", "Add", 500.0)], attrs2)
check("MaxHealth unclamped current is 600", S.compute_unclamped(attrs2["MaxHealth"]) == 600.0)
check("MaxHealth clamped current is 200",
      S.clamped_current("MaxHealth", attrs2, rules2) == 200.0)
written = S.apply_instant_modifiers([S.Modifier("Health", "Add", 600.0)], attrs2)
S.clamp_base_values(written, attrs2, rules2)
check("Health BASE written as 200, not 700",
      attrs2["Health"].base_value == 200.0, f"got {attrs2['Health'].base_value}")
# ...and it stays 200 once the bound modifier goes away — no hidden excess to reveal.
S.remove_duration_modifiers(0, attrs2)
check("Health base still 200 after the bound modifier expires",
      attrs2["Health"].base_value == 200.0, f"got {attrs2['Health'].base_value}")
check("Health displays 100 once MaxHealth returns to 100",
      S.clamped_current("Health", attrs2, rules2) == 100.0,
      f"got {S.clamped_current('Health', attrs2, rules2)}")

print("== 3. Legal 3-chain keeps working, order-independent ==")
# A max: B, B max: C, C static max 100; all start at 500 -> all normalise to 100 at t=0.
cfg3 = {
    "attributes": {"A": 500.0, "B": 500.0, "C": 500.0},
    "clamping": {"A": {"max": "B"}, "B": {"max": "C"}, "C": {"max": 100}},
    "effects": [],
}
rows = run(cfg3, duration=1)
check("3-chain: A=B=C=100 at t=0",
      all(col(rows, 0.0, n) == 100.0 for n in "ABC"),
      f"got {[col(rows, 0.0, n) for n in 'ABC']}")

print("== 4. Cycles rejected at parse time with path ==")
expect_error("2-cycle A<->B",
             {"attributes": {"A": 1.0, "B": 1.0},
              "clamping": {"A": {"max": "B"}, "B": {"max": "A"}}, "effects": []},
             "circular", "A -> B -> A")
expect_error("self-reference Health max: Health",
             {"attributes": {"Health": 1.0},
              "clamping": {"Health": {"max": "Health"}}, "effects": []},
             "circular", "Health -> Health")
expect_error("3-cycle via min",
             {"attributes": {"A": 1.0, "B": 1.0, "C": 1.0},
              "clamping": {"A": {"max": "B"}, "B": {"min": "C"}, "C": {"max": "A"}},
              "effects": []},
             "circular")

print("== 5. Unknown names rejected ==")
expect_error("unknown reference max: MaxHelth",
             {"attributes": {"Health": 1.0, "MaxHealth": 1.0},
              "clamping": {"Health": {"max": "MaxHelth"}}, "effects": []},
             "MaxHelth", "unknown")
expect_error("rule keyed on unknown attribute",
             {"attributes": {"Health": 1.0},
              "clamping": {"Helth": {"min": 0}}, "effects": []},
             "Helth", "unknown")
# Assert these are caught while PARSING, not later while resolving. Both layers
# raise ConfigError, so a whole-simulation check above cannot tell them apart —
# and the point of the parse-time check is to reject before anything runs.
for label, clamping in (
    ("parse-time: unknown reference", {"Health": {"max": "MaxHelth"}}),
    ("parse-time: rule on unknown attribute", {"Helth": {"min": 0}}),
):
    try:
        S.parse_clamping(clamping, {"Health": None, "MaxHealth": None})
        check(label, False, "parse_clamping accepted it")
    except S.ConfigError:
        check(label, True)

print("== 5b. Malformed clamp shapes rejected, not tracebacked ==")
# Needles matter here: without them any ConfigError satisfies the case, so a
# wrong-reason rejection would pass and the case-mismatch hint would be untested.
for label, clamping, needles in (
    ("rule value not a mapping", {"Health": "nonsense"}, ("mapping",)),
    ("rule value is a list", {"Health": [1, 2]}, ("mapping",)),
    ("rule value is null", {"Health": None}, ("mapping",)),
    ("clamping itself not a mapping", [1, 2], ("clamping must be a mapping",)),
    ("bound is a bool", {"Health": {"max": True}}, ("max", "number")),
    ("bound is a list", {"Health": {"min": [1, 2]}}, ("min", "number")),
    # The spec's §5.4 entity examples write Min:/Max: capitalised; this config
    # format is lowercase, so a copied example must error rather than silently
    # dropping the bound — and must say so.
    ("capitalised Min/Max", {"Health": {"Min": 0, "Max": 100}},
     ("unknown bound key", "'Max'", "lowercase")),
    ("misspelled bound key", {"Health": {"mim": 0, "max": 100}},
     ("unknown bound key", "'mim'")),
    # YAML keys are not always strings: `1:` is an int and a bare `no:` is False.
    ("non-string rule key", {"Health": {1: 5}}, ("unknown bound key", "1")),
    ("YAML bare no as a key", {"Health": {False: 5, "max": 100}},
     ("unknown bound key", "False")),
    ("mixed-type unknown keys", {"Health": {"mim": 0, 1: 2}},
     ("unknown bound key",)),
):
    expect_error(label, {"attributes": {"Health": 5.0}, "clamping": clamping,
                        "effects": []}, *needles)
# The hint must appear ONLY for a case mismatch, not for an unrelated typo.
try:
    S.parse_clamping({"Health": {"mim": 0}}, {"Health": None})
    check("no case-mismatch hint for an unrelated typo", False, "accepted")
except S.ConfigError as e:
    check("no case-mismatch hint for an unrelated typo", "lowercase" not in str(e),
          f"got {e}")

print("== 6. min > max: formula's answer (min wins) ==")
# min 50, max 30, value 100 -> max(50, min(30, 100)) = 50 (old code gave 30)
cfg6 = {
    "attributes": {"X": 100.0},
    "clamping": {"X": {"min": 50, "max": 30}},
    "effects": [],
}
rows = run(cfg6, duration=1)
check("min>max display gives 50", col(rows, 0.0, "X") == 50.0,
      f"got {col(rows, 0.0, 'X')}")
# and via base write:
cfg6b = {
    "attributes": {"X": 10.0},
    "clamping": {"X": {"min": 50, "max": 30}},
    "effects": [{"name": "W", "apply_at": 0.0, "duration_policy": "Instant",
                 "modifiers": [{"attribute": "X", "operation": "Add", "value": 90.0}]}],
}
rows = run(cfg6b, duration=1)
check("min>max base write gives 50", col(rows, 1.0, "X") == 50.0,
      f"got {col(rows, 1.0, 'X')}")

print("== 7. Interdependent batch is clamped in dependency order ==")
# One Instant effect writes a dependent attribute and the attribute its bound
# references. Order matters because clamping the referenced attribute's BASE
# changes its clamped Current Value, which is what the dependent clamps against.
#
# Making the difference observable needs a live Current-Value modifier on the
# referenced attribute — without one, its clamped current is the same before and
# after its base is clamped, and both orders agree (which is why a display-only
# assertion here tests nothing).
#
#   MaxHealth: base 100, static max 200, live Multiply -0.5
#   one Instant: Health += 600  (authored FIRST, the dependent)
#                MaxHealth += 450 (authored second, the referenced)
#
#   dependency order: MaxHealth base 550 -> 200 first, so its clamped current is
#                     200 * 0.5 = 100, and Health's base clamps to 100.
#   authored order:   Health clamps first against min(550*0.5, 200) = 200.
#
# Assert the BASE, not the display: display clamps on read, so it cannot tell a
# base of 200 from a base of 100 here.
attrs7 = {"Health": S.AttributeState(100.0), "MaxHealth": S.AttributeState(100.0)}
rules7 = S.parse_clamping(
    {"Health": {"max": "MaxHealth"}, "MaxHealth": {"max": 200}}, attrs7
)
S.add_duration_modifiers(0, [S.Modifier("MaxHealth", "Multiply", -0.5)], attrs7)
written7 = S.apply_instant_modifiers(
    [S.Modifier("Health", "Add", 600.0), S.Modifier("MaxHealth", "Add", 450.0)], attrs7
)
check("written order is the authored order (dependent first)",
      written7 == ["Health", "MaxHealth"], f"got {written7}")
S.clamp_base_values(written7, attrs7, rules7)
check("referenced attribute's base clamped to 200",
      attrs7["MaxHealth"].base_value == 200.0, f"got {attrs7['MaxHealth'].base_value}")
check("dependent base is 100 (dependency order), not 200 (authored order)",
      attrs7["Health"].base_value == 100.0, f"got {attrs7['Health'].base_value}")

print("== 7a. Out-of-bounds initial state is normalised at t=0 ==")
# X starts at 500 against a static max of 100. The t=0 normalisation must write the
# BASE down to 100; a display-only assertion at t=0 cannot see it, since read-time
# clamping shows 100 either way. A later small Instant reveals which happened:
# normalised base 100 - 10 -> 90; un-normalised base 500 - 10 -> 490, displayed 100.
cfg7a = {
    "attributes": {"X": 500.0},
    "clamping": {"X": {"max": 100}},
    "effects": [{"name": "Chip", "apply_at": 1.0, "duration_policy": "Instant",
                 "modifiers": [{"attribute": "X", "operation": "Add", "value": -10.0}]}],
}
rows = run(cfg7a, duration=2)
check("t=0 normalisation wrote the base, so the chip shows 90 (not 100)",
      col(rows, 1.0, "X") == 90.0, f"got {col(rows, 1.0, 'X')}")

print("== 7b. Base clamping is actually WIRED IN, end to end ==")
# Cases 2 and 7 compose apply_instant_modifiers + clamp_base_values by hand, which
# proves the functions but not that `simulate()` calls them. Removing either call
# from the loop leaves those cases green, so assert through simulate() instead —
# and read the base indirectly by letting the bound RECOVER afterwards, since a
# clamped display hides an over-large base while the bound is still low.
#
# Health starts 100, bounded min 0. A -250 Instant would drive the base to -150
# without clamping; clamped it stops at 0. Then a +50 heal reveals which happened:
# clamped -> 50, unclamped -> -100.
cfg7b = {
    "attributes": {"Health": 100.0},
    "clamping": {"Health": {"min": 0, "max": 1000}},
    "effects": [
        {"name": "Overkill", "apply_at": 1.0, "duration_policy": "Instant",
         "modifiers": [{"attribute": "Health", "operation": "Add", "value": -250.0}]},
        {"name": "Heal", "apply_at": 2.0, "duration_policy": "Instant",
         "modifiers": [{"attribute": "Health", "operation": "Add", "value": 50.0}]},
    ],
}
rows = run(cfg7b, duration=3)
check("Instant path: base floored at 0, so the heal shows 50 (not -100)",
      col(rows, 2.0, "Health") == 50.0, f"got {col(rows, 2.0, 'Health')}")

# Same for the periodic execution path: a DOT overshooting the floor must not
# bank a negative base that a later heal has to climb out of.
cfg7c = {
    "attributes": {"Health": 30.0},
    "clamping": {"Health": {"min": 0, "max": 1000}},
    "effects": [
        {"name": "DOT", "apply_at": 0.0, "duration_policy": "HasDuration",
         "duration": 3.0, "period": 1.0,
         "modifiers": [{"attribute": "Health", "operation": "Add", "value": -20.0}]},
        {"name": "Heal", "apply_at": 5.0, "duration_policy": "Instant",
         "modifiers": [{"attribute": "Health", "operation": "Add", "value": 50.0}]},
    ],
}
rows = run(cfg7c, duration=6)
check("periodic path: base floored at 0, so the heal shows 50 (not -10)",
      col(rows, 5.0, "Health") == 50.0, f"got {col(rows, 5.0, 'Health')}")

# There is a THIRD clamp call site: the first execution of a periodic effect with
# `execute_on_application: true`, which runs on the application branch rather than
# the tick loop. Cover it too — the two cases above leave it untested.
cfg7e = {
    "attributes": {"Health": 30.0},
    "clamping": {"Health": {"min": 0, "max": 1000}},
    "effects": [
        {"name": "Nuke", "apply_at": 0.0, "duration_policy": "HasDuration",
         "duration": 1.0, "period": 5.0, "execute_on_application": True,
         "modifiers": [{"attribute": "Health", "operation": "Add", "value": -250.0}]},
        {"name": "Heal", "apply_at": 1.0, "duration_policy": "Instant",
         "modifiers": [{"attribute": "Health", "operation": "Add", "value": 50.0}]},
    ],
}
rows = run(cfg7e, duration=2)
check("execute_on_application path: base floored at 0, heal shows 50 (not 0)",
      col(rows, 1.0, "Health") == 50.0, f"got {col(rows, 1.0, 'Health')}")

print("== 7f. A legal diamond of bound references is ACCEPTED ==")
# Two reference bounds on one rule, converging on a shared attribute. The cycle
# DFS must not mistake a re-visited node for a cycle — dropping its path.pop()
# would reject this as `D -> C -> D`. No other case has a rule with two
# attribute-reference bounds.
cfg7f = {
    "attributes": {"A": 500.0, "B": 500.0, "C": 500.0, "D": 500.0},
    "clamping": {"A": {"min": "B", "max": "C"}, "B": {"max": "D"},
                 "C": {"max": "D"}, "D": {"max": 100}},
    "effects": [],
}
try:
    rows = run(cfg7f, duration=1)
    check("legal diamond accepted, all resolve to 100",
          all(col(rows, 0.0, n) == 100.0 for n in "ABCD"),
          f"got {[col(rows, 0.0, n) for n in 'ABCD']}")
except S.ConfigError as e:
    check("legal diamond accepted, all resolve to 100", False, f"rejected: {e}")

print("== 7d. Ordering uses TRANSITIVE references (skip-intermediate) ==")
# A max: C, C max: B, B max: 200. A batch writes A and B but NOT C, so A depends
# on B only *through* C — ordering on direct references alone would clamp A first.
#
# C must start ABOVE its own bound, or its clamped value is identical before and
# after B's base is clamped and both orderings agree (which is what made an
# earlier version of this case pass under the direct-only mutation).
#
#   B: base 100 +450 -> 550, live Multiply -0.5, static max 200
#      clamped current 200 before its base is clamped, 100 after (200 x 0.5)
#   C: base 500, bound = B's clamped current -> 200 before, 100 after
#   A: base 100 +600 -> 700, bound = C's clamped current
#
#   transitive: B's base clamped first (550 -> 200), so A's bound is 100
#   direct-only: A clamped first against C's 200, giving 200
attrs7d = {
    "A": S.AttributeState(100.0),
    "B": S.AttributeState(100.0),
    "C": S.AttributeState(500.0),
}
rules7d = S.parse_clamping(
    {"A": {"max": "C"}, "C": {"max": "B"}, "B": {"max": 200}}, attrs7d
)
check("A reaches B transitively through C",
      S.transitive_references("A", rules7d) == {"B", "C"},
      f"got {S.transitive_references('A', rules7d)}")
S.add_duration_modifiers(0, [S.Modifier("B", "Multiply", -0.5)], attrs7d)
written7d = S.apply_instant_modifiers(
    [S.Modifier("A", "Add", 600.0), S.Modifier("B", "Add", 450.0)], attrs7d
)
S.clamp_base_values(written7d, attrs7d, rules7d)
check("transitive ordering: A base is 100, not 200 (direct-only)",
      attrs7d["A"].base_value == 100.0, f"got {attrs7d['A'].base_value}")

print("== 8. #101 regression: temp debuff must not destroy dependent base ==")
cfg8 = {
    "attributes": {"Health": 100.0, "MaxHealth": 100.0},
    "clamping": {"Health": {"min": 0, "max": "MaxHealth"}},
    "effects": [{"name": "MaxDebuff", "apply_at": 1.0,
                 "duration_policy": "HasDuration", "duration": 3.0,
                 "modifiers": [{"attribute": "MaxHealth", "operation": "Multiply",
                                "value": -0.5}]}],
}
rows = run(cfg8)
check("Health reads 50 during debuff", col(rows, 2.0, "Health") == 50.0,
      f"got {col(rows, 2.0, 'Health')}")
check("Health back to 100 after expiry (base untouched)",
      col(rows, 5.0, "Health") == 100.0, f"got {col(rows, 5.0, 'Health')}")

print("== 9. Doc example config unchanged (no rule on referenced attr) ==")
cfg9 = {
    "attributes": {"Health": 100.0, "MaxHealth": 100.0, "Mana": 50.0, "Armor": 20.0},
    "clamping": {"Health": {"min": 0, "max": "MaxHealth"}, "Mana": {"min": 0}},
    "effects": [
        {"name": "PoisonDOT", "apply_at": 0.0, "duration_policy": "HasDuration",
         "duration": 10.0, "period": 1.0, "execute_on_application": False,
         "modifiers": [{"attribute": "Health", "operation": "Add", "value": -5.0}]},
        {"name": "HealOverTime", "apply_at": 3.0, "duration_policy": "HasDuration",
         "duration": 8.0, "period": 2.0, "execute_on_application": True,
         "modifiers": [{"attribute": "Health", "operation": "Add", "value": 10.0}]},
        {"name": "ArmorBuff", "apply_at": 0.0, "duration_policy": "HasDuration",
         "duration": 15.0,
         "modifiers": [{"attribute": "Armor", "operation": "Multiply", "value": 0.5,
                        "channel": "Buffs"}]},
        {"name": "BigHit", "apply_at": 5.0, "duration_policy": "Instant",
         "modifiers": [{"attribute": "Health", "operation": "Add", "value": -40.0}]},
    ],
    "simulation": {"duration": 20.0, "timestep": 0.1},
}
rows = run(cfg9, duration=20, timestep=0.1)
# Pinned checkpoints. `MaxHealth` carries no clamp rule here, so clamped and
# unclamped bound resolution coincide and this trace is unchanged by the #104
# fix — which is the point: the doc example must keep working exactly as
# documented. Armor 30 = 20 x (1 + 0.5) until the buff expires at t=15.
expected9 = {
    0.0: (100.0, 100.0, 50.0, 30.0),
    3.0: (95.0, 100.0, 50.0, 30.0),
    5.0: (55.0, 100.0, 50.0, 30.0),
    10.0: (50.0, 100.0, 50.0, 30.0),
    15.0: (60.0, 100.0, 50.0, 20.0),
    20.0: (60.0, 100.0, 50.0, 20.0),
}
for t, exp in expected9.items():
    got = tuple(col(rows, t, n) for n in ("Health", "MaxHealth", "Mana", "Armor"))
    check(f"doc example at t={t}", got == exp, f"got {got}, expected {exp}")

print("== 10. Display order-independence: chain resolves same regardless ==")
# already covered by natural recursion; spot-check chain under a live buff
cfg10 = {
    "attributes": {"A": 500.0, "B": 500.0, "C": 500.0},
    "clamping": {"A": {"max": "B"}, "B": {"max": "C"}, "C": {"max": 100}},
    "effects": [{"name": "BuffC", "apply_at": 0.0, "duration_policy": "HasDuration",
                 "duration": 2.0,
                 "modifiers": [{"attribute": "C", "operation": "Add", "value": 1000.0}]}],
}
rows = run(cfg10, duration=4)
check("chain under buff: C displays 100, so A,B display 100 too",
      all(col(rows, 1.0, n) == 100.0 for n in "ABC"),
      f"got {[col(rows, 1.0, n) for n in 'ABC']}")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
