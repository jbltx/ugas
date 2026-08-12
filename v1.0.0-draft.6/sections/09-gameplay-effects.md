## 9. Gameplay Effects

### 9.1 Effect Structure

A Gameplay Effect defines a modification to an Actor’s state. Effects are data-only definitions that SHOULD NOT be subclassed.

``` typescript
struct GameplayEffect {
  /** Unique identifier */
  Name: string;

  /** Duration behavior */
  DurationPolicy: DurationPolicy;

  /** Duration value (if applicable) */
  Duration?: MagnitudeDefinition;

  /** Periodic execution settings */
  Period?: PeriodicSettings;

  /** Attribute modifications */
  Modifiers: Modifier[];

  /** Complex calculations */
  Executions: ExecutionCalculation[];

  /** Tags granted while active */
  GrantedTags: Tag[];

  /** Tags required on target for application */
  ApplicationRequiredTags: Tag[];

  /** Abilities granted while active */
  GrantedAbilities: AbilityGrant[];

  /** Execution policy for multiple instances */
  ExecutionPolicy: ExecutionPolicy;

  /**
   * Override conflict resolution priority.
   * When multiple active effects apply an Override modifier to the same
   * Attribute, the effect with the highest Priority value wins.
   * On equal Priority, last-applied wins (LIFO).
   * Defaults to 0. Negative values are valid.
   */
  Priority: integer;

  /** Gameplay cue tags */
  GameplayCues: Tag[];
}
```

### 9.2 Duration Policies

| Policy        | Base Value | Current Value | Persistence               |
|---------------|------------|---------------|---------------------------|
| `Instant`     | Modified   | Recalculated  | Permanent change          |
| `HasDuration` | Unchanged  | Modified      | Temporary (until expiry)  |
| `Infinite`    | Unchanged  | Modified      | Temporary (until removed) |

Instant Effects  
Modify the Base Value immediately and permanently. The Effect does not remain "active" after application. Classic examples: damage, healing, permanent stat increases.

HasDuration Effects  
Modify the Current Value for a specified duration. When the timer expires, the modifier is removed and the attribute reverts. Classic examples: buffs, debuffs, temporary bonuses.

Infinite Effects  
Modify the Current Value indefinitely until explicitly removed. Classic examples: passive auras, equipment bonuses, persistent status effects.

<div class="note">

`HasDuration` timers and periodic intervals (§9.3) advance in the runtime’s **tick time** — the elapsed amount passed to each update — not in any built-in notion of "turn." A **turn- or phase-based title** (a card battler, a tactics grid) represents each turn as a discrete advance: it ticks the system by one fixed turn-step at end-of-turn — so a status authored to last `N` expires after `N` turn-steps — and it does **not** **also** advance those same effects with per-frame time, which would age turn-scoped statuses mid-turn. In other words the **unit** of a duration is whatever unit the title advances the runtime by: real-time titles pass seconds; turn-based titles pass one step per turn. This keeps the effect model usable for both without a separate "turns" concept, but the title MUST drive a single, consistent clock.

</div>

### 9.3 Periodic Execution

Effects with duration (HasDuration or Infinite) MAY execute periodically:

``` typescript
struct PeriodicSettings {
  /** Time between executions */
  Period: float;

  /** Execute immediately on application? */
  ExecuteOnApplication: boolean;
}
```

Periodic effects behave like repeated Instant effects within a duration container:

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.6/schemas/gameplay_effect.json
Name: "GE_Poison"
DurationPolicy: HasDuration
Duration:
  Type: ScalableFloat
  Value: 10.0
Period:
  Period: 1.0
  ExecuteOnApplication: false
Modifiers:
  - Attribute: "Health"
    Operation: Add
    Magnitude:
      Type: ScalableFloat
      Value: -5.0  # 5 damage per second
