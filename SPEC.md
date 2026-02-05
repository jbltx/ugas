# Universal Gameplay Attribute System Specification

**Version:** 1.0
**Date:** February 2026
**Author:** Mickael Bonfill (jbltx)

---

## Table of Contents

- [Part I: Foundations](#part-i-foundations)
  - [1. Introduction](#1-introduction)
  - [2. Terminology](#2-terminology)
  - [3. Architectural Overview](#3-architectural-overview)
- [Part II: Core Components](#part-ii-core-components)
  - [4. Gameplay Controller(GC)](#4-ability-system-component-GC)
  - [5. Attributes](#5-attributes)
  - [6. Attribute Sets](#6-attribute-sets)
  - [7. Gameplay Tags](#7-gameplay-tags)
  - [8. Gameplay Abilities](#8-gameplay-abilities)
  - [9. Gameplay Effects](#9-gameplay-effects)
- [Part III: Asynchronous Execution](#part-iii-asynchronous-execution)
  - [10. Ability Tasks](#10-ability-tasks)
  - [11. Input Integration](#11-input-integration)
- [Part IV: Feedback and Networking](#part-iv-feedback-and-networking)
  - [12. Gameplay Cues](#12-gameplay-cues)
  - [13. Network Replication](#13-network-replication)
- [Part V: Reference Implementation](#part-v-reference-implementation)
  - [14. Implementation Examples](#14-implementation-examples)
  - [15. Case Studies](#15-case-studies)
- [Appendices](#appendices)
  - [Appendix A: Mathematical Notation](#appendix-a-mathematical-notation)
  - [Appendix B: Complete Schema Reference](#appendix-b-complete-schema-reference)
  - [Appendix C: References and Citations](#appendix-c-references-and-citations)

---

# Part I: Foundations

## 1. Introduction

### 1.1 Purpose and Scope

The Universal Gameplay Attribute System (UGAS) is an open, engine-agnostic specification designed to standardize gameplay logic across game engines and AI world models. This specification defines the architecture, data structures, and behavioral contracts required to implement a consistent ability system that can be deployed on platforms ranging from traditional engines (Unreal Engine, Unity, Godot) to next-generation generative world models such as Google Genie.

The scope of this specification includes:

- Numeric gameplay state representation (Attributes)
- Semantic state labeling (Gameplay Tags)
- Action definition and execution (Gameplay Abilities)
- State mutation mechanisms (Gameplay Effects)
- Asynchronous execution patterns (Ability Tasks)
- Client feedback systems (Gameplay Cues)
- Network synchronization protocols

This specification does NOT define:

- Rendering or audio implementation details
- Physics engine integration specifics
- Platform-specific memory management
- User interface implementation

### 1.2 Design Philosophy

The UGAS specification is founded on three core principles:

**Decoupled Gameplay Logic**

Traditional gameplay programming relies on imperative state changes within character classes, leading to tightly coupled code where a single modification to a health variable must manually notify UI elements, sound systems, and networking layers. UGAS shifts this paradigm toward a reactive, data-driven architecture where the Actor is merely an avatar—a spatial representation—while the Gameplay Controller(GC) serves as the authoritative state container.

**Reactive, Data-Driven Architecture**

All state changes flow through a single mutation layer (Gameplay Effects), ensuring that every modification to the game state is tracked, predicted, and synchronized. This approach eliminates expensive per-frame polling of UI elements or AI state machines in favor of event-driven notifications.

**Cross-Platform Interoperability**

By defining gameplay rules as deterministic, replicable operations on abstract data structures, UGAS enables a unified framework that can be implemented across diverse execution environments. An GC can exist as a C++ component in Unreal Engine, a Data-Oriented Technology Stack (DOTS) entity in Unity, or a latent action sequence in an AI-generated environment.

### 1.3 Document Conventions

#### Notation

This specification uses the following notational conventions:

- **Mathematical Notation**: Standard mathematical symbols for summation (Σ), product (Π), and set operations (∈, ⊆, ∩, ∪)
- **Pseudocode**: Language-agnostic pseudocode for algorithm descriptions
- **Interface Definitions**: Abstract interface declarations using TypeScript-like syntax

#### Requirement Levels

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

| Keyword | Meaning |
|---------|---------|
| MUST / REQUIRED / SHALL | Absolute requirement of the specification |
| MUST NOT / SHALL NOT | Absolute prohibition |
| SHOULD / RECOMMENDED | Valid reasons may exist to ignore, but implications must be understood |
| SHOULD NOT / NOT RECOMMENDED | Valid reasons may exist to implement, but implications must be understood |
| MAY / OPTIONAL | Truly optional; interoperability must be ensured |

### 1.4 Normative References

- RFC 2119: Key words for use in RFCs to Indicate Requirement Levels
- IEEE 754: Standard for Floating-Point Arithmetic
- JSON Schema: Draft 2020-12
- YAML 1.2 Specification

---

## 2. Terminology

This section provides formal definitions for terms used throughout this specification.

**Actor**
: An entity within the game world that can possess an Gameplay Entity. Actors MAY have spatial representation, AI behavior, or player control.

**Avatar**
: The world representation (visual, physical) associated with an Gameplay Entity. The Avatar is the entity that exists in game space and interacts with the physics and rendering systems.

**Owner**
: The logical owner of an Gameplay Entity. The Owner is responsible for the persistence and lifecycle of the GC. In networked games, the Owner typically corresponds to the authoritative controller of the entity.

**Attribute**
: A named, typed value representing a quantitative aspect of an Actor's state. Attributes implement the dual-value pattern with Base Value and Current Value.

**AttributeSet**
: A logical container that groups related Attributes. AttributeSets provide modular composition of Actor capabilities.

**Modifier**
: A temporary or permanent adjustment to an Attribute's value. Modifiers define an operation (Add, Multiply, Divide, Override) and a magnitude.

**Tag**
: A hierarchical, unique identifier serving as a conceptual label for Actors, Abilities, and Effects. Tags use dot-notation (e.g., `State.Debuff.Stunned.Magic`).

**TagContainer**
: A collection of Tags associated with an entity. TagContainers support efficient query operations.

**TagQuery**
: A predicate expression evaluated against a TagContainer to determine matches.

**Ability**
: A self-contained unit of logic defining an action an Actor can perform. Abilities are asynchronous, stateful objects with defined lifecycles.

**AbilitySpec**
: Instance data for a granted Ability, including level, input binding, and runtime parameters.

**AbilityTask**
: An asynchronous operation within an Ability that pauses execution until a specific trigger condition is met.

**Effect**
: The mechanism by which Attributes and Tags are modified. Effects are the ONLY authorized mechanism for mutating gameplay state.

**EffectSpec**
: Lightweight application data for applying an Effect, containing magnitude, level, and context information.

**EffectContext**
: Runtime context for Effect application, including source Actor, target Actor, hit location, and causal chain information.

**Cue**
: A client-side feedback element (VFX, SFX, camera effects) triggered by Tags or Effects. Cues are purely cosmetic and do not affect gameplay logic.

**CueManager**
: Client-side system responsible for instantiating and managing Cue resources.

**GC (Gameplay Entity)**
: The central component managing an Actor's Attributes, Tags, Abilities, and Effects. The GC is the authoritative state container for gameplay logic.

---

## 3. Architectural Overview

### 3.1 Four-Pillar Model

The UGAS architecture is predicated on the interaction between four distinct pillars:

```
┌─────────────────────────────────────────────────────────────────┐
│                       GAMEPLAY CONTROLLER                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────┐ ┌───────────────┐ ┌──────────────────────┐   │
│  │   DATA        │ │  SEMANTIC     │ │      LOGIC           │   │
│  │   LAYER       │ │  LAYER        │ │      LAYER           │   │
│  │               │ │               │ │                      │   │
│  │  Attributes   │ │  Gameplay Tags│ │  Gameplay Abilities  │   │
│  │ Attribute Sets│ │ Tag Containers│ │  Ability Tasks       │   │
│  │               │ │               │ │                      │   │
│  └──────┬────────┘ └──────┬────────┘ └──────────┬───────────┘   │
│         │                 │                     │               │
│         └─────────────────┼─────────────────────┘               │
│                           │                                     │
│                           ▼                                     │
│              ┌────────────────────────┐                         │
│              │    MUTATION LAYER      │                         │
│              │                        │                         │
│              │   Gameplay Effects     │                         │
│              │   Modifiers            │                         │
│              │   Execution Calcs      │                         │
│              └────────────────────────┘                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Data Layer (Attributes)**
: Numeric state representation. Attributes store quantitative values such as Health, Mana, Strength, and Speed. All numeric gameplay state MUST be represented through Attributes.

**Semantic Layer (Tags)**
: Qualitative state representation. Tags describe "what kind" or "in what state" an Actor exists. Tags enable logic gating, ability requirements, and state queries without coupling to specific implementations.

**Logic Layer (Abilities)**
: Behavioral definitions. Abilities encapsulate the asynchronous, stateful logic of actions Actors can perform. Abilities coordinate with Tasks for complex, multi-stage execution.

**Mutation Layer (Effects)**
: State change mechanism. Effects are the ONLY authorized mechanism for modifying Attributes or Tags. This restriction ensures all state changes are tracked, predicted, and synchronized.

### 3.2 Component Relationships

```
                              ┌─────────────┐
                              │   ACTOR     │
                              │  (Avatar)   │
                              └──────┬──────┘
                                     │ possesses
                                     ▼
┌─────────────┐              ┌───────────────┐              ┌─────────────┐
│   OWNER     │──────────────│   GAMEPLAY    │──────────────│ ATTRIBUTE   │
│   ACTOR     │   owns       │  CONTROLLER   │   contains   │   SETS      │
└─────────────┘              └───────┬───────┘              └─────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
             ┌───────────┐    ┌───────────┐    ┌───────────┐
             │ ABILITIES │    │   TAGS    │    │  EFFECTS  │
             │  (Specs)  │    │(Container)│    │ (Active)  │
             └─────┬─────┘    └───────────┘    └─────┬─────┘
                   │                                 │
                   ▼                                 ▼
             ┌───────────┐                    ┌───────────┐
             │   TASKS   │                    │ MODIFIERS │
             └───────────┘                    └───────────┘
```

### 3.3 Execution Model

The UGAS execution model follows a deterministic sequence for processing gameplay logic:

1. **Input Processing**: Hardware inputs are mapped to Input Actions, which trigger Ability activation attempts.

2. **Ability Activation**: The GC validates activation requirements (Tags, Costs, Cooldowns) before committing the Ability.

3. **Effect Application**: Abilities apply Effects to Targets. Effects create Modifiers on Attributes and grant/remove Tags.

4. **Attribute Recalculation**: Affected Attributes recalculate their Current Values based on active Modifiers.

5. **Event Dispatch**: OnAttributeChanged events propagate to registered observers.

6. **Cue Triggering**: Tag changes trigger appropriate Gameplay Cues on clients.

7. **Replication**: State changes are replicated to networked clients according to the configured replication mode.

### 3.4 Threading Considerations

Implementations SHOULD consider the following threading guidelines:

- **Main Thread**: Ability activation, Effect application, and Attribute modification SHOULD occur on the main game thread to ensure deterministic ordering.

- **Async Tasks**: AbilityTasks MAY spawn background work but MUST return results to the main thread for state modification.

- **Replication**: Network replication MAY occur on dedicated networking threads but MUST synchronize with the main thread for state application.

- **Cues**: Gameplay Cue instantiation MAY occur on rendering threads but MUST NOT modify gameplay state.

---

# Part II: Core Components

## 4. Gameplay Controller(GC)

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

## 5. Attributes

### 5.1 Attribute Data Structure

An Attribute MUST implement the following data structure:

```typescript
struct Attribute {
  /** Permanent value, modified only by Instant effects */
  BaseValue: float;

  /** Dynamically calculated value including all active modifiers */
  CurrentValue: float;

  /** Collection of active modifiers affecting this attribute */
  Modifiers: ModifierStack;

  /** Static configuration for this attribute */
  Metadata: AttributeMetadata;
}

struct AttributeMetadata {
  /** Unique identifier for this attribute */
  Name: string;

  /** Attribute category */
  Category: AttributeCategory;

  /** Minimum allowed value (optional) */
  MinValue?: float | AttributeReference;

  /** Maximum allowed value (optional) */
  MaxValue?: float | AttributeReference;

  /** Replication configuration */
  ReplicationMode: AttributeReplicationMode;
}

enum AttributeCategory {
  /** Consumable values (Health, Mana, Stamina) */
  Resource,

  /** Derived statistics (Damage, Defense, Speed) */
  Statistic,

  /** Meta-attributes used for calculations only */
  Meta
}
```

### 5.2 Dual-Value Pattern

Every Attribute MUST implement the dual-value pattern consisting of Base Value and Current Value. This distinction is the primary mechanism for handling temporary modifications.

**Base Value**
: The permanent, persistent value of the Attribute. Base Values are modified ONLY by Instant effects and represent permanent changes such as leveling, permanent upgrades, or instant damage/healing.

**Current Value**
: The dynamically calculated result of the Base Value plus all active temporary Modifiers. Current Values are ephemeral and automatically recalculated when Modifiers are added or removed.

| Component | Modification Source | Persistence |
|-----------|---------------------|-------------|
| Base Value | Instant Effects only | Persistent (saved) |
| Current Value | All Modifier types | Ephemeral (calculated) |

### 5.3 Modifier Pipeline

The Current Value calculation MUST follow a standardized pipeline to ensure mathematical consistency across implementations.

#### Formula

The Current Value $V_{current}$ is calculated as:

$$V_{current} = \max\left( V_{min},\ \min\left( V_{max},\ \left( V_{base} + \sum a_i \right) \times \left( 1 + \sum p_j \right) \times \prod m_k + \sum b_l \right) \right)$$

Where:
- $V_{base}$ = Base Value
- $a_i$ = Flat additive modifiers (Add operations)
- $p_j$ = Additive percentage modifiers (expressed as decimals, e.g., +10% = 0.1)
- $m_k$ = Multiplicative factors (Multiply operations)
- $b_l$ = Bonus flat (Add operations)
- $V_{min}$ = Minimum value constraint
- $V_{max}$ = Maximum value constraint

Note that clamping is not mandatory, in that case the formula can be simplified as:

$$V_{current} = \left( V_{base} + \sum a_i \right) \times \left( 1 + \sum p_j \right) \times \prod m_k + \sum b_l$$

#### Order of Operations

The order of operations is CRITICAL for deterministic results:

1. Sum all flat additive modifiers (Add)
2. Apply flat additions to Base Value
3. Sum all additive percentage modifiers
4. Apply percentage modification
5. Multiply all multiplicative factors together
6. Apply multiplicative factors
7. Add the sum of all flat bonus modifiers (very rare use cases, usually there is none)
8. Apply Override modifiers (if any, replacing the result)
9. Apply clamping constraints

#### Example Calculation

Given:
- Base Value: 100
- Add Modifier 1: +20
- Add Modifier 2: +10
- Additive Percentage 1: +10% (0.1)
- Additive Percentage 2: +15% (0.15)
- Multiplicative 1: 1.5×
- Multiplicative 2: 2.0×
- No Bonus Flat

Calculation:
```
Step 1-2: 100 + 20 + 10 = 130
Step 3-4: 130 × (1 + 0.1 + 0.15) = 130 × 1.25 = 162.5
Step 5-6: 162.5 × 1.5 × 2.0 = 487.5
```

Current Value = 487.5

### 5.4 Clamping and Bounds

Attributes MAY define minimum and maximum constraints. Constraints can be:

**Static Values**
: Fixed numeric bounds that do not change.

```yaml
Clamping:
  Min: 0.0
  Max: 100.0
```

**Dependent Attribute References**
: Bounds referencing other Attributes, enabling dynamic constraints.

```yaml
Clamping:
  Min: 0.0
  Max: "MaxHealth"  # References another attribute
```

When a constraint references another Attribute:
1. The referenced Attribute's Current Value is used as the bound
2. Changes to the referenced Attribute trigger recalculation of dependent Attributes
3. Circular dependencies MUST NOT be created

### 5.5 Attribute Metadata

Attribute Metadata defines static configuration:

**Category**
- `Resource`: Consumable values that are spent and recovered (Health, Mana, Stamina)
- `Statistic`: Derived values used in calculations (Damage, Defense, CritChance)
- `Meta`: Internal values used only for calculations, not displayed to players

**Replication Flags**
- `None`: Not replicated
- `OwnerOnly`: Replicated only to owning client
- `All`: Replicated to all clients

### 5.6 OnAttributeChanged Event

Any change to an Attribute—whether to Base Value or Current Value—MUST trigger an OnAttributeChanged event.

#### Event Payload

```typescript
struct AttributeChangedEvent {
  /** The attribute that changed */
  Attribute: AttributeReference;

  /** Previous current value */
  OldValue: float;

  /** New current value */
  NewValue: float;

  /** The effect that caused the change (if any) */
  CausalEffect?: ActiveEffectHandle;

  /** Source of the change */
  Source?: AbilitySystemComponent;

  /** Target of the change */
  Target: AbilitySystemComponent;
}
```

#### Subscription Model

Observers SHOULD register for attribute change notifications:

```typescript
interface IAttributeChangeObserver {
  OnAttributeChanged(event: AttributeChangedEvent): void;
}

// Registration
GC.RegisterAttributeChangeObserver(
  attribute: AttributeReference,
  observer: IAttributeChangeObserver
): void;

// Unregistration
GC.UnregisterAttributeChangeObserver(
  attribute: AttributeReference,
  observer: IAttributeChangeObserver
): void;
```

### 5.7 Schema Definition

```yaml
Attribute:
  Name: string              # Required: Unique identifier
  DefaultBaseValue: float   # Required: Initial base value
  Category: enum            # Optional: Resource | Statistic | Meta
  Clamping:                 # Optional: Value constraints
    Min: float | string     # Static value or attribute reference
    Max: float | string     # Static value or attribute reference
  ReplicationMode: enum     # Optional: None | OwnerOnly | All
  Metadata:                 # Optional: Additional configuration
    DisplayName: string     # Human-readable name
    Description: string     # Tooltip description
    UICategory: string      # UI grouping
```

---

## 6. Attribute Sets

### 6.1 Purpose and Composition

An Attribute Set is a logical container grouping related Attributes. Attribute Sets provide:

- **Modularity**: Actors can mix and match sets based on capabilities
- **Organization**: Related Attributes are defined together
- **Reusability**: Common sets can be shared across Actor types
- **Serialization Boundary**: Sets define units for save/load operations

### 6.2 Set Registration with GC

Attribute Sets MUST be registered with an GC before use:

```typescript
/**
 * Registers an attribute set with this GC.
 * @param attributeSet - The set to register
 */
GC.RegisterAttributeSet(attributeSet: AttributeSet): void;

/**
 * Unregisters an attribute set from this GC.
 * @param attributeSet - The set to unregister
 */
GC.UnregisterAttributeSet(attributeSet: AttributeSet): void;

/**
 * Retrieves a registered attribute set by type.
 * @returns The attribute set, or null if not registered
 */
GC.GetAttributeSet<T extends AttributeSet>(): T | null;
```

### 6.3 Modular Design Patterns

#### Combat Attribute Set

```yaml
AttributeSet:
  Name: "CombatAttributeSet"
  Attributes:
    - Name: "Health"
      DefaultBaseValue: 100.0
      Category: Resource
      Clamping:
        Min: 0.0
        Max: "MaxHealth"

    - Name: "MaxHealth"
      DefaultBaseValue: 100.0
      Category: Statistic
      Clamping:
        Min: 1.0

    - Name: "Mana"
      DefaultBaseValue: 50.0
      Category: Resource
      Clamping:
        Min: 0.0
        Max: "MaxMana"

    - Name: "MaxMana"
      DefaultBaseValue: 50.0
      Category: Statistic
      Clamping:
        Min: 0.0

    - Name: "AttackPower"
      DefaultBaseValue: 10.0
      Category: Statistic

    - Name: "Defense"
      DefaultBaseValue: 5.0
      Category: Statistic
```

#### Movement Attribute Set

```yaml
AttributeSet:
  Name: "MovementAttributeSet"
  Attributes:
    - Name: "MoveSpeed"
      DefaultBaseValue: 600.0
      Category: Statistic
      Clamping:
        Min: 0.0

    - Name: "JumpVelocity"
      DefaultBaseValue: 800.0
      Category: Statistic

    - Name: "GravityScale"
      DefaultBaseValue: 1.0
      Category: Statistic

    - Name: "AirControl"
      DefaultBaseValue: 0.5
      Category: Statistic
      Clamping:
        Min: 0.0
        Max: 1.0
```

#### Vehicle Attribute Set

```yaml
AttributeSet:
  Name: "VehicleAttributeSet"
  Attributes:
    - Name: "EngineTorque"
      DefaultBaseValue: 500.0
      Category: Statistic

    - Name: "MaxSpeed"
      DefaultBaseValue: 200.0
      Category: Statistic

    - Name: "TireGrip"
      DefaultBaseValue: 1.0
      Category: Statistic

    - Name: "Fuel"
      DefaultBaseValue: 100.0
      Category: Resource
      Clamping:
        Min: 0.0
        Max: "MaxFuel"

    - Name: "MaxFuel"
      DefaultBaseValue: 100.0
      Category: Statistic
```

### 6.4 Cross-Set Dependencies

Attributes MAY reference Attributes from other registered sets:

```yaml
AttributeSet:
  Name: "DerivedStatsSet"
  Dependencies:
    - "CombatAttributeSet"
  Attributes:
    - Name: "EffectiveHealth"
      DefaultBaseValue: 0.0
      Category: Meta
      DerivedFrom:
        Expression: "Health * (1 + Defense / 100)"
```

Cross-set references are resolved at runtime. Implementations MUST:

1. Validate all dependencies exist before registration
2. Ensure proper recalculation order when dependencies change
3. Prevent circular dependency chains

### 6.5 Schema Definition

```yaml
AttributeSet:
  Name: string                    # Required: Unique set identifier
  Dependencies: [string]          # Optional: Required attribute sets
  Attributes: [Attribute]         # Required: List of attributes
  Metadata:                       # Optional: Additional configuration
    DisplayName: string
    Description: string
```

---

## 7. Gameplay Tags

### 7.1 Hierarchical Naming Convention

Gameplay Tags use hierarchical dot-notation to represent semantic categories:

```
Category.Subcategory.Leaf
```

Examples:
- `State.Debuff.Stunned.Magic`
- `Ability.Type.Melee.Slash`
- `DamageType.Physical.Blunt`
- `Cooldown.Ability.Fireball`
- `GameplayCue.Impact.Fire`

#### Naming Rules

1. Each segment MUST use PGCalCase
2. Hierarchies SHOULD NOT exceed 5 levels
3. Leaf tags SHOULD be specific; parent tags SHOULD be categorical
4. Reserved prefixes:
   - `GameplayCue.*` - Cue trigger tags
   - `Cooldown.*` - Cooldown tracking tags
   - `State.*` - Actor state tags
   - `Ability.*` - Ability classification tags
   - `DamageType.*` - Damage classification tags

### 7.2 Tag Container

A Tag Container is a collection of tags associated with an entity.

#### Internal Representation

Implementations SHOULD use an efficient representation:

```typescript
struct TagContainer {
  /** Set of explicit tags */
  ExplicitTags: Set<Tag>;

  /** Cached parent tags (computed from explicit tags) */
  ParentTags: Set<Tag>;

  /** Combined explicit and parent tags */
  AllTags: Set<Tag>;
}
```

#### Operations

```typescript
interface TagContainer {
  /** Adds a tag to the container */
  AddTag(tag: Tag): void;

  /** Removes a tag from the container */
  RemoveTag(tag: Tag): void;

  /** Checks if the container has any tags */
  IsEmpty(): boolean;

  /** Returns the count of explicit tags */
  Count(): number;

  /** Clears all tags */
  Clear(): void;
}
```

### 7.3 Query Operations

| Operation | Semantics | Example |
|-----------|-----------|---------|
| `MatchesTag(T)` | Returns true if T or any child of T is present | Checking for any type of "Stunned" status |
| `MatchesTagExact(T)` | Returns true only if T exactly is present | Specific immunity to "Stunned.Magic" but not "Stunned.Physical" |
| `HasAny(Container)` | Returns true if intersection is non-empty | Spell that affects "Undead" OR "Demon" types |
| `HasAll(Container)` | Returns true if container is a subset | Combo requiring "Chilled" AND "Vulnerable" |
| `HasNone(Container)` | Returns true if intersection is empty | Ability blocked by any "Immunity" tag |

#### Query Examples

```typescript
// Container has: State.Debuff.Stunned.Magic, Status.Burning

container.MatchesTag("State.Debuff.Stunned")     // true (parent match)
container.MatchesTag("State.Debuff.Stunned.Magic") // true (exact match)
container.MatchesTag("State.Debuff.Stunned.Physical") // false

container.MatchesTagExact("State.Debuff.Stunned") // false (not exact)
container.MatchesTagExact("State.Debuff.Stunned.Magic") // true

container.HasAny(["Status.Frozen", "Status.Burning"]) // true
container.HasAll(["State.Debuff.Stunned.Magic", "Status.Burning"]) // true
container.HasAll(["Status.Burning", "Status.Frozen"]) // false
```

### 7.4 Tag Inheritance and Implicit Tags

When a tag is added to a container, all parent tags are implicitly present:

```
Adding: State.Debuff.Stunned.Magic

Implicit parents:
  - State
  - State.Debuff
  - State.Debuff.Stunned
```

This enables hierarchical queries where checking for `State.Debuff` matches any debuff type.

### 7.5 State Representation via Tags

Tags are the primary method for representing Actor states. Instead of boolean flags:

```typescript
// Avoid this pattern
if (actor.isStunned && !actor.isImmune) { ... }

// Use tag queries
if (actor.Tags.MatchesTag("State.Debuff.Stunned") &&
    !actor.Tags.MatchesTag("Status.Immune.Stun")) { ... }
```

This decouples the "How" of a state (animation, logic freeze) from the "What" of the state (the Tag).

### 7.6 Schema Definition

```yaml
TagDefinition:
  Tag: string                     # Full hierarchical tag name
  Description: string             # Human-readable description
  AllowMultiple: boolean          # Can multiple instances exist? (default: false)
  DevComment: string              # Developer notes
```

Tag definitions MAY be collected in a tag registry:

```yaml
TagRegistry:
  - Tag: "State.Debuff.Stunned"
    Description: "Actor is unable to perform actions"

  - Tag: "State.Debuff.Stunned.Magic"
    Description: "Stun caused by magical effect"

  - Tag: "State.Debuff.Stunned.Physical"
    Description: "Stun caused by physical impact"

  - Tag: "Status.Immune.Stun"
    Description: "Actor is immune to stun effects"
```

---

## 8. Gameplay Abilities

### 8.1 Ability Definition

A Gameplay Ability is a self-contained unit of logic defining an action an Actor can perform. Unlike simple function calls, Abilities are asynchronous, stateful objects with defined lifecycles.

#### Ability Class Structure

```typescript
abstract class GameplayAbility {
  /** Tags describing this ability */
  AbilityTags: TagContainer;

  /** Tags that block this ability's activation */
  BlockedByTags: TagContainer;

  /** Tags that this ability blocks when active */
  BlockAbilitiesWithTags: TagContainer;

  /** Tags required on owner for activation */
  ActivationRequiredTags: TagContainer;

  /** Tags that prevent activation if present */
  ActivationBlockedTags: TagContainer;

  /** Tags applied to owner while ability is active */
  ActivationOwnedTags: TagContainer;

  /** Cost effect applied on commit */
  CostEffect?: GameplayEffectClass;

  /** Cooldown effect applied on commit */
  CooldownEffect?: GameplayEffectClass;

  /** Called when ability is activated */
  abstract ActivateAbility(context: AbilityContext): void;

  /** Called when ability ends */
  abstract EndAbility(wGCancelled: boolean): void;
}
```

#### AbilitySpec (Instance Data)

```typescript
struct AbilitySpec {
  /** Reference to the ability class */
  AbilityClass: GameplayAbilityClass;

  /** Current level of this ability instance */
  Level: number;

  /** Input action binding (if any) */
  InputID?: InputID;

  /** Handle for identification */
  Handle: AbilitySpecHandle;

  /** Runtime parameters */
  Parameters: Map<string, any>;

  /** Is currently active? */
  IsActive: boolean;
}
```

### 8.2 Lifecycle State Machine

```
                    ┌──────────────┐
                    │  NotGranted  │
                    └──────┬───────┘
                           │ Grant
                           ▼
                    ┌──────────────┐
        ┌──────────▶│   Granted    │◀──────────┐
        │           │  (Inactive)  │           │
        │           └──────┬───────┘           │
        │                  │ TryActivate       │
        │                  ▼                   │
        │           ┌──────────────┐           │
        │           │  Activating  │───────────┤
        │           │ (Validating) │  Fail     │
        │           └──────┬───────┘           │
        │                  │ Commit            │
        │                  ▼                   │
        │           ┌──────────────┐           │
        │           │    Active    │           │
        │           │ (Executing)  │           │
        │           └──────┬───────┘           │
        │                  │ End/Cancel        │
        │                  ▼                   │
        │           ┌──────────────┐           │
        └───────────│   Ending     │───────────┘
                    └──────────────┘
```

### 8.3 Activation Requirements

Before an Ability can activate, the following checks MUST pass:

1. **Granted Check**: Ability must be granted to the GC
2. **Not Already Active**: Ability must not currently be active (unless configured for multiple instances)
3. **Required Tags**: Owner must have all tags in `ActivationRequiredTags`
4. **Blocked Tags**: Owner must NOT have any tags in `ActivationBlockedTags`
5. **Cost Verification**: If CostEffect is defined, owner must have sufficient resources
6. **Cooldown Verification**: Cooldown tag must not be present

```typescript
function CanActivateAbility(spec: AbilitySpec): boolean {
  const ownerTags = GC.GetOwnedTags();

  // Check required tags
  if (!ownerTags.HasAll(spec.AbilityClass.ActivationRequiredTags)) {
    return false;
  }

  // Check blocked tags
  if (ownerTags.HasAny(spec.AbilityClass.ActivationBlockedTags)) {
    return false;
  }

  // Check cooldown
  if (ownerTags.MatchesTag(GetCooldownTag(spec))) {
    return false;
  }

  // Check cost
  if (!CanAffordCost(spec)) {
    return false;
  }

  return true;
}
```

### 8.4 Commit Phase

The Commit phase is the point of no return where resources are consumed and cooldowns begin. Once committed:

1. Cost Effect is applied (resources consumed)
2. Cooldown Effect is applied (cooldown tag granted)
3. Activation Owned Tags are granted
4. Ability proceeds to execution

```typescript
function CommitAbility(spec: AbilitySpec): boolean {
  // Apply cost
  if (spec.AbilityClass.CostEffect) {
    const costSpec = MakeOutgoingSpec(spec.AbilityClass.CostEffect, spec.Level);
    ApplyGameplayEffectToSelf(costSpec);
  }

  // Apply cooldown
  if (spec.AbilityClass.CooldownEffect) {
    const cooldownSpec = MakeOutgoingSpec(spec.AbilityClass.CooldownEffect, spec.Level);
    ApplyGameplayEffectToSelf(cooldownSpec);
  }

  // Grant activation tags
  GC.AddLooseGameplayTags(spec.AbilityClass.ActivationOwnedTags);

  return true;
}
```

### 8.5 Costs and Cooldowns as Effects

Costs and Cooldowns are NOT separate variables but are implemented as specialized Gameplay Effects.

#### Cost Effect Pattern

```yaml
Effect:
  Name: "GE_Fireball_Cost"
  DurationPolicy: Instant
  Modifiers:
    - Attribute: "Mana"
      Operation: Add
      Magnitude:
        Type: ScalableFloat
        Value: -50.0  # Negative to subtract
```

#### Cooldown Effect Pattern

```yaml
Effect:
  Name: "GE_Fireball_Cooldown"
  DurationPolicy: HasDuration
  Duration:
    Type: ScalableFloat
    Value: 5.0  # 5 second cooldown
  GrantedTags:
    - "Cooldown.Ability.Fireball"
```

This pattern enables external modification of costs and cooldowns. For example, a "Mana Efficiency" buff could apply a multiplier to all cost effects:

```yaml
Effect:
  Name: "GE_ManaEfficiency_Buff"
  DurationPolicy: HasDuration
  Duration:
    Value: 30.0
  Modifiers:
    - Attribute: "ManaCostMultiplier"
      Operation: Multiply
      Magnitude:
        Value: 0.75  # 25% reduction
```

### 8.6 Cancellation and Interruption

Abilities may be cancelled by:

1. **Self-Cancellation**: Ability logic calls EndAbility(true)
2. **External Cancel**: Another system calls CancelAbility on the GC
3. **Cancel Tags**: An Effect grants a tag in the Ability's `CancelAbilitiesWithTags` set
4. **Owner Death**: Owner's Health reaches zero

```typescript
function CancelAbility(handle: AbilitySpecHandle): void {
  const spec = GetAbilitySpec(handle);
  if (!spec.IsActive) return;

  // Remove activation tags
  GC.RemoveLooseGameplayTags(spec.AbilityClass.ActivationOwnedTags);

  // Call ability's end handler
  spec.AbilityInstance.EndAbility(true /* wGCancelled */);

  // Cleanup active tasks
  CancelAllAbilityTasks(handle);

  spec.IsActive = false;
}
```

### 8.7 Schema Definition

```yaml
Ability:
  Name: string                    # Required: Unique identifier

  Tags:
    AbilityTags: [string]         # Tags describing this ability
    BlockedByTags: [string]       # Tags that block activation
    BlockAbilitiesWithTags: [string]  # Tags blocked while active
    CancelAbilitiesWithTags: [string] # Tags cancelled on activation
    ActivationRequiredTags: [string]  # Required for activation
    ActivationBlockedTags: [string]   # Block activation if present
    ActivationOwnedTags: [string]     # Granted while active

  Cost: string                    # Effect name for cost
  Cooldown: string                # Effect name for cooldown

  Tasks:                          # Sequential task definitions
    - Type: string                # Task type name
      Params: object              # Task-specific parameters

  Metadata:
    DisplayName: string
    Description: string
    Icon: string
```

---

## 9. Gameplay Effects

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
Effect:
  Name: "GE_Poison"
  DurationPolicy: HasDuration
  Duration:
    Value: 10.0
  Period:
    Period: 1.0
    ExecuteOnApplication: false
  Modifiers:
    - Attribute: "Health"
      Operation: Add
      Magnitude:
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
Effect:
  Name: "GE_Burning"
  DurationPolicy: HasDuration
  Duration:
    Value: 5.0
  GrantedTags:
    - "State.Debuff.Burning"
    - "State.Element.Fire"
  Modifiers:
    - Attribute: "Health"
      Operation: Add
      Magnitude:
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
Effect:
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

# Part III: Asynchronous Execution

## 10. Ability Tasks

### 10.1 Purpose and Design

Ability Tasks are specialized asynchronous nodes that pause ability execution until a specific trigger condition is met. Tasks enable complex, multi-stage abilities to be written in a linear, readable fashion while executing asynchronously across frames or network ticks.

Tasks leverage the Observer design pattern for efficiency. Instead of polling a condition every frame, the ability registers a task and goes dormant. When the trigger condition is met, the task "wakes up" the ability and execution continues.

### 10.2 Task Lifecycle

```
         ┌─────────────┐
         │  Inactive   │
         └──────┬──────┘
                │ Instantiate
                ▼
         ┌─────────────┐
         │   Ready     │
         └──────┬──────┘
                │ Activate
                ▼
         ┌─────────────┐     Tick (if needed)
    ┌───▶│   Active    │◀────────────────┐
    │    └──────┬──────┘                 │
    │           │                        │
    │           ├────────────────────────┘
    │           │ Trigger/Complete
    │           ▼
    │    ┌─────────────┐
    │    │  Completed  │
    │    └─────────────┘
    │
    │    ┌─────────────┐
    └────│  Cancelled  │
         └─────────────┘
```

**Instantiation**: Task is created with configuration parameters
**Activation**: Task registers with relevant systems (timers, events, physics)
**Tick** (optional): Some tasks require per-frame updates
**Completion**: Trigger condition met; ability execution resumes
**Cancellation**: Task is aborted (ability cancelled, owner died)

### 10.3 Predefined Task Categories

| Category | Trigger | Example Tasks |
|----------|---------|---------------|
| Temporal | Timer expiry | WaitDelay, WaitGameTime |
| Event-Based | Gameplay event | WaitGameplayEvent, WaitTagChanged |
| Input-Based | Input state change | WaitInputRelease, WaitInputPressed |
| State-Based | Tag change | WaitTagAdded, WaitTagRemoved |
| Spatial | Collision/overlap | WaitOverlap, WaitForTarget |
| Animation | Montage notify | WaitAnimationEvent, WaitMontageEnded |

#### WaitDelay

Waits for a specified duration.

```typescript
class WaitDelay extends AbilityTask {
  Duration: float;

  OnActivate(): void {
    this.StartTimer(this.Duration);
  }

  OnTimerComplete(): void {
    this.Completed.Broadcast();
    this.EndTask();
  }
}
```

#### WaitGameplayEvent

Waits for a gameplay event with a matching tag.

```typescript
class WaitGameplayEvent extends AbilityTask {
  EventTag: Tag;
  OnlyTriggerOnce: boolean;

  OnActivate(): void {
    this.Owner.OnGameplayEvent.Subscribe(this.EventTag, this.OnEvent);
  }

  OnEvent(payload: GameplayEventData): void {
    this.EventReceived.Broadcast(payload);
    if (this.OnlyTriggerOnce) {
      this.EndTask();
    }
  }
}
```

#### WaitInputRelease

Waits for an input action to be released.

```typescript
class WaitInputRelease extends AbilityTask {
  InputID: InputID;

  OnActivate(): void {
    this.InputSystem.OnInputReleased.Subscribe(this.InputID, this.OnRelease);
  }

  OnRelease(heldDuration: float): void {
    this.Released.Broadcast(heldDuration);
    this.EndTask();
  }
}
```

#### WaitTagAdded

Waits for a specific tag to be added to the owner.

```typescript
class WaitTagAdded extends AbilityTask {
  WaitTag: Tag;

  OnActivate(): void {
    if (this.Owner.Tags.MatchesTag(this.WaitTag)) {
      this.TagFound.Broadcast();
      this.EndTask();
      return;
    }
    this.Owner.OnTagChanged.Subscribe(this.OnTagChanged);
  }

  OnTagChanged(tag: Tag, added: boolean): void {
    if (added && this.WaitTag.Matches(tag)) {
      this.TagFound.Broadcast();
      this.EndTask();
    }
  }
}
```

### 10.4 Custom Task Implementation

Custom tasks MUST:

1. Extend the base AbilityTask class
2. Implement OnActivate() for setup
3. Implement cleanup in OnEndTask()
4. Provide delegate/event outputs for ability continuation
5. Handle cancellation gracefully

```typescript
class WaitForHealthThreshold extends AbilityTask {
  Threshold: float;
  Comparison: ComparisonType;  // LessThan | LessEqual | Greater | GreaterEqual

  OnActivate(): void {
    // Check immediately
    if (this.CheckThreshold()) {
      this.ThresholdReached.Broadcast();
      this.EndTask();
      return;
    }

    // Subscribe to attribute changes
    this.Owner.OnAttributeChanged.Subscribe("Health", this.OnHealthChanged);
  }

  OnHealthChanged(event: AttributeChangedEvent): void {
    if (this.CheckThreshold()) {
      this.ThresholdReached.Broadcast();
      this.EndTask();
    }
  }

  CheckThreshold(): boolean {
    const health = this.Owner.GetAttributeValue("Health");
    switch (this.Comparison) {
      case LessThan: return health < this.Threshold;
      case LessEqual: return health <= this.Threshold;
      case Greater: return health > this.Threshold;
      case GreaterEqual: return health >= this.Threshold;
    }
  }

  OnEndTask(): void {
    this.Owner.OnAttributeChanged.Unsubscribe("Health", this.OnHealthChanged);
  }
}
```

### 10.5 Task Ownership and Cleanup

Tasks are owned by the Ability that created them. When an Ability ends:

1. All active Tasks are cancelled
2. Task event subscriptions are cleared
3. Task resources are released

```typescript
function EndAbility(wGCancelled: boolean): void {
  // Cancel all active tasks
  for (const task of this.ActiveTasks) {
    task.Cancel();
  }
  this.ActiveTasks.Clear();

  // Continue with ability end logic...
}
```

---

## 11. Input Integration

### 11.1 Command Pattern Overview

The UGAS input system implements the Command pattern to decouple hardware inputs from ability execution. This separation enables:

- Controller remapping without code changes
- Platform-specific input schemes
- Input buffering and queuing
- Combo system integration

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Hardware   │─────▶│    Input     │─────▶│    Input     │
│    Input     │      │   Action     │      │     ID       │
└──────────────┘      └──────────────┘      └──────┬───────┘
                                                   │
                                                   ▼
                                            ┌──────────────┐
                                            │   Ability    │
                                            │  Activation  │
                                            └──────────────┘
```

### 11.2 Input Action to Ability Mapping

Abilities are bound to Input IDs, which are mapped from Input Actions:

```yaml
InputMapping:
  Actions:
    - Action: "IA_PrimaryAttack"
      InputID: "Ability.Attack.Primary"
      KeyBindings:
        - Key: "MouseLeft"
        - Key: "GamepadRightTrigger"

    - Action: "IA_SecondaryAttack"
      InputID: "Ability.Attack.Secondary"
      KeyBindings:
        - Key: "MouseRight"
        - Key: "GamepadLeftTrigger"

    - Action: "IA_Ability1"
      InputID: "Ability.Slot.1"
      KeyBindings:
        - Key: "Q"
        - Key: "GamepadFaceLeft"
```

Ability grants include optional Input ID binding:

```typescript
GC.GrantAbility(
  abilityClass: GA_Fireball,
  level: 1,
  inputID: "Ability.Slot.1"
);
```

### 11.3 Input Buffering

Input buffering allows players to queue inputs during animations or recovery frames:

```typescript
struct InputBufferConfig {
  /** Enable input buffering */
  Enabled: boolean;

  /** Buffer window in seconds */
  BufferWindow: float;

  /** Maximum buffered inputs */
  MaxBufferSize: number;
}
```

When input buffering is enabled:

1. Input arrives during "blocked" state (animation, recovery)
2. Input is stored in buffer with timestamp
3. When block ends, buffered inputs are processed in order
4. Expired inputs (beyond buffer window) are discarded

```typescript
function ProcessBufferedInputs(): void {
  const now = GetCurrentTime();

  // Remove expired inputs
  this.InputBuffer = this.InputBuffer.filter(
    input => now - input.Timestamp < this.BufferWindow
  );

  // Process valid inputs
  for (const input of this.InputBuffer) {
    if (TryActivateAbilityByInputID(input.InputID)) {
      break;  // Successfully activated, stop processing
    }
  }

  this.InputBuffer.Clear();
}
```

### 11.4 Remapping Support

Input mappings SHOULD be externalizable and modifiable at runtime:

```typescript
interface IInputMapper {
  /** Get InputID for an action */
  GetInputIDForAction(action: InputAction): InputID;

  /** Remap an action to a new key */
  RemapAction(action: InputAction, newKey: Key): void;

  /** Reset to defaults */
  ResetToDefaults(): void;

  /** Save current mappings */
  SaveMappings(): void;

  /** Load saved mappings */
  LoadMappings(): void;
}
```

---

# Part IV: Feedback and Networking

## 12. Gameplay Cues

### 12.1 Design Philosophy

Gameplay Cues enforce strict separation between Mechanics and Aesthetics. This separation provides:

- **Server Optimization**: Headless servers load no visual/audio resources
- **Client Customization**: Visual settings don't affect gameplay
- **Network Efficiency**: Cues are not replicated; only trigger tags are
- **Platform Adaptation**: Different platforms can have different cue implementations

### 12.2 Cue Trigger Mechanism

Cues are triggered by Tags following the `GameplayCue.*` convention:

```yaml
Effect:
  Name: "GE_FireDamage"
  DurationPolicy: Instant
  Modifiers:
    - Attribute: "Health"
      Operation: Add
      Magnitude:
        Value: -25.0
  GameplayCues:
    - "GameplayCue.Impact.Fire"
```

When the Effect is applied:
1. Server applies the Effect and modifies attributes
2. `GameplayCue.Impact.Fire` tag is communicated to clients
3. Clients' Cue Managers instantiate the fire impact VFX/SFX

### 12.3 Cue Types

**Burst Cues** (Fire-and-Forget)
: Triggered once, play to completion, clean themselves up.

```typescript
class GC_Impact_Fire extends GameplayCueBurst {
  OnExecute(context: CueContext): void {
    SpawnParticleSystem("PS_FireImpact", context.HitLocation);
    PlaySound("SFX_FireImpact", context.HitLocation);
  }
}
```

**Looping Cues** (Duration-Bound)
: Persist while the triggering Effect is active.

```typescript
class GC_Status_Burning extends GameplayCueLooping {
  private ParticleComponent: ParticleSystem;

  OnAdd(context: CueContext): void {
    this.ParticleComponent = SpawnLoopingParticle("PS_BurningLoop", context.Target);
    StartLoopingSound("SFX_BurningLoop", context.Target);
  }

  OnRemove(): void {
    this.ParticleComponent.Destroy();
    StopLoopingSound("SFX_BurningLoop");
  }
}
```

### 12.4 Cue Manager

The Cue Manager is a client-side system responsible for:

1. Receiving cue trigger notifications
2. Matching tags to Cue implementations
3. Instantiating and managing Cue resources
4. Pooling frequently-used Cues for performance

```typescript
class GameplayCueManager {
  private CueRegistry: Map<Tag, GameplayCueClass>;
  private ActiveLoopingCues: Map<ActiveEffectHandle, GameplayCue[]>;

  HandleCueNotify(tag: Tag, context: CueContext, type: CueNotifyType): void {
    const cueClass = this.CueRegistry.get(tag);
    if (!cueClass) return;

    switch (type) {
      case Execute:
        const burstCue = this.InstantiateCue(cueClass);
        burstCue.OnExecute(context);
        break;

      case Add:
        const loopingCue = this.InstantiateCue(cueClass);
        loopingCue.OnAdd(context);
        this.ActiveLoopingCues.get(context.EffectHandle).push(loopingCue);
        break;

      case Remove:
        const activeCues = this.ActiveLoopingCues.get(context.EffectHandle);
        for (const cue of activeCues) {
          cue.OnRemove();
        }
        this.ActiveLoopingCues.delete(context.EffectHandle);
        break;
    }
  }
}
```

### 12.5 Server Optimization

On headless servers:

1. Cue Manager is NOT instantiated
2. Cue assets are NOT loaded
3. Cue trigger tags are still processed for replication
4. Memory footprint is significantly reduced

Implementations SHOULD support a headless mode flag:

```typescript
if (!IsHeadlessServer()) {
  this.CueManager = new GameplayCueManager();
  this.CueManager.LoadCueAssets();
}
```

---

## 13. Network Replication

### 13.1 Replication Architecture

UGAS defines a client-server replication model where:

- The server is authoritative for all gameplay state
- Clients receive replicated state updates
- Clients may predict state changes locally
- Server reconciles predicted state with authoritative state

```
┌──────────────────┐            ┌──────────────────┐
│      SERVER      │            │      CLIENT      │
│                  │            │                  │
│  ┌────────────┐  │  Replicate │  ┌────────────┐  │
│  │    GC     │──┼───────────▶│  │    GC     │  │
│  │(Authority) │  │            │  │  (Proxy)   │  │
│  └────────────┘  │            │  └────────────┘  │
│                  │            │                  │
│                  │  Predict   │                  │
│                  │◀───────────┼──(Local Input)   │
│                  │            │                  │
│                  │ Reconcile  │                  │
│                  │───────────▶│                  │
└──────────────────┘            └──────────────────┘
```

### 13.2 Replication Modes

| Mode | Effects | Cues | Tags | Attributes | Use Case |
|------|---------|------|------|------------|----------|
| `Minimal` | None | All | All | None | AI entities, distant actors |
| `Mixed` | Owner only | All | All | Owner only | Player characters |
| `Full` | All | All | All | All | Single-player, debugging |

**Minimal Mode**
: Only Cue triggers and Tag changes are replicated. Effects and Attributes are server-only. Suitable for AI entities where clients don't need full state.

**Mixed Mode**
: Full replication to the owning client; minimal replication to others. The standard mode for player characters in multiplayer games.

**Full Mode**
: Complete replication to all clients. Used for single-player games or debugging. Higher bandwidth cost.

### 13.3 Bandwidth Optimization

#### Delta Compression

Only changed values are transmitted:

```typescript
struct ReplicatedAttributeSet {
  /** Bitmask of changed attributes since last update */
  DirtyMask: uint32;

  /** Only changed attribute values */
  ChangedValues: float[];
}
```

#### Dirty Bit Tracking

Attributes track their dirty state:

```typescript
function SetBaseValue(attribute: Attribute, newValue: float): void {
  if (attribute.BaseValue !== newValue) {
    attribute.BaseValue = newValue;
    attribute.bIsDirty = true;
    this.DirtyAttributes.add(attribute);
  }
}
```

#### Quantization

For bandwidth-critical scenarios, attribute values MAY be quantized:

```typescript
struct QuantizedHealth {
  /** 0-255 representing 0-100% health */
  HealthPercent: uint8;
}
```

### 13.4 Client-Side Prediction

To eliminate network latency perception, clients predict ability outcomes locally:

```typescript
function TryActivateAbility_Predicted(handle: AbilitySpecHandle): void {
  // Generate prediction key
  const predictionKey = GeneratePredictionKey();

  // Predict locally
  const success = TryActivateAbility_Local(handle, predictionKey);

  if (success) {
    // Store predicted state
    this.PredictedActivations.set(predictionKey, {
      Handle: handle,
      Timestamp: GetCurrentTime(),
      State: CaptureState()
    });

    // Send to server
    Server_TryActivateAbility(handle, predictionKey);
  }
}
```

### 13.5 Server Reconciliation

When server response differs from prediction:

```typescript
function OnServerActivationResponse(
  predictionKey: PredictionKey,
  serverSuccess: boolean,
  serverState: GameplayState
): void {
  const prediction = this.PredictedActivations.get(predictionKey);

  if (!prediction) return;

  if (!serverSuccess) {
    // Prediction was wrong - rollback
    RollbackToState(prediction.State);
  } else {
    // Prediction was correct - reconcile minor differences
    ReconcileState(serverState);
  }

  this.PredictedActivations.delete(predictionKey);
}
```

#### Rollback and Replay

For significant discrepancies:

1. Revert to last known authoritative state
2. Re-apply all inputs that occurred since that state
3. Blend visually to avoid jarring corrections

```typescript
function RollbackAndReplay(
  authoritativeState: GameplayState,
  inputHistory: Input[]
): void {
  // 1. Revert state
  ApplyState(authoritativeState);

  // 2. Replay inputs
  for (const input of inputHistory) {
    if (input.Timestamp > authoritativeState.Timestamp) {
      SimulateInput(input);
    }
  }

  // 3. Blend if needed
  if (VisualDiscrepancy > Threshold) {
    StartVisualBlend(currentVisual, newSimulatedState);
  }
}
```

### 13.6 Replication Frequency Recommendations

| Actor Type | Update Rate | Notes |
|------------|-------------|-------|
| Player Character | 60-100 Hz | High frequency for responsive feel |
| Important AI | 30-60 Hz | Moderate frequency |
| Distant Actors | 10-20 Hz | Lower frequency acceptable |
| Static Objects | On Change | Event-based only |

---

# Part V: Reference Implementation

## 14. Implementation Examples

### 14.1 Basic Damage Application

#### Effect Definition

```yaml
Effect:
  Name: "GE_BasicDamage"
  DurationPolicy: Instant
  Modifiers:
    - Attribute: "Health"
      Operation: Add
      Magnitude:
        Type: SetByCaller
        DataTag: "Damage.Amount"
  GameplayCues:
    - "GameplayCue.Impact.Generic"
```

#### Application Flow

```typescript
function ApplyDamage(target: AbilitySystemComponent, damage: float): void {
  // 1. Create context
  const context = this.GC.MakeEffectContext();
  context.SetEffectCauser(this.Owner);

  // 2. Create spec
  const spec = this.GC.MakeOutgoingSpec(GE_BasicDamage, 1, context);

  // 3. Set damage amount
  spec.SetByCallerMagnitude("Damage.Amount", -damage);  // Negative for subtraction

  // 4. Apply to target
  const handle = this.GC.ApplyGameplayEffectToTarget(target, spec);

  // 5. Check success
  if (handle.IsValid()) {
    OnDamageApplied(target, damage);
  }
}
```

#### Attribute Change Handling

```typescript
class HealthObserver implements IAttributeChangeObserver {
  OnAttributeChanged(event: AttributeChangedEvent): void {
    const oldValue = event.OldValue;
    const newValue = event.NewValue;

    // Update health bar UI
    this.HealthBar.SetPercent(newValue / this.MaxHealth);

    // Show damage number
    const damage = oldValue - newValue;
    if (damage > 0) {
      SpawnDamageNumber(damage, event.Target.GetLocation());
    }

    // Check for death
    if (newValue <= 0) {
      OnDeath(event.CausalEffect);
    }
  }
}
```

### 14.2 Buff/Debuff with Duration

#### Temporary Modifier

```yaml
Effect:
  Name: "GE_StrengthBuff"
  DurationPolicy: HasDuration
  Duration:
    Type: ScalableFloat
    Value: 30.0
  ExecutionPolicy: RunInMerge  # Refresh duration on reapplication
  Modifiers:
    - Attribute: "AttackPower"
      Operation: Multiply
      Magnitude:
        Type: ScalableFloat
        Value: 1.25  # +25% damage
  GrantedTags:
    - "Status.Buff.Strength"
  GameplayCues:
    - "GameplayCue.Status.StrengthBuff"
```

#### Visual Cue Integration

```typescript
class GC_Status_StrengthBuff extends GameplayCueLooping {
  private AuraEffect: ParticleSystem;
  private BuffIcon: UIWidget;

  OnAdd(context: CueContext): void {
    // Spawn visual aura
    this.AuraEffect = SpawnAttached(
      "PS_StrengthAura",
      context.Target,
      "Spine"
    );

    // Show buff icon in UI
    this.BuffIcon = ShowBuffIcon("Icon_Strength", context.Duration);

    // Play activation sound
    PlaySound("SFX_BuffActivate");
  }

  OnRemove(): void {
    this.AuraEffect.Destroy();
    this.BuffIcon.Remove();
    PlaySound("SFX_BuffExpire");
  }
}
```

### 14.3 Ability with Cast Time

```yaml
Ability:
  Name: "GA_Fireball"

  Tags:
    AbilityTags:
      - "Ability.Type.Spell"
      - "Ability.Element.Fire"
    ActivationOwnedTags:
      - "State.Casting"
    CancelAbilitiesWithTags:
      - "State.Stunned"
    ActivationBlockedTags:
      - "State.Silenced"

  Cost: "GE_Fireball_Cost"
  Cooldown: "GE_Fireball_Cooldown"
```

#### Task-Based Implementation

```typescript
class GA_Fireball extends GameplayAbility {
  CastTime: float = 1.5;
  ProjectileClass: ProjectileClass;

  ActivateAbility(context: AbilityContext): void {
    // 1. Commit resources
    if (!CommitAbility()) {
      EndAbility(true);
      return;
    }

    // 2. Play cast animation
    PlayAnimation("Anim_CastFireball");

    // 3. Wait for cast time
    const waitTask = WaitDelay(this.CastTime);
    waitTask.OnComplete.Subscribe(this.OnCastComplete);

    // 4. Listen for interruption
    const interruptTask = WaitTagAdded("State.Stunned");
    interruptTask.OnTagFound.Subscribe(this.OnInterrupted);
  }

  OnCastComplete(): void {
    // Spawn and launch projectile
    const projectile = SpawnProjectile(
      this.ProjectileClass,
      this.GetAvatarLocation(),
      this.GetAimDirection()
    );
    projectile.SetDamageEffect(GE_FireballDamage);

    EndAbility(false);
  }

  OnInterrupted(): void {
    // Play fizzle effect
    TriggerCue("GameplayCue.Ability.Interrupted");
    EndAbility(true);
  }
}
```

### 14.4 Complex Calculation (Armor Penetration)

```typescript
class ExecCalc_ArmorPenetration extends ExecutionCalculation {
  SourceCaptureDefinitions = [
    { Attribute: "AttackPower", CaptureTime: OnExecution },
    { Attribute: "ArmorPenetrationFlat", CaptureTime: OnExecution },
    { Attribute: "ArmorPenetrationPercent", CaptureTime: OnExecution },
    { Attribute: "CriticalChance", CaptureTime: OnExecution },
    { Attribute: "CriticalDamage", CaptureTime: OnExecution }
  ];

  TargetCaptureDefinitions = [
    { Attribute: "Armor", CaptureTime: OnExecution },
    { Attribute: "DamageReduction", CaptureTime: OnExecution }
  ];

  Execute(source, target, context): ModifierResult[] {
    // Get source stats
    const attackPower = source.Get("AttackPower");
    const armorPenFlat = source.Get("ArmorPenetrationFlat");
    const armorPenPercent = source.Get("ArmorPenetrationPercent");
    const critChance = source.Get("CriticalChance");
    const critDamage = source.Get("CriticalDamage");

    // Get target stats
    const targetArmor = target.Get("Armor");
    const damageReduction = target.Get("DamageReduction");

    // Calculate effective armor
    const armorAfterFlat = Math.max(0, targetArmor - armorPenFlat);
    const effectiveArmor = armorAfterFlat * (1 - armorPenPercent);

    // Armor damage reduction formula
    const armorDR = effectiveArmor / (effectiveArmor + 100);

    // Base damage
    let damage = attackPower * (1 - armorDR);

    // Apply critical hit
    if (RandomFloat() < critChance) {
      damage *= critDamage;
      context.SetTag("Hit.Critical");
    }

    // Apply flat damage reduction
    damage *= (1 - damageReduction);

    return [{
      Attribute: "Health",
      Operation: Add,
      Magnitude: -damage
    }];
  }
}
```

---

## 15. Case Studies

### 15.1 Platformer (Mario-style)

#### Movement Attributes

```yaml
AttributeSet:
  Name: "PlatformerMovementSet"
  Attributes:
    - Name: "GravityScale"
      DefaultBaseValue: 1.0
      Category: Statistic

    - Name: "JumpVelocity"
      DefaultBaseValue: 1200.0
      Category: Statistic

    - Name: "AirControl"
      DefaultBaseValue: 0.65
      Category: Statistic
      Clamping:
        Min: 0.0
        Max: 1.0

    - Name: "CoyoteTimeDuration"
      DefaultBaseValue: 0.15
      Category: Statistic

    - Name: "JumpBufferDuration"
      DefaultBaseValue: 0.1
      Category: Statistic

    - Name: "VerticalVelocity"
      DefaultBaseValue: 0.0
      Category: Meta

    - Name: "HorizontalSpeed"
      DefaultBaseValue: 600.0
      Category: Statistic
```

#### Jump Ability with Variable Height

```typescript
class GA_Jump extends GameplayAbility {
  ActivateAbility(context: AbilityContext): void {
    // Check grounded OR coyote time
    if (!this.Owner.Tags.MatchesTag("State.Grounded") &&
        !this.Owner.Tags.MatchesTag("Status.CoyoteTime")) {
      EndAbility(true);
      return;
    }

    // Apply jump impulse
    this.Owner.Tags.AddTag("State.InAir");
    this.Owner.Tags.RemoveTag("State.Grounded");

    const jumpVelocity = this.Owner.GetAttribute("JumpVelocity");
    ApplyImpulse(Vector3.Up * jumpVelocity);

    // Variable height: wait for button release
    const releaseTask = WaitInputRelease("Jump");
    releaseTask.OnReleased.Subscribe(this.OnJumpReleased);

    // Wait for landing
    const landTask = WaitGameplayEvent("Event.Landed");
    landTask.OnEvent.Subscribe(this.OnLanded);
  }

  OnJumpReleased(heldDuration: float): void {
    // Short press = cut jump short
    if (this.Owner.GetAttribute("VerticalVelocity") > 0) {
      // Apply gravity multiplier for shorter jump
      const cutSpec = MakeOutgoingSpec(GE_JumpCut, 1);
      ApplyGameplayEffectToSelf(cutSpec);
    }
  }

  OnLanded(): void {
    this.Owner.Tags.RemoveTag("State.InAir");
    this.Owner.Tags.AddTag("State.Grounded");
    EndAbility(false);
  }
}
```

#### Power-Up Effects

```yaml
Effect:
  Name: "GE_SuperMushroom"
  DurationPolicy: Infinite
  GrantedTags:
    - "State.PowerUp.Super"
  Modifiers:
    - Attribute: "Scale"
      Operation: Multiply
      Magnitude:
        Value: 2.0
    - Attribute: "Health"
      Operation: Add
      Magnitude:
        Value: 1.0  # Gain 1 hit point
  GameplayCues:
    - "GameplayCue.PowerUp.Super"
```

### 15.2 Racing (Forza-style)

#### Vehicle Attribute Sets

```yaml
AttributeSet:
  Name: "VehiclePerformanceSet"
  Attributes:
    - Name: "EngineTorque"
      DefaultBaseValue: 400.0
      Description: "Base torque in Nm"

    - Name: "EngineRPM"
      DefaultBaseValue: 0.0
      Category: Meta

    - Name: "MaxSpeed"
      DefaultBaseValue: 250.0
      Description: "Top speed in km/h"

    - Name: "TireGripMultiplier"
      DefaultBaseValue: 1.0
      Category: Statistic

    - Name: "AeroDownforce"
      DefaultBaseValue: 100.0
      Description: "Downforce coefficient"

    - Name: "TireTemperature"
      DefaultBaseValue: 80.0
      Clamping:
        Min: 20.0
        Max: 150.0
```

#### Biome-Based Area Effects

```yaml
Effect:
  Name: "GE_Biome_Mud"
  DurationPolicy: Infinite
  ApplicationRequiredTags:
    - "Vehicle"
  Modifiers:
    - Attribute: "TireGripMultiplier"
      Operation: Multiply
      Magnitude:
        Value: 0.4
    - Attribute: "MaxSpeed"
      Operation: Add
      Magnitude:
        Value: -30.0  # Reduce top speed
  GrantedTags:
    - "Surface.Mud"
---
Effect:
  Name: "GE_Biome_Asphalt"
  DurationPolicy: Infinite
  ApplicationRequiredTags:
    - "Vehicle"
  Modifiers:
    - Attribute: "TireGripMultiplier"
      Operation: Override
      Magnitude:
        Value: 1.0
  GrantedTags:
    - "Surface.Asphalt"
```

#### Physics Integration

```typescript
class ExecCalc_VehicleTraction extends ExecutionCalculation {
  SourceCaptureDefinitions = [
    { Attribute: "TireGripMultiplier", CaptureTime: OnExecution },
    { Attribute: "AeroDownforce", CaptureTime: OnExecution },
    { Attribute: "TireTemperature", CaptureTime: OnExecution },
    { Attribute: "CurrentSpeed", CaptureTime: OnExecution }
  ];

  Execute(source, target, context): ModifierResult[] {
    const baseGrip = source.Get("TireGripMultiplier");
    const downforce = source.Get("AeroDownforce");
    const tireTemp = source.Get("TireTemperature");
    const speed = source.Get("CurrentSpeed");

    // Downforce increases with speed squared
    const downforceBonus = (downforce * speed * speed) / 100000;

    // Tire temperature optimal range: 80-100
    let tempMultiplier = 1.0;
    if (tireTemp < 80) {
      tempMultiplier = 0.7 + (tireTemp / 80) * 0.3;
    } else if (tireTemp > 100) {
      tempMultiplier = 1.0 - ((tireTemp - 100) / 50) * 0.3;
    }

    const effectiveTraction = baseGrip * (1 + downforceBonus) * tempMultiplier;

    return [{
      Attribute: "AvailableTraction",
      Operation: Override,
      Magnitude: effectiveTraction
    }];
  }
}
```

### 15.3 ARPG (Diablo-style)

#### Damage Bucket Architecture

The "Damage Bucket" system prevents linear power creep by organizing modifiers into multiplicative groups.

```typescript
class ExecCalc_ARPGDamage extends ExecutionCalculation {
  Execute(source, target, context): ModifierResult[] {
    // Bucket A: Main Stat (additive within bucket)
    const mainStatBonus = source.Get("Strength") * 0.01;  // +1% per point

    // Bucket B: Additive Damage Bonuses
    let bucketB = 1.0;
    bucketB += source.Get("DamageBonus_Fire") || 0;
    bucketB += source.Get("DamageBonus_Elite") || 0;
    bucketB += source.Get("DamageBonus_WhileHealthy") || 0;

    // Bucket C: Multiplicative Powers
    let bucketC = 1.0;
    bucketC *= source.Get("LegendaryPowerMultiplier") || 1.0;
    bucketC *= source.Get("SetBonusMultiplier") || 1.0;

    // Vulnerability check
    let vulnerabilityMultiplier = 1.0;
    if (target.Tags.MatchesTag("Status.Vulnerable")) {
      vulnerabilityMultiplier = 1.2;
    }

    // Final calculation: Buckets multiply each other
    const baseDamage = source.Get("WeaponDamage");
    const finalDamage = baseDamage *
                        (1 + mainStatBonus) *  // Bucket A
                        bucketB *               // Bucket B
                        bucketC *               // Bucket C
                        vulnerabilityMultiplier;

    return [{
      Attribute: "Health",
      Operation: Add,
      Magnitude: -finalDamage
    }];
  }
}
```

#### Combat Tag Queries

```typescript
class GA_Whirlwind extends GameplayAbility {
  ActivateAbility(context: AbilityContext): void {
    // This ability tags
    this.AbilityTags = ["Ability.Type.Melee", "DamageType.Physical"];

    // Find targets in radius
    const targets = GetActorsInRadius(this.Owner.Location, 500);

    for (const target of targets) {
      // Check immunities
      if (target.Tags.MatchesTag("Immunity.Physical")) {
        // Show immune text
        SpawnFloatingText(target, "IMMUNE");
        continue;
      }

      // Apply damage effect
      const spec = MakeOutgoingSpec(GE_WhirlwindDamage, this.Level);

      // Check for vulnerability bonus
      if (target.Tags.MatchesTag("Status.Vulnerable")) {
        spec.SetByCallerMagnitude("VulnerabilityBonus", 0.2);
      }

      ApplyGameplayEffectToTarget(target.GC, spec);
    }
  }
}
```

#### Procedural Item Effects

```typescript
class ItemEquipSystem {
  EquipItem(item: Item): void {
    // Create infinite effect for item stats
    const itemEffect = GenerateItemEffect(item);

    // Apply effect
    const handle = this.GC.ApplyGameplayEffectToSelf(itemEffect);

    // Store handle for unequip
    this.EquippedItemEffects.set(item.ID, handle);

    // Grant item abilities
    for (const ability of item.GrantedAbilities) {
      this.GC.GrantAbility(ability.Class, ability.Level, ability.InputID);
    }
  }

  GenerateItemEffect(item: Item): EffectSpec {
    const effect = new GameplayEffect();
    effect.DurationPolicy = Infinite;

    // Add modifiers for each stat roll
    for (const stat of item.Stats) {
      effect.Modifiers.push({
        Attribute: stat.AttributeName,
        Operation: stat.Operation,
        Magnitude: { Type: ScalableFloat, Value: stat.Value }
      });
    }

    // Add item tag
    effect.GrantedTags.push(`Item.Equipped.${item.Slot}`);
    effect.GrantedTags.push(`Item.Type.${item.Type}`);

    return MakeOutgoingSpec(effect, 1, MakeEffectContext());
  }
}
```

### 15.4 Puzzle (2048-style)

#### Grid Cell Attributes

```yaml
AttributeSet:
  Name: "PuzzleCellSet"
  Attributes:
    - Name: "CellValue"
      DefaultBaseValue: 0.0
      Category: Statistic

    - Name: "GridX"
      DefaultBaseValue: 0.0
      Category: Meta

    - Name: "GridY"
      DefaultBaseValue: 0.0
      Category: Meta

    - Name: "MergePriority"
      DefaultBaseValue: 0.0
      Category: Meta
```

#### Move Ability with Tasks

```typescript
class GA_GridMove extends GameplayAbility {
  Direction: Vector2;

  ActivateAbility(context: AbilityContext): void {
    // Task 1: Scan grid
    const cells = ScanOccupiedCells();

    // Sort by direction (front to back)
    cells.sort((a, b) => GetDirectionPriority(a, b, this.Direction));

    // Calculate movements
    const movements: CellMovement[] = [];
    const merges: CellMerge[] = [];

    for (const cell of cells) {
      const result = CalculateDestination(cell, this.Direction);
      if (result.CanMove) {
        movements.push(result);
        if (result.WillMerge) {
          merges.push(result.MergeInfo);
        }
      }
    }

    // Apply movement effects
    for (const move of movements) {
      const moveSpec = MakeOutgoingSpec(GE_CellMove, 1);
      moveSpec.SetByCallerMagnitude("NewX", move.DestX);
      moveSpec.SetByCallerMagnitude("NewY", move.DestY);
      ApplyGameplayEffectToTarget(move.Cell.GC, moveSpec);
    }

    // Apply merge effects
    for (const merge of merges) {
      const mergeSpec = MakeOutgoingSpec(GE_CellMerge, 1);
      ApplyGameplayEffectToTarget(merge.TargetCell.GC, mergeSpec);

      // Mark source for destruction
      merge.SourceCell.Tags.AddTag("Status.PendingDestroy");
    }

    // Wait for animations
    const animTask = WaitDelay(0.2);
    animTask.OnComplete.Subscribe(this.OnMoveComplete);
  }

  OnMoveComplete(): void {
    // Destroy merged sources
    DestroyTaggedCells("Status.PendingDestroy");

    // Spawn new tile
    SpawnRandomTile();

    // Check win/lose conditions
    CheckGameState();

    EndAbility(false);
  }
}
```

#### Undo via Effect History

```typescript
class UndoSystem {
  private EffectHistory: HistoryFrame[] = [];

  RecordFrame(): void {
    const frame: HistoryFrame = {
      Timestamp: GetCurrentTime(),
      CellStates: [],
      AppliedEffects: []
    };

    // Capture all cell states
    for (const cell of GetAllCells()) {
      frame.CellStates.push({
        ID: cell.ID,
        Value: cell.GetAttribute("CellValue"),
        X: cell.GetAttribute("GridX"),
        Y: cell.GetAttribute("GridY")
      });
    }

    this.EffectHistory.push(frame);
  }

  Undo(): void {
    if (this.EffectHistory.length < 2) return;

    // Remove current frame
    this.EffectHistory.pop();

    // Get previous frame
    const previousFrame = this.EffectHistory[this.EffectHistory.length - 1];

    // Restore cell states
    for (const cellState of previousFrame.CellStates) {
      const cell = GetCellByID(cellState.ID);
      if (cell) {
        const restoreSpec = MakeOutgoingSpec(GE_RestoreState, 1);
        restoreSpec.SetByCallerMagnitude("Value", cellState.Value);
        restoreSpec.SetByCallerMagnitude("X", cellState.X);
        restoreSpec.SetByCallerMagnitude("Y", cellState.Y);
        ApplyGameplayEffectToTarget(cell.GC, restoreSpec);
      }
    }
  }
}
```

---

# Appendices

## Appendix A: Mathematical Notation

### Variable Naming Conventions

| Symbol | Meaning |
|--------|---------|
| $V$ | Value (generic) |
| $V_{base}$ | Base Value of an Attribute |
| $V_{current}$ | Current Value of an Attribute |
| $V_{min}$, $V_{max}$ | Minimum/Maximum bounds |
| $a$ | Additive modifier magnitude |
| $p$ | Percentage modifier magnitude |
| $m$ | Multiplicative factor |
| $t$ | Time variable |
| $\Delta_t$ | Time delta |
| $n$ | Count/index variable |

### Summation and Product Notation

**Summation** ($\sum$): Sum of values over an index range

$$\sum_{i=1}^{n} a_i = a_1 + a_2 + \cdots + a_n$$

**Product** ($\prod$): Product of values over an index range

$$\prod_{k=1}^{n} m_k = m_1 \times m_2 \times \cdots \times m_n$$

### Set Theory Notation for Tags

| Notation | Meaning |
|----------|---------|
| T | A single Tag |
| C | A TagContainer (set of Tags) |
| T ∈ C | Tag T is a member of Container C |
| C₁ ⊆ C₂ | Container C₁ is a subset of C₂ |
| C₁ ∩ C₂ | Intersection of two containers |
| C₁ ∪ C₂ | Union of two containers |
| C₁ ∩ C₂ ≠ ∅ | Containers have at least one common element |

---

## Appendix B: Complete Schema Reference

### Attribute YAML Schema

```yaml
# Attribute Definition Schema
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
          - type: string  # Attribute reference
      Max:
        oneOf:
          - type: number
          - type: string  # Attribute reference
  ReplicationMode:
    type: string
    enum: [None, OwnerOnly, All]
    default: All
  Metadata:
    type: object
    properties:
      DisplayName:
        type: string
      Description:
        type: string
      UICategory:
        type: string
      Icon:
        type: string
```

### AttributeSet YAML Schema

```yaml
# AttributeSet Definition Schema
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
    items:
      type: string
    description: Required attribute sets
  Attributes:
    type: array
    items:
      $ref: "#/definitions/Attribute"
  Metadata:
    type: object
    properties:
      DisplayName:
        type: string
      Description:
        type: string
```

### Ability YAML Schema

```yaml
# Ability Definition Schema
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
        items:
          type: string
      BlockedByTags:
        type: array
        items:
          type: string
      BlockAbilitiesWithTags:
        type: array
        items:
          type: string
      CancelAbilitiesWithTags:
        type: array
        items:
          type: string
      ActivationRequiredTags:
        type: array
        items:
          type: string
      ActivationBlockedTags:
        type: array
        items:
          type: string
      ActivationOwnedTags:
        type: array
        items:
          type: string
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
      required:
        - Type
      properties:
        Type:
          type: string
        Params:
          type: object
  Metadata:
    type: object
    properties:
      DisplayName:
        type: string
      Description:
        type: string
      Icon:
        type: string
```

### Effect JSON Schema

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
    $ref: "#/$defs/MagnitudeDefinition"
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
      $ref: "#/$defs/Modifier"
  Executions:
    type: array
    items:
      type: object
      properties:
        CalculatorClass:
          type: string
  GrantedTags:
    type: array
    items:
      type: string
  ApplicationRequiredTags:
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

$defs:
  MagnitudeDefinition:
    type: object
    required:
      - Type
    properties:
      Type:
        type: string
        enum:
          - ScalableFloat
          - AttributeBased
          - CustomCalculation
          - SetByCaller
      Value:
        type: number
      Curve:
        type: string
      CurveInput:
        type: string
      BackingAttribute:
        type: string
      Source:
        type: string
        enum:
          - Source
          - Target
      Coefficient:
        type: number
        default: 1
      PreMultiplyAdditive:
        type: number
        default: 0
      PostMultiplyAdditive:
        type: number
        default: 0
      CalculatorClass:
        type: string
      DataTag:
        type: string

  Modifier:
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
        $ref: "#/$defs/MagnitudeDefinition"
      Channel:
        type: string
```

### Tag Definition Schema

```yaml
# Tag Registry Schema
type: object
properties:
  Tags:
    type: array
    items:
      type: object
      required:
        - Tag
      properties:
        Tag:
          type: string
          pattern: "^[A-Z][a-zA-Z0-9]*(\\.[A-Z][a-zA-Z0-9]*)*$"
        Description:
          type: string
        AllowMultiple:
          type: boolean
          default: false
        DevComment:
          type: string
```

---

## Appendix C: References and Citations

### BibTeX Entries

```bibtex
@online{epicgames_gas,
  author = {{Epic Games}},
  title = {Understanding the Unreal Engine Gameplay Ability System},
  year = {2024},
  url = {https://dev.epicgames.com/documentation/en-us/unreal-engine/understanding-the-unreal-engine-gameplay-ability-system},
  urldate = {2026-02-03}
}

@online{tranek_gasdoc,
  author = {Dan Tranek},
  title = {GASDocumentation: Understanding Unreal Engine's GameplayAbilitySystem},
  year = {2024},
  url = {https://github.com/tranek/GASDocumentation},
  urldate = {2026-02-03}
}

@online{unity_gas,
  author = {{Unity Technologies}},
  title = {Unity Gameplay Ability System},
  year = {2024},
  url = {https://github.com/sjai013/unity-gameplay-ability-system},
  urldate = {2026-02-03}
}

@online{godot_attributes,
  author = {{OctoD}},
  title = {Godot Gameplay Attributes},
  year = {2024},
  url = {https://github.com/OctoD/godot_gameplay_attributes},
  urldate = {2026-02-03}
}

@online{google_genie,
  author = {{Google DeepMind}},
  title = {Genie: Generative Interactive Environments},
  year = {2024},
  url = {https://sites.google.com/view/genie-2024/home},
  urldate = {2026-02-03}
}

@book{gregory_engine,
  author = {Jason Gregory},
  title = {Game Engine Architecture},
  edition = {3rd},
  publisher = {A K Peters/CRC Press},
  year = {2018},
  isbn = {978-1138035454}
}

@online{gambetta_prediction,
  author = {Gabriel Gambetta},
  title = {Client-Side Prediction and Server Reconciliation},
  year = {2021},
  url = {https://www.gabrielgambetta.com/client-side-prediction-server-reconciliation.html},
  urldate = {2026-02-03}
}

@online{gaffer_sync,
  author = {Glenn Fiedler},
  title = {State Synchronization},
  year = {2019},
  url = {https://gafferongames.com/post/state_synchronization/},
  urldate = {2026-02-03}
}
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | February 2026 | Mickael Bonfill | Initial specification |

---

*End of Specification*
