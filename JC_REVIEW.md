# UGAS Spec Review — A Game Developer's Perspective

**Reviewer:** *Written in the spirit of John Carmack — systems programmer, game engine architect, performance absolutist*
**Spec Version:** UGAS v1.0 (February 2026)
**Date:** February 2026

---

## Executive Summary

UGAS is an ambitious attempt to do something the game industry genuinely needs: an open, engine-agnostic specification for gameplay ability systems. The core architecture is sound — it is essentially a clean-room formalization of Unreal's GameplayAbilitySystem (GAS), which is itself battle-tested across titles like Fortnite, Paragon, and dozens of shipped games. The four-pillar model (Attributes, Tags, Abilities, Effects) is the right decomposition. The effect-as-sole-mutation-layer pattern is correct and elegant.

That said, v1.0 has gaps that would cause real pain in production. Several sections are underspecified precisely where correctness matters most: networking, determinism, and the attribute math. The "universal" framing — including AI-generated worlds — oversells the spec's current maturity.

**Verdict: Interesting and worth pursuing. Not production-ready as written. Needs a v1.1 pass on the critical issues below.**

---

## Part I — What Works Well

### 1.1 The Four-Pillar Model Is Correct

Separating state into Attributes (numeric), Tags (semantic), Abilities (behavioral), and Effects (mutation) is the right architecture. It forces a clean separation of concerns that eliminates the classic "spaghetti game code" problem where a single health variable has direct references scattered across UI, networking, AI, and animation systems.

The reactive/observer approach over polling is the right call. A game running at 60Hz with 200 entities polling health every tick is wasting CPU. Event-driven notification through `OnAttributeChanged` is the professional solution.

### 1.2 Effects as the Sole Mutation Layer

The mandate that Effects are the ONLY authorized mechanism for modifying Attributes or Tags is one of the most important architectural decisions in the spec. This gives you:

- A complete audit trail of every state change
- A single choke point for replication
- A single choke point for client-side prediction rollback
- A natural serialization boundary for save/load

This is the core insight that makes GAS work in production, and UGAS preserves it correctly.

### 1.3 Dual-Value Attribute Pattern

Base Value + Current Value is the right design. Temporary effects operating only on Current Value, with Instant effects modifying Base Value, cleanly separates "permanent change" from "active modifier." This makes save/load trivial (serialize Base Values only) and makes effect removal clean (just recompute Current Value from Base + active modifiers).

### 1.4 Tag Inheritance

Implicit parent tag propagation (adding `State.Debuff.Stunned.Magic` implicitly grants `State.Debuff.Stunned`, `State.Debuff`, `State.`) is elegant and powerful. It allows coarse queries (`HasTag("State.Debuff")`) and precise queries (`MatchesTagExact("State.Debuff.Stunned.Magic")`) from a single data representation. This is cheap to implement with a hash set and pays dividends in design flexibility.

### 1.5 Execution Policies Replace Stacking

`RunInParallel`, `RunInSequence`, `RunInMerge` is a clean abstraction over what most engines call "stacking." The naming is semantic rather than mechanical, which is better for a spec document. Most real stacking patterns map cleanly to one of these three.

### 1.6 Case Studies Span the Genre Space

Covering Platformer, Racing, ARPG, and Puzzle in concrete YAML/TypeScript examples is excellent. It demonstrates that the spec isn't just theory — it handles genuinely different gameplay paradigms. The Tire Temperature model in the Racing study and the Damage Bucket architecture in the ARPG study show the spec has been thought through with real design scenarios in mind.

### 1.7 Costs and Cooldowns as Effects

Treating ability costs and cooldowns as Gameplay Effects (rather than separate special-purpose variables) is the right call. It means the same modifier pipeline that buffs damage can also reduce mana costs. The "Mana Efficiency" example demonstrates this correctly. This is one of the most underappreciated design decisions in UE4's GAS and UGAS correctly preserves it.

---

## Part II — Critical Issues

