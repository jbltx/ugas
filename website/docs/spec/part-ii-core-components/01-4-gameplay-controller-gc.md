---
title: "4. Gameplay Controller(GC)"
sidebar_position: 1
---

### 4.1 Responsibilities

The Gameplay Controlleris the central hub for all gameplay ability logic. An GC implementation MUST:

1. Maintain collections of granted Abilities, active Effects, and owned Tags
2. Manage one or more AttributeSets
3. Process Ability activation requests
4. Apply and remove Gameplay Effects
5. Dispatch events for state changes
6. Support network replication (if applicable)

### 4.2 Ownership Model

The GC implements a dual-actor ownership model:

**Owner Actor**
: The logical owner of the GC. The Owner is responsible for:
- GC lifecycle management
- Network authority
- Persistence across possession changes

**Avatar Actor**
: The world representation associated with the GC. The Avatar provides:
- Spatial position for targeting
- Animation and physics integration
- Visual representation

#### Same-Actor Configuration

For simple entities (AI-controlled enemies, destructible objects), the Owner and Avatar MAY be the same Actor:

```
┌─────────────────────────────┐
│         AI ENEMY            │
│  ┌───────────────────────┐  │
│  │         GC            │  │
│  │   Owner: this         │  │
│  │   Avatar: this        │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

#### Split-Actor Configuration

For player-controlled characters in networked games, the Owner and Avatar SHOULD be separate to ensure GC persistence across respawns:

```
┌─────────────────────────────┐        ┌─────────────────────────────┐
│       PLAYER STATE          │        │      PLAYER CHARACTER       │
│  (Persists entire session)  │        │  (Destroyed on death)       │
│  ┌───────────────────────┐  │        │                             │
│  │         GC            │──┼────────┼──▶ Avatar reference         │
│  │   Owner: this         │  │        │                             │
│  └───────────────────────┘  │        └─────────────────────────────┘
└─────────────────────────────┘
```

### 4.3 Lifecycle

#### Initialization Sequence

1. GC is instantiated on Owner Actor
2. AttributeSets are registered with GC
3. Owner and Avatar references are set
4. Initial Abilities are granted
5. Initial Effects are applied
6. Replication is configured (if networked)

#### Possession Handling

When Avatar possession changes:

1. Previous Avatar reference is cleared
2. Active Effects targeting Avatar location are re-evaluated
3. New Avatar reference is set
4. Avatar-dependent Abilities are re-validated

#### Destruction Cleanup

1. All active Effects are removed
2. All granted Abilities are revoked
3. Event subscriptions are cleared
4. Network replication is terminated

### 4.4 Interface Specification

Implementations SHOULD provide an interface for GC discovery:

```typescript
interface IAbilitySystemInterface {
  /**
   * Returns the Gameplay Controllerassociated with this entity.
   * @returns The GC instance, or null if not available
   */
  GetAbilitySystemComponent(): AbilitySystemComponent | null;
}
```

Actors participating in the ability system MUST implement this interface or provide an equivalent discovery mechanism.

### 4.5 Public API

The following methods define the core GC interface:

#### Effect Context Creation

```typescript
/**
 * Creates a new Effect Context for outgoing effects.
 * @returns A handle to the new context
 */
MakeEffectContext(): EffectContextHandle;
```

#### Effect Spec Creation

```typescript
/**
 * Creates an Effect Spec for application.
 * @param effectClass - The Effect definition to instantiate
 * @param level - The level at which to apply the effect
 * @param context - The effect context handle
 * @returns A handle to the new spec
 */
MakeOutgoingSpec(
  effectClass: GameplayEffectClass,
  level: number,
  context: EffectContextHandle
): EffectSpecHandle;
```

#### Effect Application

```typescript
/**
 * Applies an effect to this GC's owner.
 * @param spec - The effect spec to apply
 * @param predictionKey - Optional prediction key for client-side prediction
 * @returns Handle to the active effect, or invalid handle if application failed
 */
ApplyGameplayEffectToSelf(
  spec: EffectSpecHandle,
  predictionKey?: PredictionKey
): ActiveEffectHandle;

/**
 * Applies an effect to a target GC.
 * @param target - The target GC
 * @param spec - The effect spec to apply
 * @param predictionKey - Optional prediction key for client-side prediction
 * @returns Handle to the active effect, or invalid handle if application failed
 */
ApplyGameplayEffectToTarget(
  target: AbilitySystemComponent,
  spec: EffectSpecHandle,
  predictionKey?: PredictionKey
): ActiveEffectHandle;
```

#### Effect Removal

```typescript
/**
 * Removes an active effect.
 * @param handle - Handle to the active effect
 * @param stacksToRemove - Number of stacks to remove (-1 for all)
 * @returns True if removal succeeded
 */
RemoveActiveGameplayEffect(
  handle: ActiveEffectHandle,
  stacksToRemove: number = -1
): boolean;
```

#### Ability Management

```typescript
/**
 * Grants an ability to this GC.
 * @param abilityClass - The ability class to grant
 * @param level - Initial ability level
 * @param inputID - Optional input binding
 * @returns Handle to the granted ability spec
 */
GrantAbility(
  abilityClass: GameplayAbilityClass,
  level: number = 1,
  inputID?: InputID
): AbilitySpecHandle;

/**
 * Attempts to activate an ability.
 * @param handle - Handle to the ability spec
 * @returns True if activation succeeded
 */
TryActivateAbility(handle: AbilitySpecHandle): boolean;
```

---