```

<div class="note">

<div class="title">

Periodic execution over a clamped Attribute

</div>

Each periodic execution is an independent Instant application to the Base Value (§5.2) and is therefore subject to the Attribute’s bounds (§5.4) **on its own**. When more than one periodic (or Instant) Effect modifies the same clamped Attribute, the bound is applied **after each execution** — never once over their net sum. At a bound the result is consequently order-sensitive and generally differs from summing the deltas and clamping once.

*Example:* `Health` is clamped to `[0, 100]` and currently `100`. In one tick a `+10` regeneration and a `−30` poison both execute. Regen first: `min(100, 100+10)=100`, then `100−30=70`. Poison first: `100−30=70`, then `min(100, 70+10)=80`. Summing-then-clamping would give `min(100, 100+10−30)=80`. The three disagree only because a bound is reached mid-sequence.

Implementations SHOULD execute a tick’s due periodic executions in a deterministic, documented order so that a scenario is reproducible. To make opposing periodics commute at a bound, model them as a single net-magnitude periodic Effect, or leave the Attribute unclamped and clamp on read.

</div>

### 9.4 Modifier Specification

#### 9.4.1 Operations

| Operation  | Semantics                   | Pipeline Step      | Magnitude convention                                                                                                                                                               |
|------------|-----------------------------|--------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Add`      | Pre-multiply flat additive  | Step 2             | Absolute delta (e.g., `+10` adds 10)                                                                                                                                               |
| `AddPost`  | Post-multiply flat additive | Step 5 (very rare) | Absolute delta                                                                                                                                                                     |
| `Multiply` | Channel-aggregated bonus    | Step 4             | Signed bonus: `+0.25` = +25%, `−0.25` = −25%. Modifiers in the same `Channel` add their bonuses; channel effective factors multiply across channels. See §5.3 Channel Aggregation. |
| `Override` | Replace value               | Step 6             | Absolute replacement value                                                                                                                                                         |

> *Note:* There is no `Divide` operation. A 50% reduction is expressed as `Multiply` with magnitude `−0.5` (i.e., a −50% penalty). This eliminates the divide-by-zero edge case.

``` typescript
struct Modifier {
  /** Target attribute */
  Attribute: AttributeReference;

  /**
   * Modification operation.
   * - Add:      Pre-multiply flat additive (pipeline step 2)
   * - Multiply: Signed bonus, channel-aggregated as (1 + Σm) (pipeline step 4)
   * - AddPost:  Post-multiply flat additive (pipeline step 5; very rare)
   * - Override: Replace the computed value entirely (pipeline step 6)
   */
  Operation: ModifierOperation;

  /** Magnitude calculation */
  Magnitude: MagnitudeDefinition;

  /**
   * Optional aggregation channel name for `Multiply` modifiers.
   *
   * Semantics (see §5.3 Channel Aggregation for the full formula):
   * - Modifiers with the SAME Channel add their bonuses together before
   *   the channel's effective factor (1 + sum) is computed.
   * - Modifiers in DIFFERENT Channels produce independent factors that
   *   multiply against each other.
   * - A modifier with no Channel is in its own implicit singleton channel,
   *   contributing independently.
   *
   * Example — two gear bonuses and one legendary power:
   *   GE_FireDmg:    Multiply +0.20 Channel:"DamageBonuses"
   *   GE_EliteDmg:   Multiply +0.15 Channel:"DamageBonuses"
   *   GE_Legendary:  Multiply +0.50 Channel:"LegendaryPowers"
   *   → effective factor = (1 + 0.20 + 0.15) × (1 + 0.50) = 1.35 × 1.50 = 2.025
   *   vs. naive stacking: 1.20 × 1.15 × 1.50 = 2.07  (higher, causes power creep)
   *
   * Ignored on `Add`, `AddPost`, and `Override` modifiers.
   */
  Channel?: string;
}
```

#### 9.4.2 Magnitude Calculation Types

ScalableFloat  
Static or curve-based value.

``` yaml
Magnitude:
  Type: ScalableFloat
  Value: 25.0                 # Static value
  # OR
  Curve: "DamageCurve"        # Curve lookup
  CurveInput: "Level"         # Curve x-axis
```

AttributeBased  
Derived from another attribute.

``` yaml
Magnitude:
  Type: AttributeBased
  BackingAttribute: "Strength"
  Source: Target              # Source | Target
  Coefficient: 1.5
  PreMultiplyAdditive: 0.0
  PostMultiplyAdditive: 10.0
  # Result = (AttributeValue + PreAdd) * Coefficient + PostAdd
```

CustomCalculation  
Custom Modifier Magnitude Calculator (MMC).

``` yaml
Magnitude:
  Type: CustomCalculation
  CalculatorClass: "MMC_CriticalDamage"
```

SetByCaller  
Runtime-provided value via EffectSpec.

``` yaml
Magnitude:
  Type: SetByCaller
  DataTag: "Damage.Base"      # Lookup key
```

Usage:

``` typescript
const spec = MakeOutgoingSpec(damageEffect, level);
spec.SetByCallerMagnitude("Damage.Base", calculatedDamage);
ApplyGameplayEffectToTarget(target, spec);
```

### 9.5 Execution Calculations

Execution Calculations provide full access to source and target attributes for complex, multi-attribute logic.

