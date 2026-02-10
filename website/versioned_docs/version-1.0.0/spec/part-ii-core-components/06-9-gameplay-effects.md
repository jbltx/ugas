---
title: "9. Gameplay Effects"
sidebar_position: 6
---

### 9.1 Effect Structure

A Gameplay Effect defines a modification to an Actor's state. Effects are data-only definitions that SHOULD NOT be subclassed.

```typescript
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

  /** Gameplay cue tags */
  GameplayCues: Tag[];
}
```

### 9.2 Duration Policies

| Policy | Base Value | Current Value | Persistence |
|--------|------------|---------------|-------------|
| `Instant` | Modified | Recalculated | Permanent change |
| `HasDuration` | Unchanged | Modified | Temporary (until expiry) |
| `Infinite` | Unchanged | Modified | Temporary (until removed) |

**Instant Effects**
: Modify the Base Value immediately and permanently. The Effect does not remain "active" after application. Classic examples: damage, healing, permanent stat increases.

**HasDuration Effects**
: Modify the Current Value for a specified duration. When the timer expires, the modifier is removed and the attribute reverts. Classic examples: buffs, debuffs, temporary bonuses.

**Infinite Effects**
: Modify the Current Value indefinitely until explicitly removed. Classic examples: passive auras, equipment bonuses, persistent status effects.

### 9.3 Periodic Execution

Effects with duration (HasDuration or Infinite) MAY execute periodically:

```typescript
struct PeriodicSettings {
  /** Time between executions */
  Period: float;

  /** Execute immediately on application? */
  ExecuteOnApplication: boolean;
}
```

Periodic effects behave like repeated Instant effects within a duration container:

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/gameplay_effect.json
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

### 9.4 Modifier Specification

#### 9.4.1 Operations

| Operation | Semantics | Formula |
|-----------|-----------|---------|
| `Add` | Flat additive | `attr += magnitude` |
| `Multiply` | Multiplicative factor | `attr *= magnitude` |
| `Divide` | Division factor | `attr /= magnitude` |
| `Override` | Replace value | `attr = magnitude` |

```typescript
struct Modifier {
  /** Target attribute */
  Attribute: AttributeReference;

  /** Modification operation */
  Operation: ModifierOperation;

  /** Magnitude calculation */
  Magnitude: MagnitudeDefinition;

  /** Channel for modifier aggregation */
  Channel?: string;
}
```

#### 9.4.2 Magnitude Calculation Types

**ScalableFloat**
: Static or curve-based value.

```yaml
Magnitude:
  Type: ScalableFloat
  Value: 25.0                 # Static value
  # OR
  Curve: "DamageCurve"        # Curve lookup
  CurveInput: "Level"         # Curve x-axis
```

**AttributeBased**
: Derived from another attribute.

```yaml
Magnitude:
  Type: AttributeBased
  BackingAttribute: "Strength"
  Source: Target              # Source | Target
  Coefficient: 1.5
  PreMultiplyAdditive: 0.0
  PostMultiplyAdditive: 10.0
  # Result = (AttributeValue + PreAdd) * Coefficient + PostAdd
```

**CustomCalculation**
: Custom Modifier Magnitude Calculator (MMC).

```yaml
Magnitude:
  Type: CustomCalculation
  CalculatorClass: "MMC_CriticalDamage"
```

**SetByCaller**
: Runtime-provided value via EffectSpec.

```yaml
Magnitude:
  Type: SetByCaller
  DataTag: "Damage.Base"      # Lookup key
```

Usage:
```typescript
const spec = MakeOutgoingSpec(damageEffect, level);
spec.SetByCallerMagnitude("Damage.Base", calculatedDamage);
ApplyGameplayEffectToTarget(target, spec);
```

### 9.5 Execution Calculations

Execution Calculations provide full access to source and target attributes for complex, multi-attribute logic.

```typescript
abstract class ExecutionCalculation {
  /** Attributes to capture from source */
  SourceCaptureDefinitions: AttributeCapture[];

  /** Attributes to capture from target */
  TargetCaptureDefinitions: AttributeCapture[];

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

**Capture vs Snapshot Semantics**

- `OnApplication`: Attribute value is captured when Effect is first applied
- `OnExecution`: Attribute value is captured each time Effect executes

Example: Armor Penetration Calculation

```typescript
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

### 9.6 Execution Policies

Execution Policies define how multiple instances of the same Effect interact. This model replaces traditional "stacking" concepts with clearer behavioral semantics.

| Policy | Behavior |
|--------|----------|
| `RunInParallel` | All instances execute simultaneously; magnitude stacks N times |
| `RunInSequence` | Instances queue; executes one after another |
| `RunInMerge` | Single logical instance; durations merge (earliest start to latest end) |

#### RunInParallel

Each instance of the effect runs simultaneously, applying N times the magnitude.

```
Time ───────────────────────────────────▶
Instance 1: ████████████████
Instance 2:     ████████████████
Instance 3:         ████████████████

Combined magnitude at t=5: 3× base
```

Use case: Stackable damage-over-time effects, multiple buff sources

#### RunInSequence

Instances queue and execute one after another.

```
Time ───────────────────────────────────▶
Instance 1: ████████████████
Instance 2:                 ████████████████
Instance 3:                                 ████████████████
```

Use case: Channeled effects, crowd control chains

#### RunInMerge

Multiple applications merge into a single logical instance with combined duration.

```
Time ───────────────────────────────────▶
Instance 1: ████████████████
Instance 2:     ████████████████
Instance 3:         ████████████████

Merged:     ████████████████████████████
```

Use case: Buff refreshing, grace periods

### 9.7 Tag Grants

Effects MAY grant Tags while active:

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/gameplay_effect.json
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

When the Effect is applied:
1. Granted Tags are added to target's Tag Container
2. Tag change events are dispatched
3. Relevant Gameplay Cues are triggered

When the Effect is removed (duration expires or manual removal):
1. Granted Tags are removed from target's Tag Container
2. Tag change events are dispatched
3. Looping Gameplay Cues are stopped

### 9.8 Ability Grants

Effects MAY grant Abilities while active:

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/gameplay_effect.json
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

```typescript
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

```typescript
struct EffectContext {
  /** GC that created this effect */
  InstigatorGC: AbilitySystemComponent;

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
}
```

#### Handle Patterns

Handles provide lightweight references to specs and active effects:

```typescript
struct EffectSpecHandle {
  Data: SharedPtr<EffectSpec>;
}

struct ActiveEffectHandle {
  Handle: number;
  bPassedFiltersAndWasExecuted: boolean;
}
```

### 9.10 Schema Definition

```yaml
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
            - Multiply
            - Divide
            - Override
        Magnitude:
          type: object
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

---