### 2.1 ~~The Attribute Formula Has an Ambiguous Term~~ ✓ FIXED

**Section 5.3, Formula:**

```
V_current = (V_base + Σa_i) × (1 + Σp_j) × Πm_k + Σb_l
```

~~The spec defines both `a_i` as "Flat additive modifiers (Add operations)" and `b_l` as "Bonus flat (Add operations)." Both are described as `Add` operations but are mathematically distinct — `a_i` is applied before multiplication, `b_l` is applied after. There is no field in the `Modifier` struct or schema that distinguishes between pre-multiply and post-multiply Add operations.~~

**Resolution:** A distinct `AddPost` operation was introduced alongside the existing `Add` operation. The formula legend, the Order of Operations step 7, the §9.4.1 operations table, and both JSON and YAML schemas (`gameplay_effect.json` / `gameplay_effect.yaml`) have been updated. `Add` now unambiguously maps to the pre-multiply `a_i` bucket (pipeline step 2); `AddPost` maps to the post-multiply `b_l` bucket (pipeline step 7). The `Channel` field on `Modifier` has also been documented — it controls named aggregation channels for damage-bucket systems (§15.3), which is a separate concern from pre/post-multiply ordering.

### 2.2 ~~Division by Zero Is Unaddressed~~ ✓ FIXED

**Resolution:** The `Divide` operation has been removed entirely from the spec and both schemas. Division is now expressed as `Multiply` with a reciprocal magnitude (e.g., dividing by 2 = `Multiply` with magnitude `0.5`). This eliminates the divide-by-zero edge case with zero added complexity — `Multiply` already handles the full space of multiplicative transformations.

### 2.3 ~~Override Modifier Conflict Resolution Is Undefined~~ ✓ FIXED

**Resolution:** A `Priority: integer` field (default `0`, negative values valid) has been added to `GameplayEffect`. The Override conflict resolution rule is now formally specified in §5.3:

1. **Highest Priority wins** — the Override from the effect with the largest `Priority` value replaces the result; lower-priority Overrides for the same Attribute are ignored.
2. **Equal Priority → last-applied wins (LIFO)** — deterministic by application timestamp, independent of network arrival order.

The `Priority` field has been added to the `GameplayEffect` struct (§9.1), the Appendix B inline YAML schema, `gameplay_effect.json`, and `gameplay_effect.yaml`.

### 2.4 Loose Tags Break the Core Principle

**Sections 8.4 and 15.1 directly contradict Section 3.1:**

Section 3.1 states: *"Effects are the ONLY authorized mechanism for modifying Attributes or Tags."*

Section 8.4 `CommitAbility` does this:
```typescript
GC.AddLooseGameplayTags(spec.AbilityClass.ActivationOwnedTags);
```

Section 15.1 `GA_Jump` does this:
```typescript
this.Owner.Tags.AddTag("State.InAir");
this.Owner.Tags.RemoveTag("State.Grounded");
```

These are direct tag mutations that bypass the Effect layer entirely. This means:
- They are not tracked in the effect history
- They are not automatically replicated via the standard pipeline
- They cannot be rolled back during client-side prediction without special-case code
- They break the "single choke point" guarantee

The spec needs to either:
1. Define `LooseGameplayTags` as a formal, explicitly-replicated primitive with documented replication behavior, OR
2. Remove direct tag manipulation and require all tag changes to flow through Effects

UE4 GAS has the same loose tag problem and it causes real bugs. This spec has an opportunity to be cleaner.

### 2.5 The Networking Model Is Dangerously Underspecified

Section 13 covers networking at a conceptual level but leaves critical questions unanswered:

**Prediction window:** How many frames/milliseconds ahead can a client predict? What is the maximum prediction depth? Without a bound, a high-latency client can predict arbitrarily far into the future, causing unrecoverable state divergence.

**State capture scope:** `CaptureState()` in section 13.4 is called but never defined. Does it capture the entire GC state? Just attributes? Active effects? Physics state? The cost of a full state capture per predicted ability activation could be prohibitive at scale.