``` typescript
abstract class ExecutionCalculation {
  /** Attributes to capture from source */
  SourceCaptureDefinitions: AttributeCapture[];

  /** Attributes to capture from target */
  TargetCaptureDefinitions: AttributeCapture[];

  /**
   * Whether this calculation may run inside a client-side prediction
   * (§13.4). Defaults to `true`. A calculation that consumes randomness
   * MUST either draw it from `context.RNG` (the deterministic, seeded
   * stream — see "Randomness in Execution Calculations" below) so it
   * stays predictable, or set this to `false` to declare that it
   * requires server authority and cannot be predicted. When `false`,
   * the activation that triggers this calculation MUST abort prediction
   * and fall back to server authority (§13.8.2) for the random outcome.
   */
  Predictable: boolean;  // default: true

  /** Perform the calculation */
  abstract Execute(
    source: CapturedAttributes,
    target: CapturedAttributes,
    context: EffectContext
  ): ModifierResult[];
}

struct AttributeCapture {
  Attribute: AttributeReference;
  CaptureTime: CaptureTime;  // OnApplication | OnExecution
}
```

*Capture vs Snapshot Semantics*

- `OnApplication`: Attribute value is captured when Effect is first applied

- `OnExecution`: Attribute value is captured each time Effect executes

Example: Armor Penetration Calculation

``` typescript
class ExecCalc_PhysicalDamage extends ExecutionCalculation {
  SourceCaptureDefinitions = [
    { Attribute: "AttackPower", CaptureTime: OnExecution },
    { Attribute: "ArmorPenetration", CaptureTime: OnExecution }
  ];

  TargetCaptureDefinitions = [
    { Attribute: "Armor", CaptureTime: OnExecution }
  ];

  Execute(source, target, context): ModifierResult[] {
    const attackPower = source.Get("AttackPower");
    const armorPen = source.Get("ArmorPenetration");
    const targetArmor = target.Get("Armor");

    const effectiveArmor = Math.max(0, targetArmor - armorPen);
    const damageReduction = effectiveArmor / (effectiveArmor + 100);
    const finalDamage = attackPower * (1 - damageReduction);

    return [{
      Attribute: "Health",
      Operation: Add,
      Magnitude: -finalDamage
    }];
  }
}
```

*Randomness in Execution Calculations (Normative)*

Execution Calculations frequently make randomized decisions — a critical-hit roll, a random damage spread, a proc chance. Because the same calculation runs on a predicting client (§13.4) and on the authoritative server, naive randomness drawn from an ambient global (e.g. a bare `RandomFloat()`) will diverge: at `CriticalChance = 0.5` the client mispredicts the crit roughly half the time, forcing a visible rollback (§13.5) on every disagreement. The following rules make randomness in Execution Calculations deterministic and reproducible across client and server.

1.  **Seeded, deterministic stream.** Any randomness consumed during a **predicted** Execution Calculation MUST be drawn from the deterministic RNG stream exposed as `context.RNG`. That stream MUST be seeded from the activation’s `PredictionKey.Seed` (§13.8.1) and advanced deterministically, so that the predicting client and the authoritative server, starting from the same server-coordinated seed, produce identical results and no rollback is caused by RNG drift alone.

2.  **No ambient randomness.** Implementations MUST NOT consume gameplay-affecting randomness during prediction from any source other than `context.RNG` (this mirrors the prohibition in §13.8.1). A bare `RandomFloat()`-style global, a thread-local PRNG, wall-clock time, or any other non-seeded source MUST NOT be used for a roll that influences gameplay state.

3.  **Stream positioning (reproducibility).** `context.RNG` MUST be positioned per the `(Sub, draw index)` scheme of §13.8.1: each activation under a prediction `Base` consumes a disjoint sub-stream selected by its `PredictionKey.Sub`, and successive draws within one `Execute()` advance a monotonic draw index. Consequently, the *n*-th draw of a given calculation under a given `(Base, Sub)` is reproducible — re-running `Execute()` during reconciliation replay (§13.5) yields the same sequence. Implementations MUST NOT make the result depend on draw *ordering across* calculations that is not itself deterministic.

4.  **Non-predictable opt-out (escape hatch).** An Execution Calculation that genuinely requires non-reproducible or server-only randomness — for example, a roll that MUST NOT be inferable client-side, or one seeded from a source the client cannot reproduce — MUST declare itself non-predictable by setting `Predictable = false` (equivalently, carrying a `RequiresServerAuthority` marker). When such a calculation participates in an activation, that activation MUST abort prediction and fall back to awaiting server authority for the random outcome, exactly as in the prediction-window fallback of §13.8.2; the authoritative result then replicates normally. This is the second option called out by issue \#5: random Execution Calculations that cannot be predicted abort to server authority rather than mispredict.

