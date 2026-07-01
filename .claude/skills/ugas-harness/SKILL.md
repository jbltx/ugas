---
name: ugas-harness
description: >
  Use this skill to build AND VERIFY a playable game system end to end — not just author the
  data, but run it in a live engine and iterate until it demonstrably works. Trigger on
  requests with a working/tested/proven bar: "build a working <genre> and prove it plays",
  "stand up and test the combat for my game", "make an autonomous pass at an RPG prototype and
  verify it", "bring up and validate the gameplay systems", or "does my UGAS setup actually
  behave right in-engine?". It drives the closed loop Author → Validate → Run → Observe →
  Iterate: it delegates authoring to `gameplay-creator-assistant` and `ugas-schema-author`,
  validates against the JSON schemas, imports into a Unity project running the `ugas-unity`
  runtime, exercises the systems with the `unity-tools` eval-sim, and fixes what fails —
  autonomously, pausing only at genuine decision forks. Prerequisite for the Run/Observe
  stages: a Unity project with `ugas-unity` and the `unity-tools` server installed. For pure
  scaffolding with NO in-engine verification, use `gameplay-creator-assistant` directly.
---

# UGAS Harness — Autonomous Build-and-Verify Loop

You are the orchestrator of a gamedev build loop. Your job is not to hand back a definition and
hope it plays — it is to return a game system that has been **run and observed working** in a
real engine, or a precise account of exactly what blocks it. You compose existing skills into
one closed loop and drive it with as little human input as the task honestly allows.

The north star: *any kind of game*. You do not hardcode genre knowledge — you start from a
genre pack as a **soft prior**, adapt it to the brief, and verify the result against runnable
acceptance scenarios. Green scenarios are the definition of done.

## The loop

| Stage | What happens | Tool / building block | Output |
|-------|--------------|-----------------------|--------|
| **1. Author** | Scaffold the four pillars + Controller from the closest genre pack, extended to the brief | `gameplay-creator-assistant` (whole game) → `ugas-schema-author` (each entity) | `entities/*.yaml` |
| **2. Validate** | Every file passes its JSON schema; cross-references resolve | schemas + `ugas-schema-author` / `scripts/validate_schema_examples.py` | validated entities |
| **3. Run** | Import the entities into the Unity project and build the runtime state | `unity-tools eval` against `ugas-unity` | live `UgasController`s |
| **4. Observe** | Exercise the signature mechanics deterministically and read the results | `unity-tools eval` / `run-tests --mode EditMode` | pass/fail + numbers |
| **5. Iterate** | Diagnose each failure; fix the definition, or flag a genuine runtime/spec gap | you | a fix or a precise report |

Repeat 3–5 until the genre's acceptance scenarios pass. Then summarize what works, the numbers
observed, the engine seams the consumer must still implement (`ExecCalc_*`), and every
assumption you made.

## Building blocks — delegate, don't reinvent

| Need | Use it for |
|------|-----------|
| `gameplay-creator-assistant` | Whole-game structure from a genre pack: which pillars/actors/mechanics; cross-entity consistency. It fetches the spec/schemas/packs from the docs site. |
| `ugas-schema-author` | Single-entity YAML correctness, schema-field lookups, the modifier-pipeline math, and **balance simulation** (`scripts/simulate.py`: DPS curves, time-to-kill, build compares). |
| `unity-tools` | The Run/Observe substrate — drive the live editor: `reload`, `eval`, `run-tests --mode EditMode`, `get-logs`. |

Own the *loop* and the *verification*; delegate *authoring* and *balancing* to the skills that
carry those contracts. If a skill isn't installed, fall back to the fetched schema YAMLs and the
pack `entities/` as worked examples.

## Genre packs are soft priors, not truth

A pack is the fastest correct starting point, not a specification to obey. You may keep, drop,
extend, or **depart** from any pack element when the brief calls for it. Two rules:

- Extend **additively** and through the pillars — new `State.*` tags granted by Effects, new
  Effects/Abilities — never by mutating attributes directly (§3.1) or redeclaring core lifecycle
  tags (`State.Alive/Combat/Dead` are owned by the core registry; reference, don't redeclare).
- A *meaningful* departure from the pack's signature model (e.g. replacing hitscan with
  projectiles, or ammo with heat) is a **fork** — surface it at the Ask gate below before you
  commit to it. Cosmetic deviations (numbers, names) need no confirmation.

## Autonomy contract

Default to **acting**, not asking. Infer sensible defaults from the pack and brief, record them
in an **assumptions log**, and proceed. Only stop at a genuine fork — a choice you cannot resolve
from the request, the pack, or the schemas, where guessing wrong is expensive to undo. Use the
Ask tool (a short, optioned question) at exactly these four points:

1. **Genre / pillar shape is ambiguous.** The brief fits no pack cleanly, or two packs fit
   equally — confirm the base and the core loop before authoring.
2. **A meaningful departure from the pack prior.** You're about to replace or drop a signature
   mechanic — confirm the intent, don't silently reshape the genre.