**Multi-ability prediction:** If a player predicts two abilities activating in the same frame (e.g., the second ability is triggered by an attribute threshold reached by the first), how are the prediction keys coordinated? The spec shows single-ability prediction only.

**Cross-GC effect prediction:** When client predicts `ApplyGameplayEffectToTarget(enemy, spec)`, does the client also predict the state change on the enemy GC? The enemy GC is not owned by this client — its prediction behavior is undefined.

**Rollback and replay:** Section 13.5 says "re-apply all inputs that occurred since that state" but input history storage format, duration, and maximum replay depth are unspecified. A naive full-replay implementation at 60Hz with 200ms ping requires re-simulating 12 frames of the entire game — this is only feasible if the replay is scoped to the single GC, but the spec doesn't say so.

This section needs a dedicated networking annex with formal definitions, not aspirational pseudocode.

### 2.6 Deterministic Randomness Is Not Addressed

**Section 14.4, `ExecCalc_ArmorPenetration`:**

```typescript
if (RandomFloat() < critChance) {
  damage *= critDamage;
```

In a server-authoritative model, `RandomFloat()` runs on the server, which is fine for authority. But clients that predict ability outcomes (Section 13.4) will call `RandomFloat()` independently. Unless both sides use a shared, seeded RNG that advances deterministically with game state, the client's critical hit prediction will be wrong ~50% of the time at `critChance = 0.5`.

The spec must address deterministic random number generation for predicted outcomes. Options include:
- Seed the RNG from a server-provided value embedded in the prediction key
- Document that random ExecutionCalcs cannot be predicted (the prediction aborts to server-authority)
- Define a `PredictedRNG` interface that implementations must provide

This is a real and common bug in networked ability systems. The spec has a responsibility to address it.

### 2.7 SetByCaller Has No Missing-Key Semantics

**Section 9.4.2:**

When a `SetByCaller` magnitude is defined but the caller forgets to call `spec.SetByCallerMagnitude("Damage.Amount", value)`, what happens? The spec is silent. A zero default? A no-op? A runtime error?

In production, missing SetByCaller keys cause silent zero-damage hits that are notoriously hard to debug. The spec should mandate:
- Implementations MUST warn (SHOULD be a hard error in debug builds) when a SetByCaller magnitude is missing at application time
- Default behavior (zero, no-op, or error) must be specified

### 2.8 No Serialization Protocol for Active Effects

AttributeSets are described as "serialization boundaries" (Section 6.1) but no serialization protocol is defined for active effects. Specifically:

- **HasDuration effects:** How is remaining duration serialized? As absolute timestamp or remaining seconds?
- **Infinite effects:** How are they distinguished from "intended to be infinite" vs "never properly cleaned up"?
- **Periodic effects:** Where in the period is execution when saved? Does it re-execute on load?
- **Effect stacks:** How are RunInSequence queued instances serialized?

Without this, "save anywhere" functionality in single-player games, and reconnection-to-server in multiplayer, both require bespoke solutions that may diverge across implementations. This undermines the "universal" claim.

---

## Part III — Design Concerns and Missed Opportunities

### 3.1 The Attribute Formula Needs a Priority System for Real Games

The current formula aggregates all modifiers of the same type into flat sums and products. Real games need modifier priority/ordering. Examples from shipped titles:

- **Diablo 4:** "Vulnerable" multiplier applies after all other damage buckets. It is not interchangeable with other multiplicative modifiers.
- **Path of Exile:** Modifier order matters for "more" vs "increased" — these are semantically the same `Multiply` operation in UGAS's model but produce different results depending on grouping.
- **World of Warcraft:** Some haste effects stack multiplicatively with each other; others stack additively.

The spec's formula is mathematically clean but collapses all multiplications into a single product `Πm_k`. Real games need at least a `Channel` system (referenced but undefined) that allows modifiers to be grouped into named buckets that combine differently. The Diablo-style damage bucket example in Section 15.3 works around this with an `ExecutionCalculation`, but the base formula doesn't support it natively.