5.  **Single-player / non-networked.** The same `context.RNG` path is used when there is no server: the stream is seeded from a local source (e.g. a per-session or per-activation seed) instead of `PredictionKey.Seed`. No `RandomFloat()`-style ambient global is permitted for gameplay-affecting rolls even offline, so that calculation behavior is identical in shape across networked and standalone play and remains reproducible for replays and tests.

`context.RNG` is a small `DeterministicRNG` interface that conforming implementations MUST provide on the Execution Calculation `context`:

``` typescript
interface DeterministicRNG {
  /** Next uniform float in [0, 1). Advances the stream by one draw. */
  NextFloat(): float;

  /**
   * Next integer in [minInclusive, maxExclusive). Advances the stream by
   * one draw. Derived deterministically from the same sequence as
   * NextFloat(), so a given draw index yields a stable value.
   */
  NextInt(minInclusive: int, maxExclusive: int): int;
}
```

<div class="note">

The seed itself is owned by the networking layer, not by the Execution Calculation: §13.8.1 defines `PredictionKey.Seed` as server-coordinated and forbids client-chosen seeds (so a client cannot bias a predicted crit). §9.5 only defines the *consumption* contract — how a calculation draws from that seed via `context.RNG`. A calculation MUST NOT read `PredictionKey.Seed` directly or reconstruct its own RNG; it MUST go through `context.RNG` so stream positioning stays consistent with §13.8.1.

</div>

### 9.6 Execution Policies

Execution Policies define how multiple instances of the same Effect interact. This model replaces traditional "stacking" concepts with clearer behavioral semantics.

| Policy          | Behavior                                                                |
|-----------------|-------------------------------------------------------------------------|
| `RunInParallel` | All instances execute simultaneously; magnitude stacks N times          |
| `RunInSequence` | Instances queue; executes one after another                             |
| `RunInMerge`    | Single logical instance; durations merge (earliest start to latest end) |

#### RunInParallel

Each instance of the effect runs simultaneously, applying N times the magnitude.

    Time ───────────────────────────────────▶
    Instance 1: ████████████████
    Instance 2:     ████████████████
    Instance 3:         ████████████████

    Combined magnitude at t=5: 3× base

Use case: Stackable damage-over-time effects, multiple buff sources

#### RunInSequence

Instances queue and execute one after another.

    Time ───────────────────────────────────▶
    Instance 1: ████████████████
    Instance 2:                 ████████████████
    Instance 3:                                 ████████████████

Use case: Channeled effects, crowd control chains

*Chaining mechanism:* The GC owns the queue for each `RunInSequence` effect class. When the active instance’s duration expires (or it is manually removed), the GC automatically dequeues and begins the next instance, resetting the duration timer. Ability authors do not manage this transition; applying the same effect class while one is already active is sufficient to enqueue. The `OnEffectApplied` / `OnEffectRemoved` delegates fire for each instance individually, so callers can observe the moment one stun ends and the next begins.

#### RunInMerge

Multiple applications merge into a single logical instance with combined duration.

    Time ───────────────────────────────────▶
    Instance 1: ████████████████
    Instance 2:     ████████████████
    Instance 3:         ████████████████

    Merged:     ████████████████████████████

Use case: Buff refreshing, grace periods

### 9.7 Tag Grants

Effects MAY grant Tags while active:

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.6/schemas/gameplay_effect.json
Name: "GE_Burning"
DurationPolicy: HasDuration
Duration:
  Type: ScalableFloat
  Value: 5.0
GrantedTags:
  - "State.Debuff.Burning"
  - "State.Element.Fire"
Modifiers:
  - Attribute: "Health"
    Operation: Add
    Magnitude:
      Type: ScalableFloat
      Value: -10.0