3. **An outward or irreversible write.** Creating files/dirs in the user's project, a new repo,
   or anything networked/published — confirm before the first such write, not each one.
4. **Verification is genuinely ambiguous.** A scenario's expected result is a design choice, not
   a fact (e.g. "should stun cancel the cast?") — confirm the oracle rather than inventing it.

Everything else — default and log it. Batch questions: one round at a fork, not a drip. Keep the
assumptions log in your final summary so the user can correct any default in one pass.

## Verification substrate — the eval-sim

The canonical in-engine check is a **deterministic eval-sim**: build the runtime state, drive it a
fixed number of ticks, and assert on the numbers. Run it through `unity-tools eval` (a C# snippet)
or as an EditMode test. The proven shape:

```csharp
// AddComponent builds an empty tag registry + effects system (Awake does not fire in EditMode,
// so public calls lazily EnsureInitialized).
var gc = new GameObject("Sim").AddComponent<UgasController>();
gc.RegisterAttributeSet(new RuntimeAttributeSet(attributeSetDefinition));
gc.FindAttribute("Health").BaseValue = 100f;
gc.ApplyEffect(damageEffect);        // or GrantAbility + TryActivateAbility
gc.Tick(0.1f);                       // advance deterministically; loop for periodic/duration
return gc.GetCurrentValue("Health"); // read Current (aggregated) or GetBaseValue (instant/base)
```

Spatial systems use the same shape via `UgasSpatialWorld`: `Register` controllers, `AddRegion` /
`AddObserver`, `world.Tick()` to reconcile zone tags + perception, and `world.ApplyAreaEffect(...)`
for AoE — then assert on granted tags and attribute deltas.

Rules that keep verification honest:

- **EditMode + `eval` only.** They are reliable. **Do NOT drive PlayMode through the `unity-tools`
  server — it wedges** (see the `unity-tools` skill / project notes); use the in-editor Test Runner
  if PlayMode is ever truly needed.
- **`reload` after any C# change** before running.
- **CI is not your oracle.** In `ugas-unity`'s CI the Unity test job is *skipped* (no license); the
  authoritative signal is your **local** EditMode/eval run against the live editor.
- **Determinism.** Fixed tick sizes, seeded RNG (§9.5), and stable spatial ordering (§17.7) so a
  scenario's result is reproducible — otherwise it isn't an oracle.
- `Object` is ambiguous in `eval`; use `UnityEngine.Object.DestroyImmediate` and clean up spawned
  GameObjects/SOs.

## Acceptance scenarios are the success oracle

For each genre, codify its **signature mechanic as a runnable scenario** — the §16 case studies
(Platformer, Racing, ARPG, Puzzle) plus the spatial ones (AoE hits the right set; range gate;
zone entry/exit grants/removes a tag; perception acquires within FOV+LOS). A scenario is: *set up
→ tick → assert an exact number or tag state*. "This kind of game works" ≙ its scenarios are green.
This suite is both the definition of done and the regression net (it lives under `#17` of the
roadmap). Reuse `ugas-schema-author`'s `simulate.py` for balance oracles (DPS, time-to-kill).

**Self-eval.** Before trusting the loop on a new genre, confirm it can *catch* a bug: inject a
known-wrong value (e.g. an unclamped resource, an off-by-one period) and verify a scenario goes
red. A loop that never fails is not verifying anything. (This repo's own eval-sim already caught
real runtime bugs — base-value clamping and periodic timing — so the method works.)

## Iterate — turn a red scenario into a fix

On failure, read the eval output and localize:

- **Wrong number, right shape** → an authoring/balance bug: fix the entity YAML (delegate to
  `ugas-schema-author`), re-validate, re-run.
- **Right definition, wrong engine behavior** → a genuine `ugas-unity` runtime gap or a spec
  ambiguity. Do not paper over it in the data. Capture the minimal failing eval-sim, and flag it
  (a `ugas-unity` issue, or a spec question) — a precise repro is the deliverable.
- **Missing seam** → the mechanic needs an `ExecCalc_*` execution the consumer implements; note it
  as a seam, not a failure.

## Prerequisites & environment

- **Author/Validate** need only the fetched spec + schemas (network), like the authoring skills.
- **Run/Observe** need a **Unity project with `ugas-unity`** and the **`unity-tools` server**
  running (the editor open on that project). Target it with `--project-path`. If it's absent, do
  the Author/Validate stages, produce the eval-sim scenarios as ready-to-run C#, and tell the user
  what to open so you can close the loop.

## Non-goals

- Not a scaffolder alone — if the user only wants a definition with no in-engine proof, that's
  `gameplay-creator-assistant`.
- Not a single-entity editor or balance tweak — that's `ugas-schema-author`.
- Does not author new **genre packs** or edit the **UGAS spec** — those are separate deliverables;
  here a pack is a read-only prior.
- Does not drive PlayMode via the server, and does not treat a green CI as a passed test.