**Recommendation:** Define `Channel` on `Modifier` and specify that modifiers in different channels multiply against each other while modifiers in the same channel add together. This is the "bucket" design that prevents linear power creep.

### 3.2 Tag Count Semantics Are Underspecified

**Section 7.6:**

```yaml
AllowMultiple: boolean  # Can multiple instances exist? (default: false)
```

`AllowMultiple: true` allows multiple instances of the same tag — but what does this mean for queries? If `State.Debuff.Stunned` has count=2 (applied by two different effects), does `RemoveTag` decrement the count or remove all instances? Does `MatchesTag` return true at count=0 if `AllowMultiple` is set?

This needs a full reference-counting semantic definition. The common correct behavior is:
- Tags are reference-counted
- `AddTag` increments the count
- `RemoveTag` decrements the count, removing only when count reaches zero
- All query operations treat count > 0 as "tag is present"

Without this, removing one stun effect accidentally unstuns a target that should remain stunned from a second concurrent stun effect.

### 3.3 Ability Cancellation During Validation Is a Race Condition

**Section 8.2 lifecycle:**

The `Activating (Validating)` state runs synchronous checks (tags, cost, cooldown). But what if an ability requires an asynchronous validation? For example:

- Server-side anti-cheat confirmation
- Resource availability check against a remote inventory service
- Multi-step authentication for premium consumable

The spec assumes activation validation is instant and synchronous. In a pure server-authoritative model this is fine, but it breaks down when the spec also mandates client-side prediction. The client predicts success locally (synchronously), but the server may reject it after async validation. There is no state in the lifecycle machine for "validation pending" between `Activating` and `Commit`.

### 3.4 Task Tick Budget Is Not Defined

**Section 10.3:**

Spatial tasks (`WaitOverlap`, `WaitForTarget`) implicitly require per-frame physics queries. A complex ability with 5 concurrent spatial tasks across 100 simultaneous actors is 500 physics queries per frame. There is no mechanism for:

- Per-task tick rate throttling (e.g., "check every 100ms instead of every frame")
- Task priority/budget system
- Profiling hooks to identify expensive tasks

For a spec targeting both small indie games and large-scale multiplayer titles, this needs at least a SHOULD-level recommendation on tick budgeting.

### 3.5 Effect Application Authorization

`ApplyGameplayEffectToTarget(target, spec)` allows any GC to apply effects to any other GC. In a multiplayer game, this is a security surface: a compromised or exploited client could attempt to apply effects to arbitrary targets. The spec has no mention of:

- Server-side validation that the instigator GC is authorized to affect the target GC
- Capability/permission system for inter-GC effect application
- Distinction between client-requested and server-initiated effect application

At minimum, the spec should state that in networked environments, `ApplyGameplayEffectToTarget` called from a client MUST be validated server-side before execution.

### 3.6 "PGCalCase" Is a Typo

**Section 7.1:**

> "Each segment MUST use PGCalCase"

This should be `PascalCase`. A minor issue but notable in a formal spec document.

### 3.7 The AI World Model Claim Needs to Be Scoped or Substantiated

**Section 1.1:**

> "...next-generation generative world models such as Google Genie"

The spec repeatedly claims to target AI-generated environments. This is a bold claim that requires justification:

- Neural network inference is fundamentally non-deterministic across hardware vendors and driver versions. The spec's determinism requirements are incompatible with this unless the GC runs in a separate deterministic simulation layer alongside the generative model.
- "Client-side prediction" assumes a deterministic simulation that can be rolled back and replayed. A generative world model doesn't have this property.
- What does "network replication" mean when the "server" is a latent diffusion model?

This is forward-looking and philosophically interesting, but at v1.0, the AI world model target is more marketing than technical specification. I'd recommend either removing it or adding a dedicated appendix that honestly outlines the open problems and constraints for that use case.

---

## Part IV — Minor Issues

