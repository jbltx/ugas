---
'ugas': patch
---

[Fixed] `ugas-schema-author` simulator — four conformance bugs that made simulated attribute traces wrong in ways an author would not notice. Resolves the follow-ups filed while reviewing the modifier-pipeline sweep.

**Timing was `--timestep`-dependent.** Effect lifetime and tick cadence were tracked with per-step accumulators decremented in the same loop iteration that applied the effect, so an effect was charged for a timestep during which it had only just become active. A `HasDuration` effect lived `duration - timestep`: a 2.0s effect lasted 1.0s at `--timestep 1.0` but 1.5s at `0.5`, meaning the same config produced different answers at different resolutions — the one property a balance-projection tool must not have. The first periodic execution was early for the same reason, and with `execute_on_application: true` and `timestep == period` the effect **double-ticked at t=0**, applying twice the intended magnitude. Scheduling is now absolute (`expire_at`, `next_tick_at`) derived from the authored `apply_at`, and the dead `first_tick_done` field — written twice, never read, which is what let the double-tick through — is gone. Traces are now identical across timesteps.

**Effect identity was the name string.** Modifier ownership was keyed on the effect's name, and nothing deduped or rejected collisions, so two config entries sharing a name were indistinguishable at removal. The first expiry withdrew *both* effects' modifiers; a timed effect could permanently strip a same-named `Infinite` effect's contribution. Ownership is now keyed on a per-entry `instance_id`, with the name kept only for display and events.

**A temporary debuff on a referenced bound permanently destroyed the dependent attribute's Base Value.** Clamping ran as a per-step sweep over every attribute and clamped *Base Values* against bounds resolved from the referenced attribute's *Current* Value. With `Health` bounded by `max: MaxHealth`, a 3s `Multiply -0.5` on `MaxHealth` clamped `Health`'s **base** 100 → 50, and `Health` stayed at 50 after the debuff expired — a temporary −50% max-HP debuff permanently halving the character. §5.2 permits Base Values to change only through Instant applications and periodic executions. Base clamping now happens only immediately after such a write and only for the attributes that write touched; Current-Value clamping stays a read-time concern, per §5.3's formula and §5.4's rule that an attribute-reference bound resolves against that attribute's Current Value.

**Unrecognised operations were silently dropped.** The operation dispatch had no `else` branch and `parse_effects` defaulted a *missing* `operation` to `Add`, so `Divide`, lowercase `add`, and uppercase `MULTIPLY` all no-opped while the run still logged the effect as applied — and a modifier with no `operation` silently became a flat `Add` nobody authored. §5.2 requires that an implementation MUST NOT silently drop any operation. `operation` is now required and validated case-sensitively, `duration_policy` likewise, and the CLI reports the offending effect and attribute and exits `2` instead of emitting a plausible-looking wrong curve.

The config is validated more broadly in the same spirit, since every one of these previously produced either a wrong curve or a hang rather than a message:

- A modifier naming an attribute that was never declared is rejected rather than silently ignored.
- `period` must be positive. A `period` of `0` used to spin the tick loop forever, as did a negative one; the loop now also fails loudly if a period is too small to advance the schedule at all, which a positive-value check alone does not catch.
- `period` on an `Instant` effect is rejected as meaningless, and a negative `HasDuration` duration is rejected in favour of `Infinite`.
- `period`, `duration`, and `apply_at` must be numbers. YAML hands back a string more readily than it looks — `1.0e16` fails PyYAML's float pattern, which requires a signed exponent — and comparing one later raised a bare `TypeError`.
- A missing effect `name` raises a config error instead of a `KeyError` traceback.

Attributes whose initial value starts outside their declared bounds are normalised once at t=0, before any effect is active — restoring behaviour the old per-step clamp sweep provided incidentally, without reintroducing the write-through it caused.

Base clamping now runs at write time in authored modifier order, where it previously ran as a per-step sweep in clamp-rule declaration order. Both are deterministic; the change matters because clamping is order-sensitive when one attribute's bound references another, and tying the order to the authored modifiers makes it predictable from the config rather than from an unrelated declaration order. (Resolving such bounds against the referenced attribute's *clamped* Current Value, which would remove most of that order-sensitivity, is deliberately left to a follow-up — it needs cycle detection that nothing currently requires.)

No schema, spec, or gameplay-data changes; this is entirely the bundled simulator plus its config reference.