```

When the Effect is applied: 1. `AddTag` is called for each Granted Tag — grant counts increment 2. `OnTagChanged` is dispatched *only* for tags whose count transitions `0 → 1` 3. Gameplay Cues are triggered only on that same `0 → 1` transition

When the Effect is removed (duration expires or manual removal): 1. `RemoveTag` is called for each Granted Tag — grant counts decrement 2. `OnTagChanged` is dispatched *only* for tags whose count transitions `1 → 0` 3. Looping Gameplay Cues are stopped only on that same `1 → 0` transition

*Consequence for concurrent Effects:* if two Effects both grant `State.Debuff.Burning`, the tag’s count reaches 2. Removing the first Effect decrements to 1 — no event, no Cue change, the character remains visually on fire. Only removing the second Effect decrements to 0, dispatches `OnTagChanged`, and stops the looping Cue. This is the correct behaviour and falls out automatically from ref-counting.

### 9.8 Ability Grants

Effects MAY grant Abilities while active:

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.6/schemas/gameplay_effect.json
Name: "GE_FireSword_Equipped"
DurationPolicy: Infinite
GrantedAbilities:
  - AbilityClass: "GA_FlameStrike"
    Level: 1
    InputID: "Ability.Weapon.Special"
    RemoveOnEffectRemoval: true
```

This pattern enables equipment-based abilities where unequipping the item removes the Effect and consequently the granted Ability.

### 9.9 EffectSpec and EffectContext

#### EffectSpec Structure

``` typescript
struct EffectSpec {
  /** Reference to effect definition */
  EffectClass: GameplayEffectClass;

  /** Level for magnitude calculations */
  Level: number;

  /** Application context */
  Context: EffectContextHandle;

  /** SetByCaller magnitude overrides */
  SetByCallerMagnitudes: Map<string, float>;

  /** Duration override (if any) */
  DurationOverride?: float;

  /** Period override (if any) */
  PeriodOverride?: float;
}
```

#### EffectContext Structure

``` typescript
struct EffectContext {
  /** GC that created this effect */
  InstigatorGC: GameplayController;

  /** Actor that caused this effect */
  EffectCauser: Actor;

  /** Ability that applied this effect (if any) */
  SourceAbility?: GameplayAbility;

  /** Object that was the origin (projectile, etc.) */
  SourceObject?: Object;

  /** Hit result for physics-based effects */
  HitResult?: HitResult;

  /** World location for positional effects */
  WorldOrigin?: Vector3;

  /**
   * Deterministic, seeded RNG for any randomness consumed by an Execution
   * Calculation (§9.5). During prediction this stream is seeded from
   * `PredictionKey.Seed` (§13.8.1) and positioned per the (Sub, draw index)
   * scheme so client and server agree; offline it is seeded from a local
   * source. Gameplay-affecting rolls MUST use this rather than an ambient
   * global. See "Randomness in Execution Calculations" in §9.5.
   */
  RNG: DeterministicRNG;
}
```

#### Handle Patterns

Handles provide lightweight references to specs and active effects:

``` typescript
struct EffectSpecHandle {
  Data: SharedPtr<EffectSpec>;
}

struct ActiveEffectHandle {
  Handle: number;
  bPassedFiltersAndWasExecuted: boolean;
}
```

### 9.10 Schema Definition

``` yaml
# GameplayEffect Definition Schema
type: object
required:
  - Name
  - DurationPolicy
properties:
  Name:
    type: string
    description: Unique effect identifier
  DurationPolicy:
    type: string
    enum:
      - Instant
      - HasDuration
      - Infinite
  Duration:
    type: object
    properties:
      Type:
        type: string
        enum:
          - ScalableFloat
          - AttributeBased
          - SetByCaller
      Value:
        type: number
  Period:
    type: object
    properties:
      Period:
        type: number
        minimum: 0
      ExecuteOnApplication:
        type: boolean
        default: false
  ExecutionPolicy:
    type: string
    enum:
      - RunInParallel
      - RunInSequence
      - RunInMerge
    default: RunInParallel
  Priority:
    type: integer
    default: 0
    description: Override conflict priority. Highest value wins when multiple Override modifiers target the same Attribute. Equal priority resolves by last-applied (LIFO).
  Modifiers:
    type: array
    items:
      type: object
      required:
        - Attribute
        - Operation
        - Magnitude
      properties:
        Attribute:
          type: string
        Operation:
          type: string
          enum:
            - Add
            - AddPost
            - Multiply
            - Override
        Magnitude:
          type: object
        Channel:
          type: string
          description: >
            Aggregation channel for Multiply modifiers. Modifiers sharing a
            Channel add their bonuses; channels multiply against each other.
            Omit to treat this modifier as an isolated singleton channel.
            Ignored on Add, AddPost, and Override operations.
  GrantedTags:
    type: array
    items:
      type: string
  GrantedAbilities:
    type: array
    items:
      type: object
      properties:
        AbilityClass:
          type: string
        Level:
          type: integer
          default: 1
        InputID:
          type: string
        RemoveOnEffectRemoval:
          type: boolean
          default: true
  GameplayCues:
    type: array
    items:
      type: string
```

# Part III: Asynchronous Execution
