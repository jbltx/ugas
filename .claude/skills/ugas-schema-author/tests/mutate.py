#!/usr/bin/env python3
"""Mutation harness for `test_simulate.py`.

The test suite is validated by mutation, not by counting checks: a passing suite
proves nothing on its own, because an assertion can pass for the wrong reason.
This applies one behaviour-changing edit to `scripts/simulate.py` at a time, runs
the suite, and reports whether any case noticed. Run it from anywhere:

    python .claude/skills/ugas-schema-author/tests/mutate.py
    python .claude/skills/ugas-schema-author/tests/mutate.py --list
    python .claude/skills/ugas-schema-author/tests/mutate.py --only R7 M1

Exits 0 when every mutation is either CAUGHT or a documented EQUIVALENT, 1 if any
mutation SURVIVED undocumented or any anchor went stale.

## Two guards, both of which caught real misreadings while this was written

1. **The diff gate.** If a mutation's anchor text is not found, the file is
   unchanged and the suite passes — which reads exactly like "the mutation was not
   detected". Every mutation is therefore verified to have changed the file, with
   `diff` as the arbiter, and reports SKIP-BROKEN rather than a result otherwise.
   A stale anchor is a failure of this harness, not evidence about the suite.

2. **Crash detection.** Python exits 1 on an uncaught exception — the same code the
   suite uses for "some cases failed". A mutation that crashes the suite mid-run
   prints no FAIL line, so exit status alone makes it look like a survivor. The
   summary line the suite prints only on a complete run is the real signal.

## EQUIVALENT mutations

Three mutations survive and are *supposed* to: they change the code without
changing its behaviour, and the reason is recorded next to each. They are listed
so that a future change making one of them observable shows up as a surprise
rather than as a new mystery.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "scripts" / "simulate.py"
TESTS = HERE / "test_simulate.py"
# Prefer the repo's venv when present; the suite needs PyYAML.
VENV = HERE.parents[3] / ".venv" / "bin" / "python"
PYTHON = str(VENV) if VENV.exists() else sys.executable

CAUGHT, SURVIVED, EQUIVALENT, BROKEN = "CAUGHT", "SURVIVED", "EQUIVALENT", "BROKEN"

# (id, description, [(anchor, replacement), ...], expected)
#
# `expected` is CAUGHT for a real defect the suite must notice, or EQUIVALENT for a
# behaviour-preserving edit with the reason in the description.
MUTATIONS: list[tuple] = [
    # ---------------------------------------------------------------- Instant Multiply
    ("M1", "released bug: Instant Multiply scales by the raw magnitude",
     [("state.base_value *= 1.0 + mod.value", "state.base_value *= mod.value")],
     CAUGHT),
    ("M2", "Instant Multiply sign inverted",
     [("state.base_value *= 1.0 + mod.value", "state.base_value *= 1.0 - mod.value")],
     CAUGHT),
    ("M3", "channel grouping applied to the Instant base write (durational semantics)",
     [("    written: List[str] = []\n    for mod in modifiers:",
       "    written: List[str] = []\n"
       "    _ch = {}\n"
       "    for _m in modifiers:\n"
       "        if _m.operation == 'Multiply':\n"
       "            _ch.setdefault((_m.attribute, _m.channel), []).append(_m)\n"
       "    _skip = set()\n"
       "    for _ms in _ch.values():\n"
       "        if len(_ms) > 1:\n"
       "            _ms[0].value = sum(_m.value for _m in _ms)\n"
       "            for _m in _ms[1:]:\n"
       "                _skip.add(id(_m))\n"
       "    modifiers = [_m for _m in modifiers if id(_m) not in _skip]\n"
       "    for mod in modifiers:")],
     CAUGHT),
    ("M4", "Instant Multiply skipped entirely",
     [('        elif mod.operation == "Multiply":',
       '        elif mod.operation == "Multiply" and False:')],
     CAUGHT),
    ("M5", "Instant Multiply treated as Add",
     [("state.base_value *= 1.0 + mod.value", "state.base_value += mod.value")],
     CAUGHT),
    ("M6a", "authored order broken: every Add applied first",
     [("    written: List[str] = []\n    for mod in modifiers:",
       "    written: List[str] = []\n"
       "    modifiers = sorted(modifiers, key=lambda m: m.operation != 'Add')\n"
       "    for mod in modifiers:")],
     CAUGHT),
    ("M6b", "authored order broken: every Multiply applied first",
     [("    written: List[str] = []\n    for mod in modifiers:",
       "    written: List[str] = []\n"
       "    modifiers = sorted(modifiers, key=lambda m: m.operation != 'Multiply')\n"
       "    for mod in modifiers:")],
     CAUGHT),
    ("M7", "Multiply-only targets omitted from `written`, so the base clamp is skipped",
     [("        if mod.attribute not in written:\n            written.append(mod.attribute)",
       '        if mod.attribute not in written and mod.operation != "Multiply":\n'
       "            written.append(mod.attribute)")],
     CAUGHT),
    ("M8", "channel grouping removed from the Current-Value pipeline (the inverse)",
     [('key = channel if channel is not None else ("<singleton>", i)',
       'key = ("<singleton>", i)')],
     CAUGHT),

    # ------------------------------------------------- the other operations (§5.2/§5.3)
    ("R1", "periodic Multiply routed through the base, so it compounds per tick",
     [('    base_writes = [m for m in modifiers if m.operation != "Multiply"]',
       "    base_writes = list(modifiers)")],
     CAUGHT),
    ("R2", "periodic Multiply never registered as a Current-Value modifier",
     [('                            [m for m in effect.modifiers if m.operation == "Multiply"],',
       "                            [],")],
     CAUGHT),
    ("R3", "Instant Override treated as Add",
     [('        elif mod.operation == "Override":\n            state.base_value = mod.value',
       '        elif mod.operation == "Override":\n            state.base_value += mod.value')],
     CAUGHT),
    ("R4", "Instant AddPost subtracts",
     [('        elif mod.operation == "AddPost":\n            state.base_value += mod.value',
       '        elif mod.operation == "AddPost":\n            state.base_value -= mod.value')],
     CAUGHT),
    ("R5", "AddPost dropped from the pipeline (step 5)",
     [("    result += sum(magnitude for _owner, magnitude in state.add_post_modifiers)",
       "    pass")],
     CAUGHT),
    ("R6", "Override tie-break reversed: earliest wins instead of latest (§5.3 LIFO)",
     [("        return self.override_entries[-1][1] if self.override_entries else None",
       "        return self.override_entries[0][1] if self.override_entries else None")],
     CAUGHT),

    # ------------------------------------------------------- clamping semantics (§5.3/§5.4)
    ("A1", "bound resolved against the UNCLAMPED Current Value (pre-#106 behaviour)",
     [("            memo[node] = value\n            # Keeps `grey`",
       "            memo[node] = compute_unclamped(attributes[node])\n            # Keeps `grey`")],
     CAUGHT),
    ("A2", "min/max precedence inverted, so max wins when min > max",
     [("    if max_v is not None:\n        value = min(value, max_v)\n"
       "    if min_v is not None:\n        value = max(value, min_v)",
       "    if min_v is not None:\n        value = max(value, min_v)\n"
       "    if max_v is not None:\n        value = min(value, max_v)")],
     CAUGHT),
    ("A3", "min bound dropped during resolution",
     [("                min_v = bound_from_resolved(rule.min_val, memo)", "                min_v = None")],
     CAUGHT),
    ("A4", "display memo hoisted to whole-simulation lifetime, so reads go stale",
     [("        memo: Dict[str, float] = {}\n        for name in attr_names:",
       "        memo = globals().setdefault('_PERSIST', {})\n        for name in attr_names:")],
     CAUGHT),
    ("A5", "the deep unvalidated-reference guard removed (bare KeyError escapes)",
     [("        if node not in attributes:\n            raise ConfigError(",
       "        if False:\n            raise ConfigError(")],
     CAUGHT),

    # ------------------------------------------------------------- graph walks (#107)
    ("P1", "parse-time DFS treats black as grey, rejecting a legal diamond",
     [("            if state is True:\n                continue",
       "            if state is True:\n                pass")],
     CAUGHT),
    ("P2", "parse-time DFS keeps no black set, so it enumerates paths not nodes",
     [("            if leaving:\n                colour[name] = True\n                path.pop()",
       "            if leaving:\n                colour.pop(name, None)\n                path.pop()")],
     CAUGHT),
    ("C1", "batch ordering uses direct references instead of transitive ones",
     [("reach = {n: transitive_references(n, clamp_rules) for n in remaining}",
       "reach = {n: set(bound_references(clamp_rules[n])) if n in clamp_rules "
       "else set() for n in remaining}")],
     CAUGHT),

    # ------------------------------------------------------------ config validation
    ("K1", "effect unknown-key check removed",
     [("        unknown, shown = unknown_keys(edef, EFFECT_KEYS)\n        if unknown:",
       "        unknown, shown = unknown_keys(edef, EFFECT_KEYS)\n        if False:")],
     CAUGHT),
    ("K2", "modifier unknown-key check removed",
     [("            unknown, shown = unknown_keys(mdef, MODIFIER_KEYS)\n            if unknown:",
       "            unknown, shown = unknown_keys(mdef, MODIFIER_KEYS)\n            if False:")],
     CAUGHT),
    ("K3", "top-level unknown-key check removed",
     [("    unknown, shown = unknown_keys(config, TOP_LEVEL_KEYS)\n    if unknown:",
       "    unknown, shown = unknown_keys(config, TOP_LEVEL_KEYS)\n    if False:")],
     CAUGHT),
    ("K4", "simulation-block unknown-key check removed",
     [("    unknown, shown = unknown_keys(sim_def, SIMULATION_KEYS)\n    if unknown:",
       "    unknown, shown = unknown_keys(sim_def, SIMULATION_KEYS)\n    if False:")],
     CAUGHT),
    ("K5", "the casing hint fires unconditionally",
     [("    hits = [k for k in unknown if canon(k) in wanted]\n    if not hits:\n        return None",
       "    hits = [k for k in unknown if canon(k) in wanted] or list(unknown)\n"
       "    if not hits:\n        return None")],
     CAUGHT),
    ("K6", "canon() lowercases without stripping underscores, so PascalCase never matches",
     [('    return key.lower().replace("_", "") if isinstance(key, str) else None',
       "    return key.lower() if isinstance(key, str) else None")],
     CAUGHT),
    ("K7", "canon() does not guard non-string YAML keys",
     [('    return key.lower().replace("_", "") if isinstance(key, str) else None',
       '    return key.lower().replace("_", "")')],
     CAUGHT),
    ("K8", "unknown_keys sorts raw keys, which cannot order mixed types",
     [("    unknown = sorted((k for k in mapping if k not in known), key=repr)",
       "    unknown = sorted(k for k in mapping if k not in known)")],
     CAUGHT),
    ("K9", "unknown_keys double-reprs, printing an int key 1 as '1'",
     [('    return unknown, ", ".join(repr(k) for k in unknown)',
       '    return unknown, f"{[repr(k) for k in unknown]}"')],
     CAUGHT),
    ("K10", "spec-only-field hint removed",
     [("                if any(canon(k) in SPEC_ONLY_EFFECT_KEYS for k in unknown)",
       "                if False")],
     CAUGHT),
    ("K11", "Magnitude-rename hint removed",
     [('                    if any(canon(k) == "magnitude" for k in unknown)',
       "                    if False")],
     CAUGHT),
    ("K12", "a YAML bool accepted as an attribute's initial value (float(True) is 1.0)",
     [("        if isinstance(base_val, bool) or not isinstance(base_val, (int, float)):",
       "        if not isinstance(base_val, (int, float)):")],
     CAUGHT),
    ("K13", "`effects` list-shape check removed",
     [("    if not isinstance(effect_defs, list):", "    if False:")], CAUGHT),
    ("K14", "effect mapping-shape check removed",
     [("        if not isinstance(edef, dict):", "        if False:")], CAUGHT),
    ("K15", "`modifiers` list-shape check removed",
     [("        if not isinstance(mod_defs, list):", "        if False:")], CAUGHT),
    ("K16", "config mapping-shape check removed",
     [("    if not isinstance(config, dict):", "    if False:")], CAUGHT),
    ("K17", "simulation number check removed",
     [("            if isinstance(value, bool) or not isinstance(value, (int, float)):",
       "            if False:")],
     CAUGHT),
    ("K18", "parse_simulation not called from simulate(), so importers skip validation",
     [('    parse_simulation(config.get("simulation", {}))', "    pass")], CAUGHT),
    ("R7", "a present-but-null `attributes:` accepted as {} again (crashed the CLI)",
     [('    attr_defs = config.get("attributes", {})\n    if not isinstance(attr_defs, dict):',
       '    attr_defs = config.get("attributes", {}) or {}\n'
       "    if not isinstance(attr_defs, dict):")],
     CAUGHT),
    ("R8", "timestep positivity check removed (ZeroDivisionError returns)",
     [('    if "timestep" in sim_def and sim_def["timestep"] <= 0:', "    if False:")],
     CAUGHT),
    ("R9", "missing-name check back before the unknown-key check, bypassing the hint",
     [('        label = repr(edef["name"]) if "name" in edef else f"#{index}"',
       '        label = repr(edef["name"]) if "name" in edef else f"#{index}"\n'
       '        if "name" not in edef:\n'
       "            raise ConfigError(f\"effect #{index}: missing required 'name'\")")],
     CAUGHT),

    # ------------------------------------------------------------------- EQUIVALENT
    ("E1", "memo shared across the whole clamp_base_values batch. Equivalent because "
           "dependency ordering puts every reader of a batch member after its write, "
           "so no stale value is ever read. Scoped per iteration anyway, so that "
           "correctness does not depend on another function's invariant.",
     [("    for attr_name in ordered:\n        rule = clamp_rules.get(attr_name)",
       "    _batch = {}\n    for attr_name in ordered:\n        rule = clamp_rules.get(attr_name)"),
      ("        memo: Dict[str, float] = {}\n        min_v = resolve_clamp_value",
       "        memo = _batch\n        min_v = resolve_clamp_value")],
     EQUIVALENT),
    ("E2", "topological tiebreak changed from authored-earliest to LIFO. Equivalent "
           "because ready attributes are pairwise non-reaching, so clamping them in "
           "any order commutes. The heap preserves pick-identity with the scan it "
           "replaced, which is what makes that rewrite provably behaviour-preserving.",
     [("        name = remaining[heapq.heappop(ready)]", "        name = remaining[ready.pop()]"),
      ("                heapq.heappush(ready, index_of[dep])", "                ready.append(index_of[dep])")],
     EQUIVALENT),
    ("E3", "`grey.discard` removed. Equivalent because a resolved node is in `memo` "
           "and the ENTER branch tests `memo` before `grey`, so it never reaches the "
           "grey check. Kept to hold grey == on_path if that order ever changes.",
     [("            memo[node] = value\n            # Keeps `grey`", "            memo[node] = value\n            # keeps `grey`"),
      ("            grey.discard(node)\n            on_path.pop()", "            on_path.pop()")],
     EQUIVALENT),
]


def run_one(mid: str, description: str, edits: list, expected: str) -> str:
    original = SRC.read_text()
    text = original
    for anchor, replacement in edits:
        if anchor not in text:
            print(f"  BROKEN    {mid}: anchor not found — {anchor.splitlines()[0][:70]!r}")
            print("            (a stale anchor says nothing about the suite; fix it here)")
            return BROKEN
        text = text.replace(anchor, replacement, 1)
    if text == original:
        print(f"  BROKEN    {mid}: edits produced no net change")
        return BROKEN

    backup = SRC.with_suffix(".py.mutation-backup")
    shutil.copy(SRC, backup)
    SRC.write_text(text)
    try:
        # Guard 1: prove the file really differs before trusting any result.
        if subprocess.run(["diff", "-q", str(SRC), str(backup)],
                          capture_output=True).returncode == 0:
            print(f"  BROKEN    {mid}: diff reports the file unchanged")
            return BROKEN
        try:
            proc = subprocess.run([PYTHON, str(TESTS)], capture_output=True,
                                  text=True, timeout=120)
        except subprocess.TimeoutExpired:
            print(f"  CAUGHT    {mid}: suite did not finish within 120s ({description})")
            return CAUGHT
        # Guard 2: the summary line is the only proof the suite ran to completion.
        finished = any("passed," in line for line in proc.stdout.splitlines()[-3:])
        if not finished:
            last = (proc.stderr.strip().splitlines() or ["<no stderr>"])[-1]
            print(f"  CAUGHT    {mid}: suite crashed :: {last[:90]}")
            return CAUGHT
        failures = [l.strip() for l in proc.stdout.splitlines()
                    if l.strip().startswith("FAIL")]
        if failures:
            print(f"  CAUGHT    {mid}: {len(failures)} failing — {failures[0][5:85]}")
            return CAUGHT
        if expected is EQUIVALENT:
            print(f"  EQUIVALENT {mid}: survived as documented")
            return EQUIVALENT
        print(f"  SURVIVED  {mid}: NOT DETECTED — {description}")
        return SURVIVED
    finally:
        shutil.copy(backup, SRC)
        backup.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="list mutations and exit")
    parser.add_argument("--only", nargs="+", metavar="ID", help="run only these ids")
    args = parser.parse_args()

    selected = [m for m in MUTATIONS if not args.only or m[0] in args.only]
    if args.list:
        for mid, description, _edits, expected in selected:
            print(f"  {mid:<5} [{expected}] {description}")
        return 0
    if args.only:
        unknown = set(args.only) - {m[0] for m in MUTATIONS}
        if unknown:
            print(f"unknown mutation id(s): {sorted(unknown)}", file=sys.stderr)
            return 1

    # A mutated file left behind by an interrupted run would silently poison every
    # later result, so refuse to start unless the suite is green to begin with.
    baseline = subprocess.run([PYTHON, str(TESTS)], capture_output=True, text=True)
    if baseline.returncode != 0:
        print("refusing to run: the suite does not pass unmutated", file=sys.stderr)
        print(baseline.stdout[-2000:], file=sys.stderr)
        return 1
    print(f"baseline: {baseline.stdout.strip().splitlines()[-1]}\n")

    tally: dict = {}
    for mid, description, edits, expected in selected:
        result = run_one(mid, description, edits, expected)
        tally[result] = tally.get(result, 0) + 1

    print(f"\n{tally.get(CAUGHT, 0)} caught, {tally.get(EQUIVALENT, 0)} equivalent, "
          f"{tally.get(SURVIVED, 0)} survived, {tally.get(BROKEN, 0)} broken anchors")
    return 1 if tally.get(SURVIVED) or tally.get(BROKEN) else 0


if __name__ == "__main__":
    sys.exit(main())