| # | Location | Issue |
|---|----------|-------|
| 1 | §4.4 | Interface method named `GetAbilitySystemComponent()` returning `AbilitySystemComponent` — naming inconsistency with "GC" (Gameplay Controller) terminology used everywhere else |
| 2 | §8.1 | `EndAbility(wGCancelled: boolean)` — the `wGC` prefix appears to be an artifact of Unreal's `bWasCancelled` naming convention. In an engine-agnostic spec, this should simply be `wasCancelled: boolean` |
| 3 | §9.6 | `RunInSequence` use case lists "crowd control chains" but gives no example of how a second stun Effect knows when the first expired to begin its own timer. The mechanism needs elaboration. |
| 4 | §13.6 | Recommending 60-100 Hz replication for player characters is accurate for LAN/low-latency scenarios. High-latency or mobile contexts should have explicit guidance. |
| 5 | §14.3 | `OnJumpReleased` checks `VerticalVelocity > 0` to determine if the jump should be cut short. This is simulation state, not GAS state — it correctly demonstrates the Avatar/physics relationship but the check should be via an Attribute, not a direct physics query. |
| 6 | §15.4 | The 2048 undo system captures full state snapshots rather than using the Effect history for rollback. This undermines the "audit trail" benefit of the Effect layer. A proper undo system would store applied Effect specs and reverse them in order. |
| 7 | Appendix B | Schema references link to `raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/` — these are `v1.0` hardcoded paths. A spec that evolves will need versioned schema URLs with a stability guarantee. |

---

## Part V — Overall Assessment

### Is UGAS an interesting project?

**Yes. Unambiguously yes.**

The game industry lacks an open standard for gameplay ability systems. Every engine reinvents the same wheel: Unreal has GAS (powerful but underdocumented and Unreal-specific), Unity has a fragmented landscape of community implementations, Godot has plugins, and every proprietary engine has its own bespoke system. There is no shared vocabulary, no portable design format, no way to describe a gameplay mechanic in a way that a designer at a Unity studio can hand off to a developer at a Godot studio.

UGAS is attempting to create that shared vocabulary. The YAML schemas are the real gem here — they're the beginning of a portable, engine-agnostic gameplay data format. If those schemas stabilize and gain tooling support (editors, validators, importers for major engines), that alone would be valuable to the industry.

The spec is also a genuinely good learning resource. The case studies, the execution policy diagrams, the tag inheritance explanation — these are clear and well-written. As an educational document for developers new to data-driven ability systems, UGAS v1.0 is better than most of the existing documentation on UE4 GAS.

### What needs to happen for v1.1?

**Must fix (blocks implementations from being correct):**
1. Clarify `a_i` vs `b_l` distinction in the modifier formula (or remove `b_l`)
2. Define Override modifier conflict resolution
3. Specify SetByCaller missing-key behavior
4. Define Loose Tag replication semantics (or prohibit them)
5. Add basic serialization requirements for active effects

**Should fix (will cause divergent implementations):**
6. Define `Channel` on `Modifier` formally
7. Specify tag reference counting semantics for `AllowMultiple`
8. Address deterministic RNG for predicted ExecutionCalcs
9. Scope or remove the AI world model claims
10. Fix the "PGCalCase" typo

**Nice to have for v2.0:**
- Formal networking annex with prediction window bounds
- Task tick budget recommendations
- Effect application authorization model
- Savegame/serialization protocol

### Final Word

UGAS is the right idea at the right time. The architecture is sound, the case studies are practical, and the ambition is admirable. With targeted fixes to the critical issues, a reference implementation for one major engine, and a validation test suite for the schemas, this could become a genuine industry standard.

Ship it — but call it v0.9, not v1.0, until the networking model is solid.

---

*"The right way to think about this is: every time a programmer has to figure out from scratch how to implement a damage-over-time system that interacts correctly with armor, shields, buffs, and network prediction, that's engineering time that should have gone into making the game better. UGAS is trying to solve that. It's worth getting right."*
