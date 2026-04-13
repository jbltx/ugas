# UGAS Schema Reference

This file contains the canonical schema definitions and examples for all UGAS entity
types. When authoring entity files, always refer to these schemas for field names,
types, and constraints.

## Table of Contents

1. [Attribute](#attribute)
2. [Attribute Set](#attribute-set)
3. [Gameplay Effect](#gameplay-effect)
4. [Gameplay Ability](#gameplay-ability)
5. [Gameplay Tag](#gameplay-tag)
6. [Gameplay Controller](#gameplay-controller)

---

## Attribute

An individual numeric gameplay value with dual-value pattern (Base + Current).

### Schema

```yaml
type: object
required:
  - Name
  - DefaultBaseValue
properties:
  Name:
    type: string
    description: Unique identifier for this attribute
  DefaultBaseValue:
    type: number
    description: Initial base value
  Category:
    type: string
    enum: [Resource, Statistic, Meta]
    default: Statistic
  Clamping:
    type: object
    properties:
      Min:
        oneOf:
          - type: number
          - type: string    # Attribute reference
      Max:
        oneOf:
          - type: number
          - type: string    # Attribute reference
  ReplicationMode:
    type: string
    enum: [None, OwnerOnly, All]
    default: All
  Metadata:
    type: object
    properties:
      DisplayName: { type: string }
      Description: { type: string }
      UICategory: { type: string }
      Icon: { type: string }
```

### Categories

- **Resource** — Consumable values (Health, Mana, Stamina). Typically have Clamping.
- **Statistic** — Derived or passive values (Strength, AttackSpeed). Modify other calculations.
- **Meta** — Internal/system values (DamageDealt, ExperienceGained). Often not displayed to player.

### Example

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/%%UGAS_VERSION%%/schemas/attribute.json
Name: Health
DefaultBaseValue: 100.0
Category: Resource
Clamping:
  Min: 0
  Max: MaxHealth
ReplicationMode: All
Metadata:
  DisplayName: Health Points
  Description: Character's current life force
  UICategory: Vital Stats
  Icon: ui/icons/health.png
```

---

## Attribute Set

A logical grouping of related attributes.

### Schema

```yaml
type: object
required:
  - Name
  - Attributes
properties:
  Name:
    type: string
    description: Unique set identifier
  Dependencies:
    type: array
    items: { type: string }
    description: Required attribute sets
  Attributes:
    type: array
    items:
      # Inline Attribute definition (same fields as standalone Attribute)
      type: object
      required: [Name, DefaultBaseValue]
      properties:
        Name: { type: string }
        DefaultBaseValue: { type: number }
        Category: { type: string, enum: [Resource, Statistic, Meta] }
        Clamping:
          type: object
          properties:
            Min: { oneOf: [{ type: number }, { type: string }] }
            Max: { oneOf: [{ type: number }, { type: string }] }
        ReplicationMode: { type: string, enum: [None, OwnerOnly, All] }
        Metadata:
          type: object
          properties:
            DisplayName: { type: string }
            Description: { type: string }
            UICategory: { type: string }
            Icon: { type: string }
  Metadata:
    type: object
    properties:
      DisplayName: { type: string }
      Description: { type: string }
```

---

## Gameplay Effect

The only authorized mechanism for modifying attributes or tags.

### Schema

```yaml
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
    enum: [Instant, HasDuration, Infinite]
  Duration:
    # MagnitudeDefinition — see below
  Period:
    type: object
    properties:
      Period:
        type: number
        minimum: 0
        description: Time interval for periodic execution
      ExecuteOnApplication:
        type: boolean
        default: false
  ExecutionPolicy:
    type: string
    enum: [RunInParallel, RunInSequence, RunInMerge]
    default: RunInParallel
  Priority:
    type: integer
    default: 0
    description: >
      Override conflict resolution. Higher Priority wins when multiple Override
      modifiers target the same attribute. On equal Priority, last-applied wins.
  Modifiers:
    type: array
    items:
      # Modifier — see below
  Executions:
    type: array
    items:
      type: object
      properties:
        CalculatorClass: { type: string }
  GrantedTags:
    type: array
    items: { type: string }
  ApplicationRequiredTags:
    type: array
    items: { type: string }
  GrantedAbilities:
    type: array
    items:
      type: object
      properties:
        AbilityClass: { type: string }
        Level: { type: integer, default: 1 }
        InputID: { type: string }
        RemoveOnEffectRemoval: { type: boolean, default: true }
  GameplayCues:
    type: array
    items: { type: string }
```

### Modifier

```yaml
type: object
required: [Attribute, Operation, Magnitude]
properties:
  Attribute:
    type: string
    description: Target attribute to modify
  Operation:
    type: string
    enum: [Add, AddPost, Multiply, Override]
    description: >
      Add: pre-multiply flat additive (pipeline step 2).
      AddPost: post-multiply flat additive (pipeline step 7, very rare).
      Multiply: multiplicative factor at step 6 — use reciprocal for reduction
        (e.g., 0.5 to halve).
      Override: replaces computed result at step 8.
  Magnitude:
    # MagnitudeDefinition — see below
  Channel:
    type: string
    description: >
      Named aggregation channel. Same-channel modifiers sum; cross-channel
      modifiers multiply. Used for damage-bucket systems.
```

### MagnitudeDefinition

```yaml
type: object
required: [Type]
properties:
  Type:
    type: string
    enum: [ScalableFloat, AttributeBased, CustomCalculation, SetByCaller]
  Value:
    type: number
    description: Static value for ScalableFloat
  Curve: { type: string }
  CurveInput: { type: string }
  BackingAttribute:
    type: string
    description: Attribute name for AttributeBased magnitude
  Source:
    type: string
    enum: [Source, Target]
    description: Which GC to read the backing attribute from
  Coefficient: { type: number, default: 1 }
  PreMultiplyAdditive: { type: number, default: 0 }
  PostMultiplyAdditive: { type: number, default: 0 }
  CalculatorClass: { type: string }
  DataTag:
    type: string
    description: Tag for SetByCaller data lookup
```

### Duration Policy Guide

| Policy | Modifies | Persistence | Use Case |
|--------|----------|-------------|----------|
| Instant | Base Value | Permanent | Damage, healing, XP gains |
| HasDuration | Current Value | Temporary (reverts) | Buffs, debuffs, DOTs |
| Infinite | Current Value | Until removed | Passives, auras, equipment |

### Example

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/%%UGAS_VERSION%%/schemas/gameplay_effect.json
Name: SimpleDamageEffect
DurationPolicy: Instant
Modifiers:
  - Attribute: Health
    Operation: Add
    Magnitude:
      Type: ScalableFloat
      Value: -25.0
GrantedTags:
  - State.Damaged
GameplayCues:
  - GameplayCue.Character.Damage
```

---

## Gameplay Ability

A self-contained, asynchronous unit of gameplay logic.

### Schema

```yaml
type: object
required:
  - Name
properties:
  Name:
    type: string
  Tags:
    type: object
    properties:
      AbilityTags:
        type: array
        items: { type: string }
        description: Tags that describe this ability
      BlockedByTags:
        type: array
        items: { type: string }
        description: Tags that prevent this ability from running
      BlockAbilitiesWithTags:
        type: array
        items: { type: string }
        description: Block abilities with these tags while active
      CancelAbilitiesWithTags:
        type: array
        items: { type: string }
        description: Cancel abilities with these tags on activation
      ActivationRequiredTags:
        type: array
        items: { type: string }
        description: Tags required on GC to activate
      ActivationBlockedTags:
        type: array
        items: { type: string }
        description: Tags that block activation
      ActivationOwnedTags:
        type: array
        items: { type: string }
        description: Tags granted to GC while active
  Cost:
    type: string
    description: Reference to cost GameplayEffect
  Cooldown:
    type: string
    description: Reference to cooldown GameplayEffect
  Tasks:
    type: array
    items:
      type: object
      required: [Type]
      properties:
        Type:
          type: string
          description: Task type (PlayMontage, WaitGameplayEvent, SpawnProjectile, WaitDelay, WaitInputRelease, WaitTagAdded, WaitTargetData, etc.)
        Params:
          type: object
  Metadata:
    type: object
    properties:
      DisplayName: { type: string }
      Description: { type: string }
      Icon: { type: string }
```

### Example

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/%%UGAS_VERSION%%/schemas/gameplay_ability.json
Name: FireballAbility
Tags:
  AbilityTags:
    - Ability.Magic.Fireball
    - Ability.Offensive
  BlockedByTags:
    - State.Dead
  ActivationRequiredTags:
    - State.CanCast
  ActivationBlockedTags:
    - State.Silenced
    - State.Stunned
    - State.Disarmed.Magic
  ActivationOwnedTags:
    - State.Casting
    - State.Busy
Cost: ManaCostEffect_25
Cooldown: FireballCooldown_5s
Tasks:
  - Type: PlayMontage
    Params:
      MontageToPlay: Anim_CastFireball
      PlayRate: 1.0
  - Type: WaitGameplayEvent
    Params:
      EventTag: Event.Montage.CastPoint
  - Type: SpawnProjectile
    Params:
      ProjectileClass: Projectile_Fireball
      Speed: 2000.0
      Gravity: -980.0
Metadata:
  DisplayName: Fireball
  Description: Launch a ball of fire at the target, dealing damage on impact
  Icon: ui/icons/fireball.png
```

---

## Gameplay Tag

Hierarchical semantic labels for state management and logic gating.

### Schema

```yaml
type: object
properties:
  Tags:
    type: array
    items:
      type: object
      required: [Tag]
      properties:
        Tag:
          type: string
          pattern: "^[A-Z][a-zA-Z0-9]*(\\.[A-Z][a-zA-Z0-9]*)*$"
          description: Hierarchical dot notation (e.g., State.Debuff.Stunned)
        Description: { type: string }
        AllowMultiple:
          type: boolean
          default: false
        DevComment: { type: string }
```

### Query Types

| Query | Behavior |
|-------|----------|
| MatchesTag | True if tag or any child is present |
| MatchesTagExact | True only for the exact leaf tag |
| HasAny | True if any tag from a set matches |
| HasAll | True if all tags from a set match |

### Example

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/%%UGAS_VERSION%%/schemas/gameplay_tag.json
Tags:
  - Tag: State.Alive
    Description: Entity is alive and active
    AllowMultiple: false
  - Tag: State.Dead
    Description: Entity is dead
    AllowMultiple: false
  - Tag: State.Debuff.Stunned
    Description: Entity is stunned and cannot act
    AllowMultiple: false
```

---

## Gameplay Controller

The authoritative state container (the GC, formerly ASC).

### Schema

```yaml
type: object
required: [OwnerActor, AttributeSets]
properties:
  OwnerActor:
    type: object
    properties:
      ActorID: { type: string }
      ActorType: { type: string }
  AvatarActor:
    type: object
    properties:
      ActorID: { type: string }
      ActorType: { type: string }
  AttributeSets:
    type: array
    items:
      type: object
      properties:
        Name: { type: string }
        Attributes:
          type: array
          items:
            type: object
            properties:
              Name: { type: string }
              BaseValue: { type: number }
              CurrentValue: { type: number }
    minItems: 1
  GrantedAbilities:
    type: array
    items:
      type: object
      required: [AbilityClass]
      properties:
        AbilityClass: { type: string }
        Level: { type: integer, default: 1 }
        InputID: { type: string }
        Handle: { type: string }
        bIsActive: { type: boolean, default: false }
  ActiveEffects:
    type: array
    items:
      type: object
      required: [Handle, EffectClass]
      properties:
        Handle: { type: string }
        EffectClass: { type: string }
        Duration: { type: number }
        Stacks: { type: integer, default: 1 }
        StartTime: { type: number }
        Level: { type: integer, default: 1 }
        InstigatorGC: { type: string }
  OwnedTags:
    type: array
    items:
      type: string
      pattern: "^[A-Z][a-zA-Z0-9]*(\\.[A-Z][a-zA-Z0-9]*)*$"
  ReplicationMode:
    type: string
    enum: [Minimal, Mixed, Full, None]
    default: Mixed
  bIsActive:
    type: boolean
    default: true
  Metadata:
    type: object
    properties:
      DisplayName: { type: string }
      Description: { type: string }
      Tags: { type: array, items: { type: string } }
      DebugCategory: { type: string }
```
