# Preamble

Copyright 2026 Mickael Bonfill

This Specification is released under the [MIT License](https://opensource.org/licenses/MIT). Permission is hereby granted, free of charge, to any person obtaining a copy of this Specification and associated documentation files, to deal in the Specification without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Specification, and to permit persons to whom the Specification is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Specification.

The author makes no, and expressly disclaims any, representations or warranties, express or implied, regarding this Specification, including, without limitation: merchantability, fitness for a particular purpose, non-infringement of any intellectual property, correctness, accuracy, completeness, timeliness, and reliability. Under no circumstances will the author or contributors be liable for any damages, whether direct, indirect, special or consequential damages for lost revenues, lost profits, or otherwise, arising from or in connection with this Specification or the use or other dealings in this Specification.

Some parts of this Specification are purely informative and so are EXCLUDED from the normative scope of this Specification. The [???](#introduction-conventions) section of the [???](#introduction) defines how these parts of the Specification are identified.

Where this Specification uses technical terminology, defined in the [Glossary](#glossary) or otherwise, that refers to enabling technologies not expressly set forth in this Specification, those enabling technologies are EXCLUDED from the normative scope of this Specification.

Where this Specification identifies specific sections of external references, only those specifically identified sections define normative functionality.

The full text of the MIT License can be found in the [LICENSE](https://github.com/jbltx/ugas/blob/main/LICENSE) file at the root of the repository.

# Part I: Foundations

## 1. Introduction

### 1.1 Purpose and Scope

The Universal Gameplay Ability System (UGAS) is an open, engine-agnostic specification designed to standardize gameplay logic across game engines and runtime environments. This specification defines the architecture, data structures, and behavioral contracts required to implement a consistent ability system that can be deployed on any game engine or custom runtime, including Unreal Engine, Unity, and Godot.

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

*Decoupled Gameplay Logic*

Traditional gameplay programming relies on imperative state changes within character classes, leading to tightly coupled code where a single modification to a health variable must manually notify UI elements, sound systems, and networking layers. UGAS shifts this paradigm toward a reactive, data-driven architecture where the Actor is merely an avatar—a spatial representation—while the Gameplay Controller(GC) serves as the authoritative state container.

*Reactive, Data-Driven Architecture*

All state changes flow through a single mutation layer (Gameplay Effects), ensuring that every modification to the game state is tracked, predicted, and synchronized. This approach eliminates expensive per-frame polling of UI elements or AI state machines in favor of event-driven notifications.

*Cross-Platform Interoperability*

By defining gameplay rules as deterministic, replicable operations on abstract data structures, UGAS enables a unified framework that can be implemented across diverse execution environments. A GC can exist as a C++ component in Unreal Engine, a Data-Oriented Technology Stack (DOTS) entity in Unity, or a scripted component in Godot.

### 1.3 Document Conventions

#### Notation

This specification uses the following notational conventions:

- *Mathematical Notation*: Standard mathematical symbols for summation (Σ), product (Π), and set operations (∈, ⊆, ∩, ∪)

- *Pseudocode*: Language-agnostic pseudocode for algorithm descriptions

- *Interface Definitions*: Abstract interface declarations using TypeScript-like syntax

#### Requirement Levels

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

| Keyword                      | Meaning                                                                   |
|------------------------------|---------------------------------------------------------------------------|
| MUST / REQUIRED / SHALL      | Absolute requirement of the specification                                 |
| MUST NOT / SHALL NOT         | Absolute prohibition                                                      |
| SHOULD / RECOMMENDED         | Valid reasons may exist to ignore, but implications must be understood    |
| SHOULD NOT / NOT RECOMMENDED | Valid reasons may exist to implement, but implications must be understood |
| MAY / OPTIONAL               | Truly optional; interoperability must be ensured                          |

### 1.4 Normative References

- RFC 2119: Key words for use in RFCs to Indicate Requirement Levels

- IEEE 754: Standard for Floating-Point Arithmetic

- JSON Schema: Draft 2020-12

- YAML 1.2 Specification

## 2. Terminology

This section provides formal definitions for terms used throughout this specification.

Actor  
An entity within the game world that can possess a Gameplay Controller. Actors MAY have spatial representation, AI behavior, or player control.

Avatar  
The world representation (visual, physical) associated with a Gameplay Controller. The Avatar is the entity that exists in game space and interacts with the physics and rendering systems.

Owner  
The logical owner of a Gameplay Controller. The Owner is responsible for the persistence and lifecycle of the GC. In networked games, the Owner typically corresponds to the authoritative controller of the entity.

Attribute  
A named, typed value representing a quantitative aspect of an Actor’s state. Attributes implement the dual-value pattern with Base Value and Current Value.

AttributeSet  
A logical container that groups related Attributes. AttributeSets provide modular composition of Actor capabilities.

Modifier  
A temporary or permanent adjustment to an Attribute’s value. Modifiers define an operation (Add, AddPost, Multiply, Override) and a magnitude.

Tag  
A hierarchical, unique identifier serving as a conceptual label for Actors, Abilities, and Effects. Tags use dot-notation (e.g., `State.Debuff.Stunned.Magic`).

TagContainer  
A collection of Tags associated with an entity. TagContainers support efficient query operations.

TagQuery  
A predicate expression evaluated against a TagContainer to determine matches.

Ability  
A self-contained unit of logic defining an action an Actor can perform. Abilities are asynchronous, stateful objects with defined lifecycles.

AbilitySpec  
Instance data for a granted Ability, including level, input binding, and runtime parameters.

AbilityTask  
An asynchronous operation within an Ability that pauses execution until a specific trigger condition is met.

Effect  
The mechanism by which Attributes and Tags are modified. Effects are the ONLY authorized mechanism for mutating gameplay state.

EffectSpec  
Lightweight application data for applying an Effect, containing magnitude, level, and context information.

EffectContext  
Runtime context for Effect application, including source Actor, target Actor, hit location, and causal chain information.

Cue  
A client-side feedback element (VFX, SFX, camera effects) triggered by Tags or Effects. Cues are purely cosmetic and do not affect gameplay logic.

CueManager  
Client-side system responsible for instantiating and managing Cue resources.

GC (Gameplay Controller)  
The central component managing an Actor’s Attributes, Tags, Abilities, and Effects. The GC is the authoritative state container for gameplay logic.

## 3. Architectural Overview

### 3.1 Four-Pillar Model

The UGAS architecture is predicated on the interaction between four distinct pillars:

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

Data Layer (Attributes)  
Numeric state representation. Attributes store quantitative values such as Health, Mana, Strength, and Speed. All numeric gameplay state MUST be represented through Attributes.

Semantic Layer (Tags)  
Qualitative state representation. Tags describe "what kind" or "in what state" an Actor exists. Tags enable logic gating, ability requirements, and state queries without coupling to specific implementations.

Logic Layer (Abilities)  
Behavioral definitions. Abilities encapsulate the asynchronous, stateful logic of actions Actors can perform. Abilities coordinate with Tasks for complex, multi-stage execution.

Mutation Layer (Effects)  
State change mechanism. Effects are the ONLY authorized mechanism for modifying Attributes or Tags. This restriction ensures all state changes are tracked, predicted, and synchronized. Ability implementations MUST NOT call `Tags.AddTag()`, `Tags.RemoveTag()`, or any equivalent direct tag mutation API. All tag state changes MUST flow through a `GameplayEffect` applied via the GC’s effect application pipeline. This is a deliberate departure from UE4 GAS (which permits "loose tags") and is the property that makes replication of tag state tractable.

### 3.2 Component Relationships

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

### 3.3 Execution Model

The UGAS execution model follows a deterministic sequence for processing gameplay logic:

1.  *Input Processing*: Hardware inputs are mapped to Input Actions, which trigger Ability activation attempts.

2.  *Ability Activation*: The GC validates activation requirements (Tags, Costs, Cooldowns) before committing the Ability.

3.  *Effect Application*: Abilities apply Effects to Targets. Effects create Modifiers on Attributes and grant/remove Tags.

4.  *Attribute Recalculation*: Affected Attributes recalculate their Current Values based on active Modifiers.

5.  *Event Dispatch*: OnAttributeChanged events propagate to registered observers.

6.  *Cue Triggering*: Tag changes trigger appropriate Gameplay Cues on clients.

7.  *Replication*: State changes are replicated to networked clients according to the configured replication mode.

### 3.4 Threading Considerations

Implementations SHOULD consider the following threading guidelines:

- *Main Thread*: Ability activation, Effect application, and Attribute modification SHOULD occur on the main game thread to ensure deterministic ordering.

- *Async Tasks*: AbilityTasks MAY spawn background work but MUST return results to the main thread for state modification.

- *Replication*: Network replication MAY occur on dedicated networking threads but MUST synchronize with the main thread for state application.

- *Cues*: Gameplay Cue instantiation MAY occur on rendering threads but MUST NOT modify gameplay state.

# Part II: Core Components

## 4. Gameplay Controller(GC)

### 4.1 Responsibilities

The Gameplay Controlleris the central hub for all gameplay ability logic. An GC implementation MUST:

1.  Maintain collections of granted Abilities, active Effects, and owned Tags

2.  Manage one or more AttributeSets

3.  Process Ability activation requests

4.  Apply and remove Gameplay Effects

5.  Dispatch events for state changes

6.  Support network replication (if applicable)

### 4.2 Ownership Model

The GC implements a dual-actor ownership model:

Owner Actor  
The logical owner of the GC. The Owner is responsible for:

- GC lifecycle management

- Network authority

- Persistence across possession changes

Avatar Actor  
The world representation associated with the GC. The Avatar provides:

- Spatial position for targeting

- Animation and physics integration

- Visual representation

#### Same-Actor Configuration

For simple entities (AI-controlled enemies, destructible objects), the Owner and Avatar MAY be the same Actor:

    ┌─────────────────────────────┐
    │         AI ENEMY            │
    │  ┌───────────────────────┐  │
    │  │         GC            │  │
    │  │   Owner: this         │  │
    │  │   Avatar: this        │  │
    │  └───────────────────────┘  │
    └─────────────────────────────┘

#### Split-Actor Configuration

For player-controlled characters in networked games, the Owner and Avatar SHOULD be separate to ensure GC persistence across respawns:

    ┌─────────────────────────────┐        ┌─────────────────────────────┐
    │       PLAYER STATE          │        │      PLAYER CHARACTER       │
    │  (Persists entire session)  │        │  (Destroyed on death)       │
    │  ┌───────────────────────┐  │        │                             │
    │  │         GC            │──┼────────┼──▶ Avatar reference         │
    │  │   Owner: this         │  │        │                             │
    │  └───────────────────────┘  │        └─────────────────────────────┘
    └─────────────────────────────┘

### 4.3 Lifecycle

#### Initialization Sequence

1.  GC is instantiated on Owner Actor

2.  AttributeSets are registered with GC

3.  Owner and Avatar references are set

4.  Initial Abilities are granted

5.  Initial Effects are applied

6.  Replication is configured (if networked)

#### Possession Handling

When Avatar possession changes:

1.  Previous Avatar reference is cleared

2.  Active Effects targeting Avatar location are re-evaluated

3.  New Avatar reference is set

4.  Avatar-dependent Abilities are re-validated

#### Destruction Cleanup

1.  All active Effects are removed

2.  All granted Abilities are revoked

3.  Event subscriptions are cleared

4.  Network replication is terminated

### 4.4 Interface Specification

Implementations SHOULD provide an interface for GC discovery:

``` typescript
interface IAbilitySystemInterface {
  /**
   * Returns the Gameplay Controllerassociated with this entity.
   * @returns The GC instance, or null if not available
   */
  GetGameplayController(): GameplayController | null;
}
```

Actors participating in the ability system MUST implement this interface or provide an equivalent discovery mechanism.

### 4.5 Public API

The following methods define the core GC interface:

#### Effect Context Creation

``` typescript
/**
 * Creates a new Effect Context for outgoing effects.
 * @returns A handle to the new context
 */
MakeEffectContext(): EffectContextHandle;
```

#### Effect Spec Creation

``` typescript
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

``` typescript
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
 *
 * NETWORKED ENVIRONMENTS: A call originating on a client is speculative.
 * The server MUST validate instigator authority, ability ownership, target
 * reachability, and effect-class whitelist before executing the authoritative
 * application. See §13.7 for the full validation pipeline.
 *
 * @param target - The target GC
 * @param spec - The effect spec to apply
 * @param predictionKey - Optional prediction key for client-side prediction
 * @returns Handle to the active effect, or invalid handle if application failed
 */
ApplyGameplayEffectToTarget(
  target: GameplayController,
  spec: EffectSpecHandle,
  predictionKey?: PredictionKey
): ActiveEffectHandle;
```

#### Effect Removal

``` typescript
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

``` typescript
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

## 5. Attributes

### 5.1 Attribute Data Structure

An Attribute MUST implement the following data structure:

``` typescript
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

Base Value  
The permanent, persistent value of the Attribute. Base Values are modified ONLY by Instant effects and represent permanent changes such as leveling, permanent upgrades, or instant damage/healing.

Current Value  
The dynamically calculated result of the Base Value plus all active temporary Modifiers. Current Values are ephemeral and automatically recalculated when Modifiers are added or removed.

| Component     | Modification Source  | Persistence            |
|---------------|----------------------|------------------------|
| Base Value    | Instant Effects only | Persistent (saved)     |
| Current Value | All Modifier types   | Ephemeral (calculated) |

#### Instant Modifiers on the Base Value

An Instant effect applies each of its Modifiers **directly to the Base Value**, in authored order, according to the operation:

- `Add` / `AddPost` — add the (signed) magnitude to the Base Value.

- `Override` — set the Base Value to the magnitude.

- `Multiply` — scale the Base Value by `(1 + m)(1 + m)`, the same signed-bonus convention the Current-Value pipeline uses (§5.3): a magnitude of `+1.0` doubles the Base Value, `-0.25` removes 25%. Channel grouping is a Current-Value concept and does not apply to a Base-Value write — each Instant `Multiply` scales the Base Value independently, in authored order.

The result is then clamped to the Attribute’s declared bounds. These per-operation rules are **total**: an implementation MUST NOT silently drop any operation (a `Multiply` on an Instant effect is a Base-Value scale, not a no-op). An Instant `Multiply` with magnitude `0` is the identity (`times 1times 1`).

This applies only to **Instant** effects. A durational (Infinite / HasDuration) effect’s `Multiply` and `Divide` modifiers are Current-Value modifiers (§5.3) and are never written to the Base Value — including on the periodic ticks of a periodic durational effect, whose executions apply only `Add` / `AddPost` / `Override` to the Base Value (a periodic `Multiply`-to-base would double-count against the effect’s own Current-Value contribution and compound every tick). A percentage change that must be **permanent** is authored as an Instant `Multiply`; a percentage change that lasts **while an effect is active** is a durational `Multiply` in the Current-Value pipeline.

### 5.3 Modifier Pipeline

The Current Value calculation MUST follow a standardized pipeline to ensure mathematical consistency across implementations.

#### Formula

The Current Value $V_{current}$ is calculated as:

$$V_{current} = \max\left( V_{min},\ \min\left( V_{max},\ \left( V_{base} + \sum a_i \right) \times \prod_{c \in C} \left(1 + \sum_{k \in c} m_k\right) + \sum b_l \right) \right)$$

Where: - $V_{base}$ = Base Value - $a_i$ = Pre-multiply flat additive modifiers (`Add` operations) - $C$ = the set of distinct Channel values among active `Multiply` modifiers; each modifier without a `Channel` belongs to its own unique implicit singleton channel - $m_k$ = signed bonus magnitude for each `Multiply` modifier (e.g., `+0.25` for a +25% bonus, `−0.25` for a 25% penalty) - $b_l$ = Post-multiply flat additive modifiers (`AddPost` operations; very rare) - $V_{min}$, $V_{max}$ = clamping constraints

Note that clamping is not mandatory; the simplified form is:

$$V_{current} = \left( V_{base} + \sum a_i \right) \times \prod_{c \in C} \left(1 + \sum_{k \in c} m_k\right) + \sum b_l$$

#### Channel Aggregation

The channel product $\prod_{c \in C}\!\left(1 + \sum_{k \in c} m_k\right)$ is how the "damage bucket" design is expressed at the pipeline level:

- *Same channel → bonuses ADD.* All `Multiply` modifiers sharing a `Channel` value contribute their magnitudes additively. The channel’s effective factor is `1 + sum of magnitudes`. Two +20% bonuses in the same channel yield ×1.40, not ×1.44.

- *Different channels → factors MULTIPLY.* Each channel produces one effective factor; those factors are multiplied together. A ×1.40 channel and a ×1.30 channel yield ×1.82.

- *No channel → isolated singleton.* A `Multiply` modifier without a `Channel` is in its own implicit channel, so its contribution is `1 + magnitude` — independent of all other modifiers.

This is the primary tool for preventing linear power creep: bonuses from the same source category (e.g., "damage bonuses from gear") are additive within a channel, while bonuses from categorically different sources (e.g., "gear bonuses" vs. "legendary powers") are multiplicative across channels.

#### Order of Operations

The order of operations is CRITICAL for deterministic results:

1.  Sum all flat additive modifiers (`Add`): `flat = ΣAdd`

2.  Apply flat additions to Base Value: `value = Base + flat`

3.  Group `Multiply` modifiers by `Channel`. For each channel, sum the magnitudes: `channel_factor = 1 + Σm_k`

4.  Multiply all channel factors together and apply: `value *= Π channel_factor`

5.  Add sum of all post-multiply flat additive modifiers (`AddPost`): `value += ΣAddPost`

6.  Apply `Override` modifiers (if any, replacing the result) — see conflict resolution below

7.  Apply clamping constraints

#### Override Conflict Resolution

When multiple active Override modifiers target the same Attribute simultaneously, implementations MUST resolve the conflict deterministically using the following ordered rules:

1.  *Priority wins*: The Override modifier from the `GameplayEffect` with the highest `Priority` value replaces the result. Lower-priority Overrides are ignored for that Attribute.

2.  *Last-applied wins on tie*: If two or more competing Override modifiers share the same `Priority`, the one from the most recently applied effect wins (LIFO order, determined by application timestamp).

`Priority` defaults to `0`. Effects intended to be overrideable by other effects should use lower priority values (e.g. `-10`); effects that must always dominate should use higher values (e.g. `100`).

> *Example:* A "Freeze" effect sets `MoveSpeed` Override to `0` at Priority `10`. A "Slow\` effect also sets an Override to `50` at Priority `5`. The Freeze wins because `10 > 5`. If a "Root" effect then sets an Override to `0` at Priority `10`, it ties with Freeze — the more recently applied effect’s Override is used, but the end result is identical.

#### Example Calculation

Given: - Base Value: 100 - Add Modifier 1: +20 - Add Modifier 2: +10 - Additive Percentage 1: +10% (0.1) - Additive Percentage 2: +15% (0.15) - Multiplicative 1: 1.5× - Multiplicative 2: 2.0× - No Bonus Flat

Calculation:

    Step 1-2: 100 + 20 + 10 = 130
    Step 3-4: 130 × (1 + 0.1 + 0.15) = 130 × 1.25 = 162.5
    Step 5-6: 162.5 × 1.5 × 2.0 = 487.5

Current Value = 487.5

### 5.4 Clamping and Bounds

Attributes MAY define minimum and maximum constraints. Constraints can be:

Static Values  
Fixed numeric bounds that do not change.

``` yaml
Clamping:
  Min: 0.0
  Max: 100.0
```

Dependent Attribute References  
Bounds referencing other Attributes, enabling dynamic constraints.

``` yaml
Clamping:
  Min: 0.0
  Max: "MaxHealth"  # References another attribute
```

When a constraint references another Attribute: 1. The referenced Attribute’s Current Value is used as the bound 2. Changes to the referenced Attribute trigger recalculation of dependent Attributes 3. Circular dependencies MUST NOT be created

### 5.5 Attribute Metadata

Attribute Metadata defines static configuration:

*Category* - `Resource`: Consumable values that are spent and recovered (Health, Mana, Stamina) - `Statistic`: Derived values used in calculations (Damage, Defense, CritChance) - `Meta`: Internal values used only for calculations, not displayed to players

*Replication Flags* - `None`: Not replicated - `OwnerOnly`: Replicated only to owning client - `All`: Replicated to all clients

### 5.6 OnAttributeChanged Event

Any change to an Attribute—whether to Base Value or Current Value—MUST trigger an OnAttributeChanged event.

#### Event Payload

``` typescript
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
  Source?: GameplayController;

  /** Target of the change */
  Target: GameplayController;
}
```

#### Subscription Model

Observers SHOULD register for attribute change notifications:

``` typescript
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

``` yaml
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

## 6. Attribute Sets

### 6.1 Purpose and Composition

An Attribute Set is a logical container grouping related Attributes. Attribute Sets provide:

- *Modularity*: Actors can mix and match sets based on capabilities

- *Organization*: Related Attributes are defined together

- *Reusability*: Common sets can be shared across Actor types

- *Serialization Boundary*: Sets define units for save/load operations

### 6.2 Set Registration with GC

Attribute Sets MUST be registered with an GC before use:

``` typescript
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

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/attribute_set.json
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

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/attribute_set.json
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

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/attribute_set.json
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

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/attribute_set.json
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

1.  Validate all dependencies exist before registration

2.  Ensure proper recalculation order when dependencies change

3.  Prevent circular dependency chains

### 6.5 Schema Definition

``` yaml
AttributeSet:
  Name: string                    # Required: Unique set identifier
  Dependencies: [string]          # Optional: Required attribute sets
  Attributes: [Attribute]         # Required: List of attributes
  Metadata:                       # Optional: Additional configuration
    DisplayName: string
    Description: string
```

## 7. Gameplay Tags

### 7.1 Hierarchical Naming Convention

Gameplay Tags use hierarchical dot-notation to represent semantic categories:

    Category.Subcategory.Leaf

Examples: - `State.Debuff.Stunned.Magic` - `Ability.Type.Melee.Slash` - `DamageType.Physical.Blunt` - `Cooldown.Ability.Fireball` - `GameplayCue.Impact.Fire`

#### Naming Rules

1.  Each segment MUST use PascalCase

2.  Hierarchies SHOULD NOT exceed 5 levels

3.  Leaf tags SHOULD be specific; parent tags SHOULD be categorical

4.  Reserved prefixes:

    - `GameplayCue.*` - Cue trigger tags

    - `Cooldown.*` - Cooldown tracking tags

    - `State.*` - Actor state tags

    - `Ability.*` - Ability classification tags

    - `DamageType.*` - Damage classification tags

### 7.2 Tag Container

A Tag Container is a collection of tags associated with an entity.

#### Internal Representation

A `TagContainer` MUST maintain *reference counts* per tag, not a simple set. Multiple concurrent Effects can grant the same tag; each grant increments the count; each removal decrements it. The tag is considered present only while its count is greater than zero.

``` typescript
struct TagContainer {
  /**
   * Grant counts for every explicitly-held tag.
   * A tag is "explicitly present" when its count > 0.
   * Managed exclusively by the GC Effect application pipeline.
   */
  ExplicitTagCounts: Map<Tag, number>;

  /**
   * Cumulative grant counts for all explicit tags AND their ancestor tags.
   * Automatically maintained by AddTag/RemoveTag: adding tag T also
   * increments the count of every ancestor of T; removing T decrements them.
   * Used to answer MatchesTag queries in O(1).
   */
  AllTagCounts: Map<Tag, number>;
}
```

#### Operations

``` typescript
interface TagContainer {
  /**
   * @internal Reserved for the GC Effect application pipeline.
   * Ability implementations MUST NOT call this directly.
   * Grant tags via a GameplayEffect with GrantedTags instead.
   *
   * Increments the grant count of `tag` in ExplicitTagCounts and the grant
   * count of every ancestor of `tag` in AllTagCounts.
   * Dispatches an OnTagChanged event ONLY when the count transitions 0 → 1
   * (i.e. the tag was previously absent). Subsequent grants of the same tag
   * by additional Effects increment the count silently.
   */
  AddTag(tag: Tag): void;

  /**
   * @internal Reserved for the GC Effect application pipeline.
   * Ability implementations MUST NOT call this directly.
   * Remove tags by removing the GameplayEffect that granted them.
   *
   * Decrements the grant count of `tag` in ExplicitTagCounts and the grant
   * count of every ancestor of `tag` in AllTagCounts.
   * MUST NOT decrement below 0; implementations MUST treat an underflow as
   * a logic error (assert / log error and skip).
   * Dispatches an OnTagChanged event ONLY when the count transitions 1 → 0
   * (i.e. the tag is now fully absent). While the count remains > 1, no
   * event is dispatched.
   */
  RemoveTag(tag: Tag): void;

  /**
   * Returns the current grant count for `tag` in ExplicitTagCounts.
   * Useful for "how many stacks of Burning are active?" queries.
   * Returns 0 if the tag is not present.
   */
  GetTagCount(tag: Tag): number;

  /** Returns true if no explicit tags have a count > 0. */
  IsEmpty(): boolean;

  /** Returns the number of distinct explicit tags with count > 0. */
  Count(): number;

  /**
   * @internal Reserved for the GC Effect application pipeline.
   * Sets all counts to 0 and dispatches OnTagChanged for every tag whose
   * count was > 0. Used during GC teardown only.
   */
  Clear(): void;
}
```

### 7.3 Query Operations

| Operation            | Map queried         | Semantics                                                                               | Example                                                |
|----------------------|---------------------|-----------------------------------------------------------------------------------------|--------------------------------------------------------|
| `MatchesTag(T)`      | `AllTagCounts`      | True if `AllTagCounts[T] > 0` — matches T itself or any descendant of T that is present | Checking for any type of "Stunned" status              |
| `MatchesTagExact(T)` | `ExplicitTagCounts` | True if `ExplicitTagCounts[T] > 0` — exact tag only, no hierarchy                       | Immunity to "Stunned.Magic" but not "Stunned.Physical" |
| `GetTagCount(T)`     | `ExplicitTagCounts` | Returns `ExplicitTagCounts[T]` (0 if absent)                                            | "How many stacks of Burning?"                          |
| `HasAny(Container)`  | `AllTagCounts`      | True if any tag in Container has `AllTagCounts > 0`                                     | Spell that affects "Undead" OR "Demon"                 |
| `HasAll(Container)`  | `AllTagCounts`      | True if every tag in Container has `AllTagCounts > 0`                                   | Combo requiring "Chilled" AND "Vulnerable"             |
| `HasNone(Container)` | `AllTagCounts`      | True if no tag in Container has `AllTagCounts > 0`                                      | Ability blocked by any "Immunity" tag                  |

#### Query Examples

``` typescript
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

When a tag is added to a container, the grant counts of all ancestor tags in `AllTagCounts` are incremented by the same amount. When a tag is removed, ancestor counts are decremented symmetrically. This means `MatchesTag` on a parent tag is always consistent with the sum of grants on its descendants:

    AddTag("State.Debuff.Stunned.Magic")
      ExplicitTagCounts["State.Debuff.Stunned.Magic"] = 1
      AllTagCounts["State.Debuff.Stunned.Magic"]      = 1
      AllTagCounts["State.Debuff.Stunned"]             = 1  ← propagated
      AllTagCounts["State.Debuff"]                     = 1  ← propagated
      AllTagCounts["State"]                            = 1  ← propagated

    AddTag("State.Debuff.Stunned.Magic")  # second effect grants same tag
      ExplicitTagCounts["State.Debuff.Stunned.Magic"] = 2
      AllTagCounts["State.Debuff.Stunned.Magic"]      = 2
      AllTagCounts["State.Debuff.Stunned"]             = 2
      AllTagCounts["State.Debuff"]                     = 2
      AllTagCounts["State"]                            = 2

    RemoveTag("State.Debuff.Stunned.Magic")  # first effect expires
      ExplicitTagCounts["State.Debuff.Stunned.Magic"] = 1  # still present!
      AllTagCounts["State.Debuff.Stunned.Magic"]      = 1
      AllTagCounts["State.Debuff.Stunned"]             = 1
      ...
      # MatchesTag("State.Debuff.Stunned") → still true, no event dispatched

    RemoveTag("State.Debuff.Stunned.Magic")  # second effect expires
      ExplicitTagCounts["State.Debuff.Stunned.Magic"] = 0  # now absent
      AllTagCounts["State.Debuff.Stunned.Magic"]      = 0
      AllTagCounts["State.Debuff.Stunned"]             = 0
      ...
      # OnTagChanged dispatched for the leaf and each ancestor that hit 0

This enables hierarchical queries where `MatchesTag("State.Debuff")` matches any active debuff, and the match remains valid as long as any descendant tag has a count \> 0.

### 7.5 State Representation via Tags

Tags are the primary method for representing Actor states. Instead of boolean flags:

``` typescript
// Avoid this pattern
if (actor.isStunned && !actor.isImmune) { ... }

// Use tag queries
if (actor.Tags.MatchesTag("State.Debuff.Stunned") &&
    !actor.Tags.MatchesTag("Status.Immune.Stun")) { ... }
```

This decouples the "How" of a state (animation, logic freeze) from the "What" of the state (the Tag).

### 7.6 Schema Definition

``` yaml
TagDefinition:
  Tag: string                     # Full hierarchical tag name
  Description: string             # Human-readable description
  AllowMultiple: boolean          # Can multiple instances exist? (default: false)
  DevComment: string              # Developer notes
```

Tag definitions MAY be collected in a tag registry:

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_tag.json
Tags:
  - Tag: "State.Debuff.Stunned"
    Description: "Actor is unable to perform actions"

  - Tag: "State.Debuff.Stunned.Magic"
    Description: "Stun caused by magical effect"

  - Tag: "State.Debuff.Stunned.Physical"
    Description: "Stun caused by physical impact"

  - Tag: "Status.Immune.Stun"
    Description: "Actor is immune to stun effects"
```

## 8. Gameplay Abilities

### 8.1 Ability Definition

A Gameplay Ability is a self-contained unit of logic defining an action an Actor can perform. Unlike simple function calls, Abilities are asynchronous, stateful objects with defined lifecycles.

#### Ability Class Structure

``` typescript
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

  /**
   * Tags applied to the owner while this ability is active.
   * Implementations MUST apply these as an auto-generated Infinite GameplayEffect
   * on CommitAbility and remove that effect on EndAbility/CancelAbility.
   * Direct tag mutation is prohibited (see §3.1).
   */
  ActivationOwnedTags: TagContainer;

  /** Cost effect applied on commit */
  CostEffect?: GameplayEffectClass;

  /** Cooldown effect applied on commit */
  CooldownEffect?: GameplayEffectClass;

  /** Called when ability is activated */
  abstract ActivateAbility(context: AbilityContext): void;

  /** Called when ability ends */
  abstract EndAbility(wasCancelled: boolean): void;
}
```

#### AbilitySpec (Instance Data)

``` typescript
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

  /**
   * Handle to the auto-generated Infinite Effect that grants ActivationOwnedTags.
   * Set by CommitAbility; cleared by EndAbility/CancelAbility.
   * Undefined when the ability is not active.
   */
  ActiveOwnedTagsHandle?: ActiveEffectHandle;
}
```

### 8.2 Lifecycle State Machine

The base lifecycle assumes the `Activating (Validating)` checks of §8.3 are synchronous: an ability that passes them proceeds straight to Commit (§8.4). Some activations, however, require **asynchronous** server-side validation (anti-cheat, remote inventory, entitlement/auth) whose result is not known synchronously. The `PendingConfirmation` state models that unresolved authoritative outcome; its full normative treatment, including the client-side prediction path, is in §8.8.

`PendingConfirmation` sits between `Activating (Validating)` and `Commit`. Synchronous-only abilities skip it and go `Validating → Commit` exactly as before; abilities that require asynchronous validation (§8.8) route through it. Under client-side prediction (§13.8) the predicting client may instead **speculatively** enter Active while the authoritative side holds the activation in `PendingConfirmation` until the server confirms or rejects the prediction key — the reject edge rolls the speculative activation back to `Granted` via §13.5.

                        ┌──────────────┐
                        │  NotGranted  │
                        └──────┬───────┘
                               │ Grant
                               ▼
                        ┌──────────────┐
            ┌──────────▶│   Granted    │◀────────────────┐
            │           │  (Inactive)  │◀──────────┐     │
            │           └──────┬───────┘           │     │
            │                  │ TryActivate       │     │
            │                  ▼                   │     │
            │           ┌──────────────┐           │     │
            │           │  Activating  │───────────┤     │
            │           │ (Validating) │  Fail     │     │
            │           └──┬────────┬──┘           │     │
            │   sync-only  │        │ requires      │     │
            │  (§8.3 pass) │        │ async         │     │
            │              │        ▼ validation    │     │
            │              │ ┌────────────────────┐ │     │
            │              │ │ PendingConfirmation │─┘     │
            │              │ │  (awaiting server   │ Fail  │
            │              │ │     validation)     │ (async│
            │              │ └─────────┬───────────┘ reject)│
            │              │           │ Confirm            │
            │              │           │ (async success)    │
            │              ▼           ▼                    │
            │           ┌──────────────────┐                │
            │           │      Commit      │ ───────────────┘
            │           │ (cost/cooldown)  │  RejectPrediction
            │           └────────┬─────────┘  -> rollback (§13.5)
            │                    │ proceed
            │                    ▼
            │           ┌──────────────────┐
            │           │      Active      │   Client prediction (§13.8):
            │           │   (Executing)    │   client enters Active SPECULATIVELY
            │           │                  │   while server stays in
            │           └────────┬─────────┘   PendingConfirmation until the
            │                    │ End/Cancel   prediction key resolves.
            │                    ▼              ConfirmPrediction -> no change;
            │           ┌──────────────────┐    RejectPrediction -> rollback to
            └───────────│      Ending      │    Granted via §13.5.
                        └──────────────────┘

### 8.3 Activation Requirements

Before an Ability can activate, the following checks MUST pass:

1.  *Granted Check*: Ability must be granted to the GC

2.  *Not Already Active*: Ability must not currently be active (unless configured for multiple instances)

3.  *Required Tags*: Owner must have all tags in `ActivationRequiredTags`

4.  *Blocked Tags*: Owner must NOT have any tags in `ActivationBlockedTags`

5.  *Cost Verification*: If CostEffect is defined, owner must have sufficient resources

6.  *Cooldown Verification*: Cooldown tag must not be present

``` typescript
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

1.  Cost Effect is applied (resources consumed)

2.  Cooldown Effect is applied (cooldown tag granted)

3.  Activation Owned Tags are granted

4.  Ability proceeds to execution

``` typescript
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

  // Grant activation tags via an auto-generated Infinite Effect.
  // Direct tag mutation is prohibited (§3.1); all tag state flows through Effects.
  if (!spec.AbilityClass.ActivationOwnedTags.IsEmpty()) {
    const ownedTagsSpec = MakeOwnedTagsEffect(spec.AbilityClass.ActivationOwnedTags, spec.Level);
    spec.ActiveOwnedTagsHandle = ApplyGameplayEffectToSelf(ownedTagsSpec);
  }

  return true;
}
```

### 8.5 Costs and Cooldowns as Effects

Costs and Cooldowns are NOT separate variables but are implemented as specialized Gameplay Effects.

#### Cost Effect Pattern

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
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

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
Name: "GE_Fireball_Cooldown"
DurationPolicy: HasDuration
Duration:
  Type: ScalableFloat
  Value: 5.0  # 5 second cooldown
GrantedTags:
  - "Cooldown.Ability.Fireball"
```

This pattern enables external modification of costs and cooldowns. For example, a "Mana Efficiency" buff could apply a multiplier to all cost effects:

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
Name: "GE_ManaEfficiency_Buff"
DurationPolicy: HasDuration
Duration:
  Type: ScalableFloat
  Value: 30.0
Modifiers:
  - Attribute: "ManaCostMultiplier"
    Operation: Multiply
    Magnitude:
      Type: ScalableFloat
      Value: -0.25  # -25% mana cost
```

### 8.6 Cancellation and Interruption

Abilities may be cancelled by:

1.  *Self-Cancellation*: Ability logic calls EndAbility(true)

2.  *External Cancel*: Another system calls CancelAbility on the GC

3.  *Cancel Tags*: An Effect grants a tag in the Ability’s `CancelAbilitiesWithTags` set

4.  *Owner Death*: Owner’s Health reaches zero

``` typescript
function CancelAbility(handle: AbilitySpecHandle): void {
  const spec = GetAbilitySpec(handle);
  if (!spec.IsActive) return;

  // Remove activation tags by removing the Effect that granted them.
  // Direct tag mutation is prohibited (§3.1).
  if (spec.ActiveOwnedTagsHandle) {
    RemoveActiveGameplayEffect(spec.ActiveOwnedTagsHandle);
    spec.ActiveOwnedTagsHandle = undefined;
  }

  // Call ability's end handler
  spec.AbilityInstance.EndAbility(true /* wasCancelled */);

  // Cleanup active tasks
  CancelAllAbilityTasks(handle);

  spec.IsActive = false;
}
```

### 8.7 Schema Definition

``` yaml
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

  AsyncValidation:                # Optional: async server validation (§8.8)
    Required: boolean             # If true, route through PendingConfirmation
    Kind: string                  # AntiCheat | RemoteInventory | Entitlement | Custom
    TimeoutMs: number             # Max wait before treating as async failure
    Predicted: boolean            # If true, client may speculatively Activate (§13.8)

  Tasks:                          # Sequential task definitions
    - Type: string                # Task type name
      Params: object              # Task-specific parameters

  Metadata:
    DisplayName: string
    Description: string
    Icon: string
```

### 8.8 Asynchronous Validation and Predicted Activation

The lifecycle of §8.2 assumes the §8.3 activation checks are synchronous. Some activations require **asynchronous** server-side validation whose result is not available in the activating frame — for example server-side anti-cheat confirmation, a resource check against a remote inventory service, or multi-step authentication for a premium consumable. Under the client-side prediction this specification mandates (§13.4–§13.8), the client predicts success synchronously and goes Active, but the server MAY reject the activation after its asynchronous validation resolves. Without a modeled state for the unresolved authoritative outcome, that late rejection has no defined transition — the race condition this section resolves.

This section introduces an explicit lifecycle state, `PendingConfirmation`, for an activation that has passed the synchronous §8.3 checks but whose authoritative outcome is not yet known. It is additive to §8.2–§8.7 and MUST NOT contradict them, and it builds on the networking model of §13.5, §13.7, and §13.8 without modifying it. Where this section uses MUST/SHOULD/MAY it carries the same RFC-2119 force as the rest of this specification.

#### 8.8.1 The PendingConfirmation State

`PendingConfirmation` denotes an activation that has passed the synchronous §8.3 checks but whose authoritative result is still outstanding pending asynchronous validation. While an activation is in `PendingConfirmation`:

1.  It MUST NOT have committed (§8.4). Cost and Cooldown Effects MUST NOT have been applied, and `ActivationOwnedTags` MUST NOT have been granted, on the side that is awaiting confirmation. Commit is reached only on confirmation.

2.  It MUST NOT be executing ability Tasks that produce authoritative gameplay mutations. An implementation MAY run non-authoritative presentation work (e.g. a wind-up animation or a local-visual cue) while pending, consistent with the speculative/local-visual rule of §13.7 and §13.8.4.

3.  `spec.IsActive` MUST be `false` on the authoritative side while pending; the ability is not yet Active in the §8.2 sense. (Under prediction, the predicting client MAY report a **speculative** Active locally — see §8.8.4.)

An ability is eligible for `PendingConfirmation` only when it is marked as requiring asynchronous validation. The OPTIONAL `AsyncValidation` block of the §8.7 schema is the normative marker: when `AsyncValidation.Required` is `true`, an activation that passes the §8.3 checks MUST enter `PendingConfirmation` before Commit rather than committing synchronously. When the marker is absent or `Required` is `false`, the ability retains the synchronous §8.2 behaviour (`Validating → Commit`) unchanged. An implementation MAY represent the marker by other means, but the resulting semantics MUST match this section.

#### 8.8.2 Transition Table

The following transitions are added to §8.2. All other §8.2 transitions are unchanged.

| From                    | To                   | Trigger / Condition                                                                                                                                                                                                                      |
|-------------------------|----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Activating (Validating) | Commit               | Synchronous §8.3 checks pass AND the ability does NOT require async validation (`AsyncValidation.Required` is absent/false). Unchanged from §8.2.                                                                                        |
| Activating (Validating) | PendingConfirmation  | Synchronous §8.3 checks pass AND the ability requires async validation (`AsyncValidation.Required == true`). No cost/cooldown consumed yet.                                                                                              |
| Activating (Validating) | Granted (via Fail)   | A synchronous §8.3 check fails. Unchanged from §8.2.                                                                                                                                                                                     |
| PendingConfirmation     | Commit → Active      | Asynchronous validation succeeds (server authority), or `ConfirmPrediction(key)` is received (§13.7) for a predicted activation. Cost/Cooldown/`ActivationOwnedTags` are applied at Commit (§8.4).                                       |
| PendingConfirmation     | Granted (via Fail)   | Asynchronous validation fails, `AsyncValidation.TimeoutMs` elapses, or `RejectPrediction(key)` is received (§13.7). No cost/cooldown was consumed. For a predicted speculative Active, the client MUST roll back via §13.5 (see §8.8.4). |
| PendingConfirmation     | Granted (via Cancel) | The activation is cancelled or interrupted while pending (§8.6, §8.8.5).                                                                                                                                                                 |

A `PendingConfirmation` activation has, by construction, not consumed cost or cooldown; therefore both the Fail and Cancel exits from `PendingConfirmation` return the ability to `Granted` with no resources spent and no cooldown started.

#### 8.8.3 Path A — Server-Authoritative Async Validation (No Prediction)

This is the pure server-authoritative flow (prediction disabled, or `AsyncValidation.Predicted` not set). After the synchronous §8.3 checks pass, an ability requiring async validation enters `PendingConfirmation` **before** Commit. The server initiates the asynchronous validation (anti-cheat, remote inventory, entitlement/auth). The activation remains pending — no cost, no cooldown, not executing — until the validation resolves:

- On asynchronous **success**, the activation proceeds to Commit (§8.4) and then to Active (§8.2). This is the only point at which cost and cooldown are consumed.

- On asynchronous **failure** (including a `TimeoutMs` expiry), the activation transitions to Fail and back to `Granted`. Because Commit was never reached, no cost or cooldown was consumed and `ActivationOwnedTags` were never granted; no rollback of authoritative gameplay state is required.

``` typescript
// Server-authoritative async validation (no client prediction).
function TryActivateAbility_ServerAsync(spec: AbilitySpec): void {
  // 1. Synchronous §8.3 checks first.
  if (!CanActivateAbility(spec)) {
    Fail(spec); // -> Granted (§8.2)
    return;
  }

  // 2. Synchronous-only ability: commit immediately (unchanged §8.2 path).
  if (!spec.AbilityClass.AsyncValidation?.Required) {
    CommitAbility(spec); // §8.4
    ActivateAbility(spec);
    return;
  }

  // 3. Async ability: enter PendingConfirmation BEFORE commit.
  //    No cost/cooldown consumed; ability is not yet Active.
  spec.State = AbilityState.PendingConfirmation;
  spec.IsActive = false;

  BeginAsyncValidation(spec, spec.AbilityClass.AsyncValidation, (result) => {
    if (spec.State !== AbilityState.PendingConfirmation) {
      return; // Cancelled/interrupted while pending (§8.8.5) — ignore late result.
    }
    if (result.ok) {
      CommitAbility(spec);   // §8.4 — cost/cooldown applied HERE, not before.
      ActivateAbility(spec); // -> Active
    } else {
      Fail(spec);            // -> Granted; nothing was consumed.
    }
  });
}
```

While an activation is pending under Path A, an implementation MUST define how concurrent input and cancellation are treated; the RECOMMENDED behaviour is in §8.8.5.

#### 8.8.4 Path B — Client-Side Prediction

This is the flow when prediction is enabled for the ability (`AsyncValidation.Predicted == true`) and the activation is predicted by the owning client per §13.8. It resolves the race directly: the authoritative side now has a modeled `PendingConfirmation` state to occupy while the client is speculatively Active, so a late server rejection has the defined `RejectPrediction → rollback → Granted` transition rather than an undefined one.

1.  **Client (speculative).** The client runs the synchronous §8.3 checks locally and, if they pass, **predictively commits and enters Active (speculative)**, carrying a `PredictionKey` generated per §13.8.1. Before predicting it MUST capture rollback state via `CaptureState()` (§13.8.3) and it MUST respect the bounded prediction window of §13.8.2. The speculative Active MUST be treated as unconfirmed (§13.7); any effect it applies to a non-owned GC is speculative/local-visual only (§13.8.4).

2.  **Server (authoritative).** The server receives the predicted activation, runs the synchronous checks, and holds the activation in `PendingConfirmation` while its asynchronous validation runs. The server does NOT mirror the client’s speculative Active; it commits only when validation succeeds.

3.  **Confirmation.** On asynchronous success the server emits `ConfirmPrediction(key)` (§13.7). The client’s speculative Active is confirmed with no visible change — the predicted commit becomes authoritative. The server itself transitions `PendingConfirmation → Commit → Active`.

4.  **Rejection.** On asynchronous failure (or `TimeoutMs`) the server emits `RejectPrediction(key)` (§13.7). The client MUST roll back the speculative activation via the §13.5 reconciliation path, restoring the `CaptureState()` snapshot of §13.8.3 (which includes ability activation state, so the speculatively-consumed cost/cooldown and granted `ActivationOwnedTags` are reverted), and the ability returns to `Granted`. The authoritative server side, which only ever held `PendingConfirmation`, transitions to Fail → `Granted` without ever having committed.

``` typescript
// Client: predict, then reconcile on the server's confirm/reject.
function TryActivateAbility_Predicted_Async(handle: AbilitySpecHandle): void {
  const spec = GetAbilitySpec(handle);
  if (!CanActivateAbility(spec)) return;       // local synchronous §8.3 checks

  // Window guard (§13.8.2) — do not predict past the bounded window.
  if (!PredictionWindowAllowsNewActivation()) return;

  const key = GeneratePredictionKey();         // §13.8.1
  this.PredictedActivations.set(key, {
    Handle: handle,
    Timestamp: GetCurrentTime(),
    State: CaptureState()                       // §13.8.3 — owning GC only
  });

  // Predictive commit + speculative Active (unconfirmed, §13.7).
  CommitAbility(spec);
  ActivateAbility(spec);                        // speculative Active

  Server_TryActivateAbility(handle, key);       // server holds PendingConfirmation
}

// Client: server outcome of the predicted (async-validated) activation.
function OnServerActivationResponse_Async(key: PredictionKey, ok: boolean): void {
  const prediction = this.PredictedActivations.get(key);
  if (!prediction) return;

  if (!ok) {
    // RejectPrediction: roll back speculative activation via §13.5,
    // restoring the §13.8.3 snapshot. Ability returns to Granted.
    RollbackToState(prediction.State);
  }
  // ConfirmPrediction: no visible change; predicted commit was correct.
  this.PredictedActivations.delete(key);
}
```

Because a predicted activation participates in the prediction model, it is bound by the same group and key rules: if it is part of a multi-ability prediction group it is confirmed or rejected atomically with that `PredictionKey.Base` (§13.8.4), so a chained activation predicted off this one is never left confirmed while this one is rolled back.

#### 8.8.5 Interaction with Cancellation, Interruption, and the Prediction Window

**Cancellation while pending (§8.6).** A `PendingConfirmation` activation MAY be cancelled or interrupted by any of the §8.6 mechanisms (self-cancel, external `CancelAbility`, a cancel tag, or owner death) before its asynchronous validation resolves. On such a cancel the ability MUST leave `PendingConfirmation` and return to `Granted`. Because nothing was committed, the §8.6 teardown is reduced: there are no committed cost/cooldown effects to reverse and no `ActiveOwnedTagsHandle` to remove (it is set only at Commit, §8.4). An implementation MUST NOT consume cost or cooldown as a side effect of cancelling a pending activation.

**In-flight async validation.** When a pending activation is cancelled, an implementation SHOULD attempt to abort the in-flight asynchronous validation, but MUST tolerate a validation result that arrives after the cancel. A late result for an activation that is no longer in `PendingConfirmation` MUST be discarded (it MUST NOT retroactively commit, re-activate, or consume resources). For the predicted Path B, a cancel before resolution MUST still roll back the speculative activation via §13.5 if the server subsequently rejects, and a late `ConfirmPrediction` for an already-cancelled key MUST NOT resurrect the activation.

**Prediction window bound (§13.8.2).** A speculative Active awaiting confirmation is server-unconfirmed predicted state and therefore counts against the bounded prediction window of §13.8.2. A client MUST NOT remain speculatively Active past that window while awaiting confirmation: if the window bound (`MaxPredictionMillis` / `MaxPredictionFrames`) is reached before `ConfirmPrediction`/`RejectPrediction` arrives, the client MUST fall back to awaiting server authority per §13.8.2 — surrendering the speculative outcome and applying authoritative state on the next update — rather than holding the unconfirmed activation indefinitely. An asynchronous validation whose expected latency exceeds the prediction window SHOULD be modelled as server-authoritative (Path A, `Predicted == false`) so the user is not shown a speculative outcome that routinely exceeds the window and rolls back.

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
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
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
   * - AddPost:  Post-multiply flat additive (pipeline step 7; very rare)
   * - Multiply: Multiplicative factor (pipeline step 6)

   * - Override: Replace the computed value entirely (pipeline step 8)
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
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

## 10. Ability Tasks

### 10.1 Purpose and Design

Ability Tasks are specialized asynchronous nodes that pause ability execution until a specific trigger condition is met. Tasks enable complex, multi-stage abilities to be written in a linear, readable fashion while executing asynchronously across frames or network ticks.

Tasks leverage the Observer design pattern for efficiency. Instead of polling a condition every frame, the ability registers a task and goes dormant. When the trigger condition is met, the task "wakes up" the ability and execution continues.

### 10.2 Task Lifecycle

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

*Instantiation*: Task is created with configuration parameters *Activation*: Task registers with relevant systems (timers, events, physics) *Tick* (optional): Some tasks require per-frame updates (see §10.6) *Completion*: Trigger condition met; ability execution resumes *Cancellation*: Task is aborted (ability cancelled, owner died)

### 10.3 Predefined Task Categories

| Category    | Trigger            | Example Tasks                        |
|-------------|--------------------|--------------------------------------|
| Temporal    | Timer expiry       | WaitDelay, WaitGameTime              |
| Event-Based | Gameplay event     | WaitGameplayEvent, WaitTagChanged    |
| Input-Based | Input state change | WaitInputRelease, WaitInputPressed   |
| State-Based | Tag change         | WaitTagAdded, WaitTagRemoved         |
| Spatial     | Collision/overlap  | WaitOverlap, WaitForTarget           |
| Animation   | Montage notify     | WaitAnimationEvent, WaitMontageEnded |

#### WaitDelay

Waits for a specified duration.

``` typescript
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

``` typescript
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

``` typescript
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

``` typescript
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

1.  Extend the base AbilityTask class

2.  Implement OnActivate() for setup

3.  Implement cleanup in OnEndTask()

4.  Provide delegate/event outputs for ability continuation

5.  Handle cancellation gracefully

``` typescript
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

1.  All active Tasks are cancelled

2.  Task event subscriptions are cleared

3.  Task resources are released

``` typescript
function EndAbility(wasCancelled: boolean): void {
  // Cancel all active tasks
  for (const task of this.ActiveTasks) {
    task.Cancel();
  }
  this.ActiveTasks.Clear();

  // Remove activation-owned tags by removing the Effect that granted them.
  // This is the normal (non-cancelled) end path; CancelAbility handles the cancel path.
  const spec = GC.GetAbilitySpec(this.Handle);
  if (spec?.ActiveOwnedTagsHandle) {
    GC.RemoveActiveGameplayEffect(spec.ActiveOwnedTagsHandle);
    spec.ActiveOwnedTagsHandle = undefined;
  }

  // Continue with ability end logic...
}
```

### 10.6 Tick Budgeting and Performance

Most tasks are event-driven and impose no per-frame cost: as described in §10.1, an ability registers a task, goes dormant, and is woken only when the trigger fires. A subset of tasks, however, cannot be expressed as a single subscription and require periodic re-evaluation. The clearest example is the *Spatial* category (§10.3): `WaitOverlap` and `WaitForTarget` poll physics queries to detect overlaps or acquire targets.

Ticking tasks scale multiplicatively with both ability complexity and actor count. An ability running five concurrent spatial tasks across 100 simultaneous actors performs 500 physics queries per frame. Without throttling, prioritisation, or visibility into per-task cost, this class of task becomes the dominant performance hazard of the system on large-scale titles, while remaining negligible on small ones.

This section defines RECOMMENDED mechanisms for bounding that cost. The base `AbilityTask` SHOULD expose the controls described below, and the runtime SHOULD honour them when scheduling task ticks. Event-, state-, and input-driven tasks are never ticked and are unaffected.

#### Per-Task Tick Throttling

A ticking task SHOULD support a configurable tick interval rather than ticking every frame. Implementations SHOULD expose a `TickInterval` on the base task, expressed in seconds, where `0` means "tick every frame". When `TickInterval > 0`, the runtime MUST NOT tick the task more frequently than the interval; it SHOULD accumulate elapsed time and evaluate once per elapsed interval.

``` typescript
abstract class AbilityTask {
  // Seconds between Tick() evaluations. 0 = every frame (default).
  TickInterval: float = 0;
  // Higher values tick first when the per-frame budget is exhausted. Default 0.
  Priority: int = 0;

  private accumulated: float = 0;

  // Called by the runtime each frame for tasks that require ticking.
  InternalTick(deltaTime: float): void {
    if (this.TickInterval <= 0) {
      this.Tick(deltaTime);
      return;
    }
    this.accumulated += deltaTime;
    if (this.accumulated >= this.TickInterval) {
      this.Tick(this.accumulated);  // pass real elapsed time, not the nominal interval
      this.accumulated = 0;
    }
  }

  protected abstract Tick(deltaTime: float): void;
}
```

Throttling trades responsiveness for cost. The interval SHOULD be chosen per task according to how quickly the observed condition changes and how tolerant the gameplay is to latency:

| Category                    | Recommended Interval | Rationale                                                                       |
|-----------------------------|----------------------|---------------------------------------------------------------------------------|
| Spatial (gameplay-critical) | Every frame (0)      | Hit detection and targeting where a missed frame is player-visible              |
| Spatial (ambient / AOE)     | 50-100 ms            | Lingering area effects and aura acquisition; sub-frame precision is unnecessary |
| Temporal                    | Every frame (0)      | Driven by the timer subsystem; cost is already O(1) per task                    |
| Animation                   | Every frame (0)      | Must align with notify windows; no polling cost beyond the montage system       |
| Event / State / Input       | n/a (no tick)        | Observer-driven; never ticked (see §10.1)                                       |

#### Task Tick Budget and Priority

Throttling bounds the cost of an individual task but not the aggregate cost across many actors. Implementations SHOULD additionally support a *per-frame tick budget*: an upper bound on the number of task ticks, or on accumulated tick time, that the runtime executes in a single frame.

When the budget is exhausted in a given frame, the runtime SHOULD defer the remaining ticking tasks to a subsequent frame rather than exceeding the budget. Tasks SHOULD declare a `Priority`; when deferring, the runtime SHOULD tick higher-priority tasks first and SHOULD avoid starving any task indefinitely (for example, by ageing deferred tasks toward a higher effective priority). Gameplay-critical tasks, such as player hit detection and targeting, SHOULD be assigned a higher priority than ambient ones.

`TickInterval` and `Priority` are conventional, optional parameters applicable to any task; they appear on the Ability schema’s task entries (see Appendix B, Ability Schema Definition).

#### Profiling Hooks

To make expensive tasks identifiable in production, implementations SHOULD expose profiling hooks around task ticking. At minimum, the runtime SHOULD make the following available per task type:

- Number of active instances

- Aggregate and per-instance tick time

- Effective tick frequency (after throttling)

These metrics SHOULD be surfaced through the host engine’s profiler or an equivalent instrumentation channel, so that integrators can attribute frame cost to specific task types and tune `TickInterval`, `Priority`, and the per-frame budget accordingly.

## 11. Input Integration

### 11.1 Command Pattern Overview

The UGAS input system implements the Command pattern to decouple hardware inputs from ability execution. This separation enables:

- Controller remapping without code changes

- Platform-specific input schemes

- Input buffering and queuing

- Context-driven input switching via Gameplay Tags

The input layer defines four formal entity schemas that sit between raw hardware and the ability system:

    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │    Device    │─────▶│   Modifier   │─────▶│    Action    │
    │    Input     │      │   Pipeline   │      │   (InputID)  │
    └──────────────┘      └──────────────┘      └──────┬───────┘
                                                       │
                                 ┌──────────────┐      │
                                 │  Action Set  │◀─────┘
                                 │  (context)   │
                                 └──────┬───────┘
                                        │
                                 ┌──────────────┐
                                 │   Ability    │
                                 │  Activation  │
                                 └──────────────┘

The *Mapping* entity connects Device Inputs to Actions, applying Modifiers along the way. Action Sets group Actions into switchable contexts driven by Gameplay Tags on the owning GC.

### 11.2 Input Actions

An Input Action is a named, semantic input intent — the logical "what", not the physical "how". Actions decouple gameplay logic from hardware: an ability binds to the Action `Fire`, never to `Mouse.LeftButton`.

Each Action declares a value type and a trigger behavior:

| Value Type | Description                                                                                     |
|------------|-------------------------------------------------------------------------------------------------|
| Digital    | Boolean on/off. Emits Started/Ongoing/Completed trigger events.                                 |
| Axis1D     | Single float axis (e.g. throttle, steering). Emits a continuous value each frame while nonzero. |
| Axis2D     | Two-component vector (e.g. movement direction, camera look).                                    |
| Axis3D     | Three-component vector (e.g. VR hand position, gyroscope orientation).                          |

| Trigger Behavior | Description                                                    |
|------------------|----------------------------------------------------------------|
| OnPressed        | Fire once when input goes from zero to nonzero (default).      |
| OnReleased       | Fire once when input returns to zero.                          |
| WhileHeld        | Fire every frame while input is nonzero.                       |
| OnTap            | Fire once on press-then-release within `TapThreshold` seconds. |
| OnDoubleTap      | Fire on two taps within `DoubleTapWindow` seconds.             |

``` yaml
Name: Fire
ValueType: Digital
TriggerBehavior: OnPressed
ConsumeInput: true
Tags:
  ActionTags:
    - Input.Type.Combat
Metadata:
  DisplayName: Fire Weapon
  Category: Combat
```

The `Name` field is the value that `InputID` fields on `GrantedAbilities` (§4) and `WaitInputRelease` tasks (§10.3) resolve to. Implementations MUST use exact string matching between `Action.Name` and `InputID`.

`ConsumeInput` controls whether this action consumes the underlying input event. When `true` (the default), lower-priority actions bound to the same hardware input do not receive the event. When `false`, the event propagates.

`Tags.ActionTags` enable bulk operations. A Gameplay Effect that grants the tag `Input.Blocked.Combat` could suppress all actions tagged `Input.Type.Combat` without listing them individually.

### 11.3 Action Sets

An Action Set is a context-based group of Actions that are active together. When a player enters a vehicle, the `OnFoot` set deactivates and the `InVehicle` set activates — driven by the same tag-based activation rules that govern abilities.

``` yaml
Name: OnFoot
Actions:
  - Move
  - Look
  - Fire
  - Aim
  - Reload
  - Jump
  - Sprint
Priority: 0
ActivationTags:
  RequiredTags:
    - State.Alive
  BlockedTags:
    - State.InVehicle
    - State.Cutscene
InputBuffer:
  Enabled: true
  BufferWindow: 0.12
  MaxBufferSize: 2
```

#### Activation Rules

Action Sets activate and deactivate based on the owning GC’s tag state, evaluated whenever owned tags change:

1.  ALL tags in `ActivationTags.RequiredTags` MUST be present on the GC (AND logic).

2.  NONE of the tags in `ActivationTags.BlockedTags` MAY be present (OR logic to block).

3.  Multiple Action Sets MAY be active simultaneously. When two active sets contain the same Action, the set with the highest `Priority` wins for that Action.

4.  When `Exclusive` is `true`, activating this set deactivates all other non-exclusive sets at the same or lower priority. This is appropriate for modal contexts (vehicle controls, cutscenes, menu navigation).

The runtime SHOULD store the list of currently active Action Set names on the GC’s `ActiveActionSets` field for debugging and serialization.

#### Per-Set Input Buffering

Each Action Set MAY override the global input buffer configuration (see §11.7). This enables per-context tuning:

- Fighting games: aggressive buffering (0.1s window, 5 buffer size)

- Platformers: moderate buffering (0.15s window, 3 buffer size)

- Menus: no buffering (avoid accidental double-confirms)

- Driving: no buffering (analog inputs are continuous, not event-based)

### 11.4 Device Inputs

A Device Input is a canonical, engine-agnostic identifier for a physical input on a hardware device. Device Inputs are referenced inline within Mappings using a `Device` + `Input` pair — they are not standalone entity files, since hardware is a finite catalogue, not game-specific authored data.

| Device   | Example Inputs                                                                                                                   |
|----------|----------------------------------------------------------------------------------------------------------------------------------|
| Keyboard | `Key.Space`, `Key.W`, `Key.LeftShift`, `Key.Escape`                                                                              |
| Mouse    | `Mouse.LeftButton`, `Mouse.RightButton`, `Mouse.Axis.X`, `Mouse.Axis.Y`, `Mouse.Scroll`                                          |
| Gamepad  | `Gamepad.FaceBottom` (A/Cross), `Gamepad.FaceRight` (B/Circle), `Gamepad.LeftStick.X`, `Gamepad.RightTrigger`, `Gamepad.DPad.Up` |
| Touch    | `Touch.Tap`, `Touch.Region.Left`, `Touch.Swipe`                                                                                  |
| Gyro     | `Gyro.Pitch`, `Gyro.Yaw`, `Gyro.Roll`                                                                                            |
| Custom   | Extension point for VR controllers, flight sticks, steering wheels. Uses `CustomDeviceName` for disambiguation.                  |

Implementations MUST bridge canonical Device Input identifiers to their engine-specific equivalents at runtime. The canonical naming convention uses hierarchical dot notation: `{Category}.{Identifier}` (e.g. `Key.Space`, `Gamepad.LeftStick.X`).

### 11.5 Input Mappings

A Mapping binds one or more Device Inputs to an Action, within an Action Set and optional platform context. This is the core data file that designers author to define "what button does what."

``` yaml
ActionSet: OnFoot
Platform: PC
Bindings:
  - Action: Fire
    Inputs:
      - Device: Mouse
        Input: Mouse.LeftButton

  - Action: Move
    CompositeInputs:
      Up:
        Device: Keyboard
        Input: Key.W
      Down:
        Device: Keyboard
        Input: Key.S
      Left:
        Device: Keyboard
        Input: Key.A
      Right:
        Device: Keyboard
        Input: Key.D

  - Action: Look
    Inputs:
      - Device: Mouse
        Input: Mouse.Axis.X
      - Device: Mouse
        Input: Mouse.Axis.Y
    Modifiers:
      - MouseSensitivity
```

#### Binding Types

*Simple binding*: A single Device Input maps to an Action. The most common case.

*Chord binding*: Multiple Device Inputs in the `Inputs` array must all be active simultaneously for the binding to fire. Used for modifier keys (Shift+1 for an alternate ability slot). When a chord and a simple binding share an input, the chord SHOULD have a higher `Priority` to avoid the simple binding firing first.

*Composite binding*: The `CompositeInputs` object composes multiple digital inputs into an axis value. The directional slots (`Up`, `Down`, `Left`, `Right`, `Forward`, `Backward`) map to a normalized vector suitable for Axis2D or Axis3D actions. This is how WASD keys produce a 2D movement vector on keyboard.

#### Platform Filtering

When `Platform` is set, the mapping only applies on that platform. Implementations SHOULD resolve platform at load time and discard non-matching mappings. When `Platform` is omitted, the mapping applies universally.

Multiple mapping files MAY target the same Action Set with different platforms, providing platform-specific defaults:

- `input_mapping_onfoot_pc.yaml` — keyboard + mouse bindings

- `input_mapping_onfoot_gamepad.yaml` — gamepad bindings

#### Rebinding

Bindings with `bIsRebindable: true` (the default) SHOULD be modifiable at runtime through the remapping interface (see §11.8). Bindings with `bIsRebindable: false` are fixed and MUST NOT appear in the player’s controls settings screen.

### 11.6 Input Modifiers

An Input Modifier is a reusable processing step applied to raw input values as they flow through the mapping pipeline. Modifiers are standalone entities referenced by name — not inline configuration — enabling sharing across mappings and integration with player settings screens.

| Modifier Type    | Description                                                                                                                                       |
|------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| DeadZone         | Clamps values below `InnerThreshold` to zero and above `OuterThreshold` to 1.0. Shape is `Axial` (per-axis) or `Radial` (magnitude of 2D vector). |
| Sensitivity      | Linear multiplier applied to the value. Per-axis multipliers available for 2D actions.                                                            |
| ResponseCurve    | Non-linear response curve. Types: `Linear`, `Exponential` (with `Exponent`), `SCurve`, `Custom` (with explicit `CurvePoints`).                    |
| AxisInvert       | Inverts one or more axes (`InvertX`, `InvertY`).                                                                                                  |
| AxisScale        | Scales axes by arbitrary factors (`ScaleX`, `ScaleY`, `ScaleZ`).                                                                                  |
| AxisSwizzle      | Reorders axes (e.g. `SwizzleOrder: "YXZ"` swaps X and Y).                                                                                         |
| RadialScaling    | Normalizes input to a maximum radius, clamping to the unit circle.                                                                                |
| Normalize        | Normalizes the input vector to unit length.                                                                                                       |
| TriggerThreshold | Converts an analog value to digital: values above `PressThreshold` count as pressed.                                                              |
| Clamp            | Clamps the value between `Min` and `Max`.                                                                                                         |
| Custom           | Engine-specific implementation via `CalculatorClass`.                                                                                             |

``` yaml
Name: StickDeadzone
Type: DeadZone
Params:
  InnerThreshold: 0.15
  OuterThreshold: 0.95
  DeadZoneShape: Radial
UserConfigurable: true
Metadata:
  DisplayName: Stick Dead Zone
```

#### Pipeline Processing

Modifiers in a binding’s `Modifiers` array are processed in order — the output of each modifier feeds into the next. The pipeline runs every frame for axis-type actions and on input events for digital actions.

A typical gamepad stick pipeline:

1.  Raw stick position → `DeadZone` (eliminate drift) → `RadialScaling` (normalize to unit circle) → processed value reaches the Action.

A typical mouse look pipeline:

1.  Raw mouse delta → `Sensitivity` (user-configurable multiplier) → processed value reaches the Action.

#### User-Configurable Modifiers

When `UserConfigurable` is `true`, the runtime SHOULD expose the modifier’s parameters in the player’s settings screen (e.g. a sensitivity slider, an invert-Y toggle, a dead zone adjustment). The modifier’s `Metadata.DisplayName` provides the label for the settings UI.

### 11.7 Input Buffering

Input buffering allows players to queue inputs during animations or recovery frames. The buffer configuration is specified per Action Set (see §11.3) or globally:

``` typescript
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

1.  Input arrives during "blocked" state (animation, recovery)

2.  Input is stored in buffer with timestamp

3.  When block ends, buffered inputs are processed in order

4.  Expired inputs (beyond buffer window) are discarded

``` typescript
function ProcessBufferedInputs(actionSet: ActionSet): void {
  const config = actionSet.InputBuffer ?? this.GlobalBufferConfig;
  if (!config.Enabled) return;

  const now = GetCurrentTime();

  // Remove expired inputs
  this.InputBuffer = this.InputBuffer.filter(
    input => now - input.Timestamp < config.BufferWindow
  );

  // Process valid inputs
  for (const input of this.InputBuffer) {
    if (TryActivateAbilityByInputID(input.ActionName)) {
      break;  // Successfully activated, stop processing
    }
  }

  this.InputBuffer.Clear();
}
```

Buffered inputs MUST only be processed if the Action Set that contains their Action is still active when the buffer is drained.

### 11.8 Remapping Support

Input mappings SHOULD be externalizable and modifiable at runtime:

``` typescript
interface IInputMapper {
  /** Get the active bindings for an action */
  GetBindingsForAction(action: ActionName): Binding[];

  /** Remap a binding to a new device input */
  RemapBinding(action: ActionName, oldInput: DeviceInput, newInput: DeviceInput): void;

  /** Reset all bindings to defaults for an action set */
  ResetToDefaults(actionSet: ActionSetName): void;

  /** Save current mappings to persistent storage */
  SaveMappings(): void;

  /** Load saved mappings from persistent storage */
  LoadMappings(): void;
}
```

Implementations MUST respect the `bIsRebindable` flag on bindings. Only bindings with `bIsRebindable: true` SHOULD be presented in the controls settings UI and accepted by `RemapBinding`.

When a player remaps a binding, the runtime SHOULD check for conflicts (two bindings in the same Action Set using the same Device Input) and either warn the player or swap the conflicting binding.

# Part IV: Feedback, Networking, and Persistence

## 12. Gameplay Cues

### 12.1 Design Philosophy

Gameplay Cues enforce strict separation between Mechanics and Aesthetics. This separation provides:

- *Server Optimization*: Headless servers load no visual/audio resources

- *Client Customization*: Visual settings don’t affect gameplay

- *Network Efficiency*: Cues are not replicated; only trigger tags are

- *Platform Adaptation*: Different platforms can have different cue implementations

### 12.2 Cue Trigger Mechanism

Cues are triggered by Tags following the `GameplayCue.*` convention:

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
Name: "GE_FireDamage"
DurationPolicy: Instant
Modifiers:
  - Attribute: "Health"
    Operation: Add
    Magnitude:
      Type: ScalableFloat
      Value: -25.0
GameplayCues:
  - "GameplayCue.Impact.Fire"
```

When the Effect is applied: 1. Server applies the Effect and modifies attributes 2. `GameplayCue.Impact.Fire` tag is communicated to clients 3. Clients' Cue Managers instantiate the fire impact VFX/SFX

### 12.3 Cue Types

*Burst Cues* (Fire-and-Forget) : Triggered once, play to completion, clean themselves up.

``` typescript
class GC_Impact_Fire extends GameplayCueBurst {
  OnExecute(context: CueContext): void {
    SpawnParticleSystem("PS_FireImpact", context.HitLocation);
    PlaySound("SFX_FireImpact", context.HitLocation);
  }
}
```

*Looping Cues* (Duration-Bound) : Persist while the triggering Effect is active.

``` typescript
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

1.  Receiving cue trigger notifications

2.  Matching tags to Cue implementations

3.  Instantiating and managing Cue resources

4.  Pooling frequently-used Cues for performance

``` typescript
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

1.  Cue Manager is NOT instantiated

2.  Cue assets are NOT loaded

3.  Cue trigger tags are still processed for replication

4.  Memory footprint is significantly reduced

Implementations SHOULD support a headless mode flag:

``` typescript
if (!IsHeadlessServer()) {
  this.CueManager = new GameplayCueManager();
  this.CueManager.LoadCueAssets();
}
```

## 13. Network Replication

### 13.1 Replication Architecture

UGAS defines a client-server replication model where:

- The server is authoritative for all gameplay state

- Clients receive replicated state updates

- Clients may predict state changes locally

- Server reconciles predicted state with authoritative state

<!-- -->

    ┌──────────────────┐            ┌──────────────────┐
    │      SERVER      │            │      CLIENT      │
    │                  │            │                  │
    │  ┌────────────┐  │  Replicate │  ┌────────────┐  │
    │  │    GC      │──┼───────────▶│  │    GC      │  │
    │  │(Authority) │  │            │  │  (Proxy)   │  │
    │  └────────────┘  │            │  └────────────┘  │
    │                  │            │                  │
    │                  │  Predict   │                  │
    │                  │◀───────────┼──(Local Input)   │
    │                  │            │                  │
    │                  │ Reconcile  │                  │
    │                  │───────────▶│                  │
    └──────────────────┘            └──────────────────┘

### 13.2 Replication Modes

| Mode      | Effects    | Cues | Tags | Attributes | Use Case                    |
|-----------|------------|------|------|------------|-----------------------------|
| `Minimal` | None       | All  | All  | None       | AI entities, distant actors |
| `Mixed`   | Owner only | All  | All  | Owner only | Player characters           |
| `Full`    | All        | All  | All  | All        | Single-player, debugging    |

Minimal Mode  
Only Cue triggers and Tag changes are replicated. Effects and Attributes are server-only. Suitable for AI entities where clients don’t need full state.

Mixed Mode  
Full replication to the owning client; minimal replication to others. The standard mode for player characters in multiplayer games.

Full Mode  
Complete replication to all clients. Used for single-player games or debugging. Higher bandwidth cost.

### 13.3 Bandwidth Optimization

#### Delta Compression

Only changed values are transmitted:

``` typescript
struct ReplicatedAttributeSet {
  /** Bitmask of changed attributes since last update */
  DirtyMask: uint32;

  /** Only changed attribute values */
  ChangedValues: float[];
}
```

#### Dirty Bit Tracking

Attributes track their dirty state:

``` typescript
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

``` typescript
struct QuantizedHealth {
  /** 0-255 representing 0-100% health */
  HealthPercent: uint8;
}
```

### 13.4 Client-Side Prediction

To eliminate network latency perception, clients predict ability outcomes locally. The structures referenced below — `PredictionKey`, `GeneratePredictionKey()`, and `CaptureState()` — are defined normatively in §13.8. Prediction MUST observe the bounded prediction window of §13.8.2; a client MUST NOT predict beyond it.

``` typescript
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

``` typescript
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

1.  Revert to last known authoritative state

2.  Re-apply all inputs that occurred since that state

3.  Blend visually to avoid jarring corrections

The input-history record format that feeds `inputHistory`, its bounded retention duration, the maximum replay depth, and the rule that re-simulation is scoped to the single owning GC are defined normatively in §13.8.5. `RollbackToState` and `ApplyState` operate on the output of `CaptureState()` (§13.8.3) — the owning GC’s gameplay state only.

``` typescript
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

| Actor Type                               | Update Rate | Notes                                                                         |
|------------------------------------------|-------------|-------------------------------------------------------------------------------|
| Player Character (LAN / low-latency)     | 60-100 Hz   | High frequency for responsive feel                                            |
| Player Character (mobile / high-latency) | 20-30 Hz    | Reduce to manage bandwidth; compensate with aggressive client-side prediction |
| Important AI                             | 30-60 Hz    | Moderate frequency                                                            |
| Distant Actors                           | 10-20 Hz    | Lower frequency acceptable                                                    |
| Static Objects                           | On Change   | Event-based only                                                              |

> *High-latency guidance:* On connections with RTT \> 150 ms (common on mobile or cross-region play), implementations SHOULD lower the player-character replication rate to 20-30 Hz and increase prediction window depth accordingly. Attribute and Tag state SHOULD be sent at a lower rate than position to prioritise movement responsiveness. Dead-reckoning or interpolation SHOULD be applied on the receiving end.

### 13.7 Effect Application Authorization

`ApplyGameplayEffectToTarget` is the primary mutation surface of the GC pipeline and therefore a critical security boundary in networked environments.

#### Core requirement

In any networked environment, a call to `ApplyGameplayEffectToTarget` that originates on a client MUST be validated by the server before the effect is executed on authoritative state. Clients MUST NOT be permitted to mutate server-authoritative GC state directly.

#### Validation pipeline

The server-side validation step MUST check, at minimum:

1.  *Instigator authority* — the instigating GC is owned by the requesting client (or is a server-controlled entity).

2.  *Ability ownership* — the effect is being applied as part of an ability that the instigator has been granted (i.e., the ability spec exists in the instigator’s granted-ability list).

3.  *Target reachability* — the target GC is a legitimate target for the instigator at the time of application (range, line-of-sight, or game-rule checks as appropriate to the title).

4.  *Effect class whitelist* — the effect class is one the ability is permitted to apply; implementations SHOULD reject arbitrary `EffectClass` values supplied by the client.

If any check fails, the server MUST reject the application and MAY roll back any prediction the client has already applied locally (via the standard reconciliation path in §13.5).

#### Predicted applications

When a client applies an effect locally as part of a prediction (using a `PredictionKey`), the local application is speculative only. The authoritative application — or its rejection — is determined by the server. Implementations MUST treat predicted effect applications as unconfirmed until the server acknowledges the prediction key. When the predicted effect targets a GC the predicting client does not own, the additional cross-GC rules of §13.8.4 apply.

``` typescript
// Client: speculative application
const predictionKey = GeneratePredictionKey();
const specHandle = MakeOutgoingSpec(GE_Damage, level, predictionKey);
ApplyGameplayEffectToTarget(target.GC, specHandle, predictionKey);
// Effect is active locally, but flagged as predicted (unconfirmed).

// Server: receives the RPC, validates, then applies authoritatively
function Server_ApplyEffect(
  instigatorGC: GameplayController,
  targetGC: GameplayController,
  specHandle: EffectSpecHandle,
  predictionKey: PredictionKey
): void {
  // 1. Validate instigator owns the ability that produced this spec
  if (!ValidateInstigatorAuthority(instigatorGC, specHandle)) {
    RejectPrediction(predictionKey);
    return;
  }
  // 2. Validate target is reachable / eligible
  if (!ValidateTarget(instigatorGC, targetGC, specHandle)) {
    RejectPrediction(predictionKey);
    return;
  }
  // Authoritative application — triggers replication to all clients
  ApplyGameplayEffectToTarget(targetGC, specHandle);
  ConfirmPrediction(predictionKey);
}
```

#### Authoritative-only effects

Some effects MUST only ever be applied by the server (e.g., spawn effects, death effects, anti-cheat corrections). These effects SHOULD be tagged with `Gameplay.Effect.AuthoritativeOnly` and implementations MUST refuse to apply them on a client even if a prediction key is present.

### 13.8 Prediction Model (Normative)

§13.4 through §13.7 describe client-side prediction conceptually but leave the prediction primitives undefined. This section defines them normatively: the `PredictionKey` structure, the bounded prediction window, the scope of `CaptureState()`, multi-ability key coordination, cross-GC prediction behavior, and the input-history and replay bounds. It is additive to and MUST NOT contradict §13.4–§13.7. Where this section uses MUST/SHOULD/MAY it carries the same RFC-2119 force as the rest of this specification.

#### 13.8.1 PredictionKey

A `PredictionKey` is the unit of speculation. Every speculative ability activation and every speculative effect application (§13.7) carries exactly one `PredictionKey`. The key correlates a client’s local prediction with the server’s authoritative execution so the outcome can later be confirmed (`ConfirmPrediction`) or rejected (`RejectPrediction`).

``` typescript
struct PredictionKey {
  /**
   * Base key — a per-client monotonically increasing identifier for the
   * prediction *group* created in a single input frame. All activations and
   * effect applications predicted as a consequence of one input share this
   * Base value. Unique per owning client for the lifetime of the connection.
   */
  Base: uint32;

  /**
   * Sub-key — monotonically increasing within a Base, starting at 0 for the
   * activation that the input directly triggered. Chained activations (one
   * triggered by an attribute threshold reached by another in the SAME frame)
   * receive the next Sub value under the same Base. Sub-key 0 is the parent;
   * Sub > 0 are dependent (child) keys. See §13.8.4.
   */
  Sub: uint16;

  /**
   * Parent sub-key. For the directly-triggered activation (Sub == 0) this is
   * NONE. For a chained/dependent activation this is the Sub value of the
   * activation that caused it, establishing the dependency edge used for
   * atomic reconciliation (§13.8.4).
   */
  ParentSub: uint16 | NONE;

  /**
   * Owning client identifier. The server uses (ClientId, Base, Sub) as the
   * globally-unique correlation tuple; clients only need (Base, Sub) locally.
   */
  ClientId: uint32;

  /**
   * Server-coordinated RNG seed for this prediction group. This is the seed
   * from which a deterministic RNG stream is derived on BOTH client and
   * server so that any randomized decision taken during prediction (e.g. a
   * critical-hit roll) advances the SAME sequence on both ends and therefore
   * yields the same result, avoiding a rollback caused solely by RNG drift.
   *
   * The AUTHORITATIVE seed originates server-side. The server allocates a
   * per-connection seed lineage at session establishment and communicates,
   * per prediction Base, the seed value the client MUST use (see
   * §13.8.1 "Seed derivation"). The seed is shared by every Sub under the
   * same Base; the RNG stream is advanced deterministically by (Sub, draw
   * index) so that parent and child activations consume disjoint, reproducible
   * sub-streams. Implementations MUST NOT derive gameplay-affecting randomness
   * during prediction from any source other than this seed.
   */
  Seed: uint64;
}

const NONE = 0xFFFF;
```

Seed derivation  
The server is the sole authority for `Seed`. At connection establishment the server MUST establish a seed lineage for the client (for example, a server-chosen 64-bit root seed advanced once per prediction `Base`) and MUST communicate the per-`Base` seed to the client such that the client can reproduce it before it predicts under that `Base`. Two communication strategies are permitted: (a) the server pushes the next seed(s) ahead of time (seed pre-distribution), so the client already holds the seed when local input occurs; or (b) the seed is derived by a shared, pre-agreed deterministic function of values both ends already know (e.g. `HKDF(rootSeed, Base)` where `rootSeed` was delivered once, server-side-chosen). In both cases the client MUST treat the server seed as authoritative: on `ConfirmPrediction` the server confirms the RNG stream matched; on a mismatch the server MUST `RejectPrediction` and the authoritative result replicates normally. Clients MUST NOT choose their own seed, because a client-chosen seed would let a client bias predicted random outcomes (this is the hook issue \#5 relies on for predicted critical-hit RNG).

#### 13.8.2 Prediction Window (Maximum Depth)

A client MUST NOT predict arbitrarily far ahead of confirmed authoritative state. Unbounded prediction lets a high-latency client diverge into a state the server will never reach, producing unrecoverable corrections.

The prediction window is the maximum amount of locally-predicted, server-unconfirmed simulation a client may hold at once. It is bounded in BOTH time and frames; the effective bound is whichever limit is reached first:

| Bound                 | Default   | Semantics                                                                                                                 |
|-----------------------|-----------|---------------------------------------------------------------------------------------------------------------------------|
| `MaxPredictionMillis` | 250 ms    | Maximum wall-clock span, measured from the oldest unconfirmed prediction’s timestamp to now, that may remain unconfirmed. |
| `MaxPredictionFrames` | 16 frames | Maximum number of simulation frames that may remain unconfirmed, independent of frame rate.                               |

- A client MUST NOT initiate a new predicted activation while doing so would exceed either bound. Once a bound is reached the client MUST fall back to awaiting server authority — i.e. it stops predicting, surrenders responsiveness for that input, and applies state only on the next authoritative update — until the oldest outstanding prediction is confirmed or rejected and the window reopens.

- Implementations SHOULD make `MaxPredictionMillis` and `MaxPredictionFrames` configurable per title and per connection class. The defaults above are RECOMMENDED starting values for a 60 Hz simulation.

- This bound is the concrete realization of the high-latency guidance in §13.6. When RTT exceeds the replication interval, an implementation MAY raise `MaxPredictionMillis` (and the corresponding frame count) to widen the prediction window so a high-latency client can still predict across its RTT — but the window MUST remain finite, and the fallback-to-authority behavior above MUST still trigger once the (raised) bound is exceeded. Raising the bound trades reconciliation cost and mis-prediction visibility against responsiveness; the §13.6 recommendation to "increase prediction window depth" refers to adjusting these two values.

#### 13.8.3 CaptureState() Scope

`CaptureState()` (called in §13.4) returns a snapshot used by `RollbackToState` to restore the client’s speculative state if a prediction is rejected. Its scope is deliberately narrow.

`CaptureState()` MUST capture ONLY the owning Gameplay Controller’s gameplay state:

1.  Attribute **Base** and **Current** values for the owning GC’s Attribute Sets.

2.  Active effect records on the owning GC.

3.  Ability activation states on the owning GC (which abilities are mid-activation, their phase, and cooldown/charge state).

4.  The owning GC’s owned-tag container.

`CaptureState()` MUST NOT capture world or physics state, and MUST NOT capture any other GC’s state. This keeps a per-activation capture cheap and bounds rollback cost to a single GC regardless of world size or actor count.

The concrete field set is the GC State Snapshot already defined in §14.2 (and the `ActiveEffectRecord` of §14.3). `CaptureState()` MUST reuse that field set rather than defining a parallel one, with two prediction-specific differences:

- Current Values and the owned-tag container, which §14.2 treats as derived/debug-only for persistence, ARE captured as restorable state here, because a speculative rollback restores the exact pre-prediction runtime state rather than recomputing from a save file.

- The capture is in-memory and short-lived (retained only until its `PredictionKey` is confirmed or rejected); it is not subject to the §14 serialization/versioning requirements.

``` typescript
/**
 * Captures ONLY the owning GC's gameplay state for speculative rollback.
 * Field set per §14.2 GC State Snapshot + §14.3 ActiveEffectRecord, reused
 * (not duplicated). Excludes world/physics state and all non-owned GCs.
 */
function CaptureState(): GameplayState {
  return {
    // §14.2: Attribute Base Values + (here) Current Values, owning GC only
    AttributeSets: this.OwningGC.CaptureAttributeSets(),     // Base + Current
    // §14.3: ActiveEffectRecord[], owning GC only
    ActiveEffects: this.OwningGC.CaptureActiveEffectRecords(),
    // Ability activation / cooldown / charge states, owning GC only
    AbilityStates: this.OwningGC.CaptureAbilityActivationStates(),
    // Owned-tag container, owning GC only
    OwnedTags: this.OwningGC.CaptureOwnedTagContainer(),
    Timestamp: GetCurrentTime()
  };
}
```

#### 13.8.4 Multi-Ability and Cross-GC Prediction

##### Multi-ability prediction (atomic groups)

When more than one ability is predicted to activate as a consequence of a single input frame, all of those activations MUST share one `PredictionKey.Base` and are coordinated by `Sub`:

1.  The activation directly triggered by the input receives `Sub = 0`, `ParentSub = NONE`.

2.  A chained activation — one triggered during the same frame by an attribute threshold, tag change, or event produced by an already-predicted activation in this group — receives the next monotonically increasing `Sub` under the same `Base`, with `ParentSub` set to the `Sub` of the activation that caused it. This makes the chain a dependency tree rooted at `Sub = 0`.

3.  `GeneratePredictionKey()` returns the root key (`Sub = 0`) for a new input; dependent activations within the same frame MUST be obtained from the same group (e.g. `DeriveChildKey(parentKey)`), NOT from a fresh `GeneratePredictionKey()` call, so the shared `Base` and `Seed` are preserved.

A prediction `Base` group MUST be reconciled atomically: the server confirms or rejects the group as a unit. If the parent activation (`Sub = 0`) is rejected, every dependent activation in the group MUST also be rolled back, because their precondition no longer holds. A child MAY be individually rejected while its parent is confirmed (the parent happened, but the threshold it was predicted to cross did not). This guarantees a chained activation is never left confirmed while the activation that caused it is rolled back.

``` typescript
function GeneratePredictionKey(): PredictionKey {
  const base = this.NextPredictionBase++;     // monotonic per client
  return {
    Base: base,
    Sub: 0,
    ParentSub: NONE,
    ClientId: this.LocalClientId,
    Seed: this.GetServerSeedForBase(base)      // authoritative, server-derived
  };
}

// Same-frame chained activation: keep Base + Seed, advance Sub, record parent.
function DeriveChildKey(parent: PredictionKey): PredictionKey {
  return {
    Base: parent.Base,
    Sub: this.NextSubForBase(parent.Base),     // monotonic within the Base
    ParentSub: parent.Sub,
    ClientId: parent.ClientId,
    Seed: parent.Seed
  };
}
```

##### Cross-GC effect prediction

This extends the "Predicted applications" rule of §13.7; it does not replace it. When a client predicts `ApplyGameplayEffectToTarget` (§13.7) on a GC it does NOT own:

- The predicted change on the non-owned target GC MUST be treated as **speculative, local-visual only**. It MUST NOT be treated as authoritative and MUST NOT influence any decision that is itself replicated as authoritative.

- The authoritative change on the non-owned GC MUST be reconciled from the server. The client MUST replace its speculative cross-GC change with the server-replicated result when the prediction key is confirmed (or discard it if rejected), exactly via the §13.5 reconciliation path.

- `RollbackToState`/`CaptureState()` for the predicting client cover only the owning GC (§13.8.3); the predicting client does not roll back the non-owned target GC’s authoritative state. The non-owned GC’s correction arrives through normal replication, not through the predicting client’s local replay.

- A predicted cross-GC application MUST still be `Gameplay.Effect.AuthoritativeOnly`-aware: effects so tagged (§13.7) MUST NOT be applied speculatively even as local-visual.

In short: a client MAY **show** a predicted hit landing on an enemy, but the enemy’s real state only ever changes when the server says so.

#### 13.8.5 Input History, Rollback Retention, and Replay Bounds

`RollbackAndReplay` (§13.5) re-applies inputs after reverting to authoritative state. This section defines the record format, retention, and bounds that §13.5 leaves open, and confirms the replay is single-GC scoped.

Input-history record  
``` typescript
struct PredictedInputRecord {
  /** Simulation frame on which the input was sampled (monotonic). */
  Frame: uint32;

  /** Client timestamp at sample time; used for the time-based window bound. */
  Timestamp: number;

  /**
   * The input payload that drove prediction this frame: the InputActions and
   * their values (see Part 3), plus any ability-activation requests issued.
   */
  Input: InputFrame;

  /**
   * Prediction group(s) created by this input, if any. Links the input to the
   * PredictionKey Base(s) it produced so confirm/reject can age out the
   * matching records.
   */
  PredictionBases: uint32[];
}
```

Retention  
The input history is a bounded ring buffer. Its retention MUST be at least the prediction window of §13.8.2 (i.e. it MUST retain enough records to cover `MaxPredictionMillis` / `MaxPredictionFrames`), and it MUST NOT need to retain more, because no input older than the window can still be unconfirmed. A record MAY be dropped once its associated prediction `Base`(s) are all confirmed or rejected AND it falls outside the window. Because retention is tied to the same bound, raising the prediction window (§13.8.2) automatically widens input retention.

Maximum replay depth  
The maximum number of inputs re-simulated in a single `RollbackAndReplay` MUST NOT exceed the prediction window of §13.8.2 (`MaxPredictionFrames` frames / `MaxPredictionMillis` of inputs). Since a client cannot predict beyond the window, it can never need to replay beyond it. This bounds worst-case replay cost to the window size — e.g. at 60 Hz with the default 16-frame window, at most 16 frames are replayed, not an unbounded RTT-driven count.

Replay scope  
Replay/re-simulation MUST be scoped to the single owning GC, NOT the whole world. `RollbackAndReplay` reverts and re-simulates only the state covered by `CaptureState()` (§13.8.3) — the owning GC’s attributes, active effects, ability states, and owned tags — re-applying the owning GC’s inputs from the history buffer. World state, physics, and non-owned GCs are NOT re-simulated by the predicting client; they are corrected through normal replication (§13.1, §13.5). This is what makes replay affordable: cost scales with one GC and the window depth, not with world size or actor count.

``` typescript
function RollbackAndReplay_Bounded(
  authoritativeState: GameplayState,   // §13.8.3 scope: owning GC only
  inputHistory: PredictedInputRecord[] // bounded ring buffer (retention above)
): void {
  // 1. Revert ONLY the owning GC's gameplay state.
  ApplyState(authoritativeState);

  // 2. Replay the owning GC's inputs newer than the authoritative state,
  //    bounded by the §13.8.2 prediction window.
  const replayable = inputHistory.filter(
    r => r.Timestamp > authoritativeState.Timestamp
  );
  // Window invariant: replayable.length <= MaxPredictionFrames.
  for (const record of replayable) {
    SimulateInput(record.Input);       // owning GC only; not the world
  }

  // 3. Blend visually if the corrected result diverges (§13.5).
  if (VisualDiscrepancy > Threshold) {
    StartVisualBlend(currentVisual, newSimulatedState);
  }
}
```

## 14. State Persistence

### 14.1 Overview

UGAS defines a persistence protocol so that the runtime state of a Gameplay Controller — attributes, active effects, granted abilities, and owned tags — can be captured, serialized, and restored. The primary use cases are:

- *Save / Load* in single-player games ("save anywhere" support)

- *Reconnection* in multiplayer — restoring a player’s GC after a disconnect

- *Server migration* — transferring authoritative GC state between server processes

- *Replay systems* — recording and replaying gameplay state at arbitrary points

Attribute Sets are the serialization boundary for attribute data (§6.1). This section defines the complementary protocol for active effect state, which is the primary source of complexity in GC persistence.

### 14.2 GC State Snapshot

A complete GC snapshot MUST contain:

| Component         | Content                                                | Restoration Order                             |
|-------------------|--------------------------------------------------------|-----------------------------------------------|
| Attribute Sets    | Base Values for every registered attribute             | 1 — restore first                             |
| Active Effects    | One `ActiveEffectRecord` per active effect (see §14.3) | 2 — re-apply after attributes                 |
| Granted Abilities | Ability class, level, input binding, grant source      | 3 — after effects (some are effect-granted)   |
| Owned Tags        | Tag grant counts                                       | Derived — reconstructed from restored effects |

Current Values and Owned Tags are *derived state*: they are recomputed when active effects are re-applied to the restored Base Values. Implementations MUST NOT serialize Current Values or tag grant counts as authoritative state; they exist in the snapshot only for debugging and validation.

``` typescript
struct GCSnapshot {
  /** Monotonic snapshot version for forward-compatibility checks */
  Version: integer;

  /** Reference to the snapshotted GC */
  OwnerActorID: string;

  /** Wall-clock or game-time at capture */
  CaptureTimestamp: number;

  /** Base Values, keyed by AttributeSet then Attribute name */
  AttributeSets: SerializedAttributeSet[];

  /** Every active (non-Instant) effect */
  ActiveEffects: ActiveEffectRecord[];

  /** Granted abilities not sourced from an active effect */
  GrantedAbilities: SerializedAbilityGrant[];
}
```

### 14.3 Active Effect Record

Each active effect (`HasDuration` or `Infinite`) is serialized as an `ActiveEffectRecord`. Instant effects modify Base Values directly and leave no active state; they are captured implicitly via the attribute snapshot.

``` typescript
struct ActiveEffectRecord {
  /** Unique handle — preserved across save/load for external references */
  Handle: string;

  /** Effect class identifier (references a GameplayEffect definition) */
  EffectClass: string;

  /** Duration policy of the originating effect */
  DurationPolicy: "HasDuration" | "Infinite";

  /** Effect level at time of application */
  Level: integer;

  /** GC that applied this effect */
  InstigatorGC: string;

  /** Ability that applied this effect (if any) */
  SourceAbility?: string;

  /** Remaining duration in seconds. Present only for HasDuration effects. */
  RemainingDuration?: number;

  /** Periodic execution state. Present only for periodic effects. */
  PeriodicState?: PeriodicExecutionState;

  /** Execution policy state for multi-instance effects */
  ExecutionPolicyState?: ExecutionPolicyState;

  /** Number of active instances (RunInParallel) or queued+active instances (RunInSequence) */
  InstanceCount: integer;

  /** Attribute values captured OnApplication (frozen at apply-time) */
  CapturedAttributes?: Map<string, number>;

  /** SetByCaller magnitudes set at application time */
  SetByCallerMagnitudes?: Map<string, number>;
}
```

#### 14.3.1 Duration Encoding

`HasDuration` effects MUST serialize remaining time as *seconds remaining*, not as an absolute wall-clock or game-time deadline.

| Field               | Semantics                                                                                                        |
|---------------------|------------------------------------------------------------------------------------------------------------------|
| `RemainingDuration` | Seconds of effect time remaining at the moment of capture. On restore, the effect timer resumes from this value. |

Rationale: absolute timestamps couple serialized state to the clock source. Remaining-seconds is portable across sessions, servers, and time zones. The `CaptureTimestamp` on the snapshot provides the reference point if an implementation needs to compute how much time has elapsed since capture (e.g., to expire effects during an offline period — see §14.5).

#### 14.3.2 Infinite Effect Intent

Infinite effects have no expiry timer, which raises a cleanup concern: is an Infinite effect *intended to persist indefinitely* (e.g., an equipment passive) or was it *leaked* by a bug?

The serialization protocol addresses this through provenance tracking: every `ActiveEffectRecord` with `DurationPolicy: Infinite` MUST carry an `InstigatorGC`, a `SourceAbility`, or both. On restoration, implementations SHOULD validate that the instigator and/or source ability still exist. If neither reference resolves, the implementation SHOULD log a warning and MAY discard the effect.

Implementations MAY additionally define a `Gameplay.Effect.Persistent` tag on effect definitions that are *designed* to survive serialization boundaries. Effects without this tag MAY be stripped during save if the game design requires it (e.g., clearing temporary combat buffs on zone transition or session end). This is a game-design decision, not a spec mandate — the tag provides a declarative mechanism for expressing the intent.

#### 14.3.3 Periodic Execution State

For effects with `Period` settings (§9.3), the serialization record MUST capture where the effect is within its current period cycle:

``` typescript
struct PeriodicExecutionState {
  /** Seconds elapsed since the last periodic execution */
  PeriodElapsed: number;

  /** Total number of periodic executions that have fired */
  ExecutionCount: integer;
}
```

On restoration:

1.  The period timer resumes from `PeriodElapsed`, counting toward the next execution at the configured `Period` interval.

2.  The effect MUST NOT re-execute for the current period on load. A periodic tick fires only when the resumed timer reaches the next period boundary.

3.  `ExecutionCount` is preserved for effects whose logic depends on how many times they have executed (e.g., escalating damage over time).

#### 14.3.4 Execution Policy State

##### RunInParallel

Each concurrent instance is serialized as an independent `ActiveEffectRecord` sharing the same `EffectClass`. `InstanceCount` records the total number of simultaneously active instances. On restore, all instances resume independently with their own timers.

##### RunInSequence

Queued instances that are waiting (not yet active) MUST also be serialized. The queue is represented by an ordered list of handles:

``` typescript
struct SequenceQueueState {
  /** Ordered handles of instances — first element is the currently active instance */
  Queue: string[];
}
```

The active instance (head of the queue) carries its own `RemainingDuration` and `PeriodicState`. Queued instances retain their full configured duration — they have not started yet. On restore, the GC reconstructs the queue: the head instance resumes with its saved timer state, and queued instances wait in order.

##### RunInMerge

A merged effect is a single logical instance regardless of how many times it was applied. The serialized record carries the merged remaining duration (time until the latest-ending application would have expired) and the merge count:

``` typescript
struct MergeState {
  /** Number of applications that were merged into this instance */
  MergeCount: integer;
}
```

### 14.4 Restoration Protocol

Restoring a GC from a snapshot MUST follow this sequence:

1.  **Restore Attribute Base Values.** For each `SerializedAttributeSet`, set each attribute’s Base Value. Do NOT recompute Current Values yet.

2.  **Re-apply Active Effects.** For each `ActiveEffectRecord`, reconstruct the `EffectSpec` from the stored `EffectClass` definition, `Level`, `SetByCallerMagnitudes`, and `CapturedAttributes`. Apply the effect to the GC using the restoration overrides (duration from `RemainingDuration`, periodic state from `PeriodicState`). The effect pipeline runs normally — modifiers are added, Tags are granted, Abilities are granted — but timers are initialized from the serialized state rather than from the effect’s configured values.

3.  **Restore Granted Abilities.** Re-grant abilities that were not sourced from an active effect. Effect-granted abilities are restored automatically in step 2.

4.  **Recompute Current Values.** With all modifiers back in place, trigger a full attribute recalculation. The resulting Current Values SHOULD match the pre-save state.

5.  **Validate.** Implementations SHOULD compare restored Current Values and Owned Tags against any debug/validation copies stored in the snapshot. Mismatches indicate a restoration error or a data definition change between save and load.

``` typescript
function RestoreGC(gc: GameplayController, snapshot: GCSnapshot): void {
  // 1. Attributes
  for (const set of snapshot.AttributeSets) {
    const attrSet = gc.GetAttributeSet(set.Name);
    for (const attr of set.Attributes) {
      attrSet.SetBaseValue(attr.Name, attr.BaseValue);
    }
  }

  // 2. Active Effects — order matters for RunInSequence queues
  for (const record of snapshot.ActiveEffects) {
    const spec = ReconstructEffectSpec(record);
    gc.ApplyGameplayEffect(spec, {
      ResumeRemainingDuration: record.RemainingDuration,
      ResumePeriodicState: record.PeriodicState,
      RestoredHandle: record.Handle
    });
  }

  // 3. Non-effect-granted Abilities
  for (const grant of snapshot.GrantedAbilities) {
    gc.GrantAbility(grant.AbilityClass, grant.Level, grant.InputID);
  }

  // 4. Recompute
  gc.RecalculateAllAttributes();
}
```

### 14.5 Offline Duration Advancement

For single-player games where real time passes between save and load (e.g., mobile idle games), implementations MAY advance effect timers by the elapsed real time:

``` typescript
function AdvanceOfflineTime(
  snapshot: GCSnapshot,
  currentTime: number
): void {
  const elapsed = currentTime - snapshot.CaptureTimestamp;

  for (const record of snapshot.ActiveEffects) {
    if (record.DurationPolicy === "HasDuration" && record.RemainingDuration != null) {
      record.RemainingDuration -= elapsed;
      if (record.RemainingDuration <= 0) {
        // Effect expired while offline — remove from snapshot before restore
        continue;
      }
    }
    if (record.PeriodicState) {
      record.PeriodicState.PeriodElapsed += elapsed;
    }
  }
}
```

Whether to execute missed periodic ticks (batch-fire accumulated executions) or simply advance the timer is a game-design decision. The spec does not mandate either behavior; implementations SHOULD document their choice.

# Part V: Reference Implementation

## 15. Implementation Examples

### 15.1 Basic Damage Application

#### Effect Definition

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
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

``` typescript
function ApplyDamage(target: GameplayController, damage: float): void {
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

``` typescript
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

### 15.2 Buff/Debuff with Duration

#### Temporary Modifier

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
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
      Value: 0.25  # +25% damage
GrantedTags:
  - "Status.Buff.Strength"
GameplayCues:
  - "GameplayCue.Status.StrengthBuff"
```

#### Visual Cue Integration

``` typescript
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

### 15.3 Ability with Cast Time

``` yaml
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

``` typescript
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

### 15.4 Complex Calculation (Armor Penetration)

``` typescript
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

    // Apply critical hit.
    // Draw from the deterministic, seeded stream (context.RNG) rather than a
    // bare RandomFloat(), so a predicting client and the server roll the same
    // crit and avoid a rollback. The stream is seeded from PredictionKey.Seed
    // (§13.8.1) and positioned per the (Sub, draw index) scheme; see the
    // "Randomness in Execution Calculations" rule in §9.5. (This calculation
    // stays Predictable; a roll that must be server-only would instead set
    // Predictable = false and abort prediction per §13.8.2.)
    if (context.RNG.NextFloat() < critChance) {
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

## 16. Case Studies

### 16.1 Platformer (Mario-style)

#### Movement Attributes

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/attribute_set.json
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

``` typescript
class GA_Jump extends GameplayAbility {
  // Handle to the Infinite Effect that grants State.InAir while airborne.
  // State.Grounded is managed by the physics subsystem via its own Effect,
  // not by this ability — tag ownership follows responsibility.
  private inAirHandle: ActiveEffectHandle;

  ActivateAbility(context: AbilityContext): void {
    // Check grounded OR coyote time
    if (!this.Owner.Tags.MatchesTag("State.Grounded") &&
        !this.Owner.Tags.MatchesTag("Status.CoyoteTime")) {
      EndAbility(true);
      return;
    }

    // Grant State.InAir via an Effect — direct tag mutation is prohibited (§3.1).
    // GE_InAir is an Infinite Effect with GrantedTags: ["State.InAir"].
    // The physics subsystem independently removes its GE_Grounded effect
    // when it detects the character is no longer on the ground.
    const inAirSpec = MakeOutgoingSpec(GE_InAir, 1);
    this.inAirHandle = ApplyGameplayEffectToSelf(inAirSpec);

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
    // Short press = cut jump short.
    // VerticalVelocity is a GAS Attribute kept in sync by the physics Avatar,
    // so this remains a pure GAS query — no direct physics coupling here.
    if (this.Owner.GetAttribute("VerticalVelocity") > 0) {
      // Apply gravity multiplier for shorter jump
      const cutSpec = MakeOutgoingSpec(GE_JumpCut, 1);
      ApplyGameplayEffectToSelf(cutSpec);
    }
  }

  OnLanded(): void {
    // Remove State.InAir by removing the Effect that granted it.
    // The physics subsystem re-applies its GE_Grounded effect on landing.
    RemoveActiveGameplayEffect(this.inAirHandle);
    EndAbility(false);
  }
}
```

#### Power-Up Effects

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
Name: "GE_SuperMushroom"
DurationPolicy: Infinite
GrantedTags:
  - "State.PowerUp.Super"
Modifiers:
  - Attribute: "Scale"
    Operation: Multiply
    Magnitude:
      Type: ScalableFloat
      Value: 1.0  # +100% (doubles size)
  - Attribute: "Health"
    Operation: Add
    Magnitude:
      Type: ScalableFloat
      Value: 1.0  # Gain 1 hit point
GameplayCues:
  - "GameplayCue.PowerUp.Super"
```

### 16.2 Racing (Forza-style)

#### Vehicle Attribute Sets

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/attribute_set.json
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

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
Name: "GE_Biome_Mud"
DurationPolicy: Infinite
ApplicationRequiredTags:
  - "Vehicle"
Modifiers:
  - Attribute: "TireGripMultiplier"
    Operation: Multiply
    Magnitude:
      Type: ScalableFloat
      Value: -0.6  # -60% grip (retains 40% of normal grip)
  - Attribute: "MaxSpeed"
    Operation: Add
    Magnitude:
      Type: ScalableFloat
      Value: -30.0  # Reduce top speed
GrantedTags:
  - "Surface.Mud"
---
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
Name: "GE_Biome_Asphalt"
DurationPolicy: Infinite
ApplicationRequiredTags:
  - "Vehicle"
Modifiers:
  - Attribute: "TireGripMultiplier"
    Operation: Override
    Magnitude:
      Type: ScalableFloat
      Value: 1.0
GrantedTags:
  - "Surface.Asphalt"
```

#### Physics Integration

``` typescript
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

### 16.3 ARPG (Diablo-style)

#### Damage Bucket Architecture

The "Damage Bucket" system prevents linear power creep by organizing `Multiply` modifiers into named channels. Modifiers in the same channel add their bonuses; channels multiply against each other. Because the `Channel` mechanism is built into the modifier pipeline (§5.3), the bucket design is expressed *declaratively* in Effect YAML — no custom calculation code required for the stacking logic itself.

Three canonical buckets:

| Channel             | What goes in it                                                | Stacking                                         |
|---------------------|----------------------------------------------------------------|--------------------------------------------------|
| `"MainStat"`        | Stat-derived scaling (e.g. Strength → +damage)                 | Additive                                         |
| `"DamageBonuses"`   | Conditional damage bonuses (fire, vs. elites, while healthy …) | Additive                                         |
| `"LegendaryPowers"` | Item set / legendary power multipliers                         | Additive within, ×MainStat ×DamageBonuses across |

``` yaml
# GE_Weapon_FireSword.yaml — item that grants a fire damage bonus
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
Name: "GE_Weapon_FireSword"
DurationPolicy: Infinite
Modifiers:
  - Attribute: "WeaponDamage"
    Operation: Multiply
    Magnitude:
      Type: ScalableFloat
      Value: 0.20        # +20% fire damage
    Channel: "DamageBonuses"
```

``` yaml
# GE_Passive_EliteHunter.yaml — passive skill: +15% damage vs. elites
Name: "GE_Passive_EliteHunter"
DurationPolicy: Infinite
ApplicationRequiredTags:
  - "Status.FightingElite"
Modifiers:
  - Attribute: "WeaponDamage"
    Operation: Multiply
    Magnitude:
      Type: ScalableFloat
      Value: 0.15        # +15% damage vs. elites
    Channel: "DamageBonuses"
```

``` yaml
# GE_Set_LegendaryPower.yaml — set bonus: +50% damage (its own channel)
Name: "GE_Set_LegendaryPower"
DurationPolicy: Infinite
Modifiers:
  - Attribute: "WeaponDamage"
    Operation: Multiply
    Magnitude:
      Type: ScalableFloat
      Value: 0.50        # +50% legendary multiplier
    Channel: "LegendaryPowers"
```

``` yaml
# GE_MainStat_Strength.yaml — applied by the attribute system per point of Strength
Name: "GE_MainStat_Strength"
DurationPolicy: Infinite
Modifiers:
  - Attribute: "WeaponDamage"
    Operation: Multiply
    Magnitude:
      Type: AttributeBased
      BackingAttribute: "Strength"
      Source: Source
      Coefficient: 0.01  # +1% per Strength point
    Channel: "MainStat"
```

With all four effects active (Strength 50, fire sword, elite hunter active, legendary set): - `MainStat` channel factor: `1 + (0.01 × 50)` = *×1.50* - `DamageBonuses` channel factor: `1 + 0.20 + 0.15` = *×1.35* - `LegendaryPowers` channel factor: `1 + 0.50` = *×1.50* - Final `WeaponDamage` multiplier: `1.50 × 1.35 × 1.50` = *×3.04*

vs. naive unchanelled stacking: `1.50 × 1.20 × 1.15 × 1.50` = *×3.11* — a modest difference at low item counts that compounds severely at higher counts.

*Conditional modifiers* (e.g. the Vulnerability bonus) that depend on target state at hit-time still require an `ExecutionCalculation`, but only for the conditional logic — the stacking math is already handled by the pipeline:

``` typescript
class ExecCalc_ARPGDamage extends ExecutionCalculation {
  Execute(source, target, context): ModifierResult[] {
    // All bucket stacking is already resolved in WeaponDamage's Current Value.
    const weaponDamage = source.Get("WeaponDamage");

    // Only conditional logic needs to live here.
    const vulnerabilityBonus = target.Tags.MatchesTag("Status.Vulnerable") ? 0.20 : 0.0;

    return [{
      Attribute: "Health",
      Operation: Add,
      Magnitude: -weaponDamage * (1 + vulnerabilityBonus)
    }];
  }
}
```

#### Combat Tag Queries

``` typescript
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

``` typescript
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

### 16.4 Puzzle (2048-style)

#### Grid Cell Attributes

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/attribute_set.json
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

``` typescript
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

      // Mark source for destruction via an Effect — direct tag mutation is prohibited (§3.1).
      // GE_PendingDestroy is an Infinite Effect with GrantedTags: ["Status.PendingDestroy"].
      const destroySpec = MakeOutgoingSpec(GE_PendingDestroy, 1);
      ApplyGameplayEffectToTarget(merge.SourceCell.GC, destroySpec);
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

#### Undo via Effect Audit Trail

Rather than snapshotting raw cell values, the undo system hooks into the GC Effect application pipeline via `OnBeforeEffectApplied`. Each effect applied during a turn is recorded alongside the pre-apply attribute values it will overwrite. Undoing a turn replays those pre-apply values back through Instant Effects — the undo state is derived entirely from the Effect layer, not from bespoke value captures.

``` typescript
interface EffectRecord {
  TargetGC: GameplayController;
  Spec: EffectSpec;
  /** Attribute values captured immediately before this Effect was applied. */
  PreApplyValues: Map<string, number>;
}

interface TurnRecord {
  EffectsApplied: EffectRecord[];
}

class UndoSystem {
  private TurnHistory: TurnRecord[] = [];
  private CurrentTurn: TurnRecord | null = null;

  /** Called by GA_Move at the start of each player turn. */
  BeginTurn(): void {
    this.CurrentTurn = { EffectsApplied: [] };
  }

  /**
   * Hook registered on each cell GC as OnBeforeEffectApplied.
   * The GC pipeline calls this immediately before applying an Effect,
   * giving us a chance to snapshot the attribute values that will change.
   */
  OnBeforeEffectApplied(targetGC: GameplayController, spec: EffectSpec): void {
    if (!this.CurrentTurn) return;
    const preApplyValues = new Map<string, number>();
    for (const modifier of spec.EffectClass.Modifiers) {
      preApplyValues.set(modifier.Attribute, targetGC.GetAttribute(modifier.Attribute));
    }
    this.CurrentTurn.EffectsApplied.push({ TargetGC: targetGC, Spec: spec, PreApplyValues: preApplyValues });
  }

  /** Called by GA_Move after all effects for the turn have been applied. */
  CommitTurn(): void {
    if (this.CurrentTurn) {
      this.TurnHistory.push(this.CurrentTurn);
      this.CurrentTurn = null;
    }
  }

  Undo(): void {
    if (this.TurnHistory.length === 0) return;
    const lastTurn = this.TurnHistory.pop()!;

    // Restore pre-apply values in reverse Effect order.
    // Each restore is itself an Instant Override Effect — undo flows through
    // the same pipeline as every other state change.
    for (const record of [...lastTurn.EffectsApplied].reverse()) {
      const restoreSpec = MakeOutgoingSpec(GE_RestoreValues, 1);
      for (const [attr, value] of record.PreApplyValues) {
        restoreSpec.SetByCallerMagnitude(attr, value);
      }
      ApplyGameplayEffectToTarget(record.TargetGC, restoreSpec);
    }
  }
}
```

`GE_RestoreValues` is an Instant Effect with one `Override` modifier per restored attribute, driven by `SetByCaller` magnitudes. Every undo operation passes through the standard Effect pipeline: it is observable, replicable, and appears in the Effect audit trail exactly like any other state change.

# Part VI: World & Spatial Model

## 17. World & Spatial Model

UGAS is otherwise position-agnostic: Attributes, Tags, Effects, and Abilities describe *what* an entity is and *what happens to it*, not *where* it is. Yet most genres need spatial reasoning — an area-of-effect blast, a weapon’s range, a perception radius, a capture zone. Until now the specification only *gestured* at space: `EffectContext.WorldOrigin` and `HitResult` (§9.9), the `WaitOverlap` / `WaitForTarget` tasks categorised "Spatial" with their tick budgets (§10.3, §10.6), the Avatar’s "spatial position for targeting" (§4.2), and the "range, line-of-sight" reachability check delegated to the title (§13.7). This section makes the spatial model **first-class and normative**.

Like Execution Calculations (§9.5), the spatial model is an **engine seam**: this specification defines the *data model* and the *query contract*; the implementing engine provides the spatial index (uniform grid, BVH, physics scene, tilemap, …) that answers the queries. UGAS does not mandate a partitioning structure — that is the subject of §17.6 — only that the queries defined here are answerable and behave as specified.

<div class="note">

This pillar is appended at §17 (rather than inserted among the Part II pillars) to avoid renumbering §4–§16 and the many cross-references to them, including those in the genre packs. It is nonetheless a core gameplay concept and is intended to be read alongside the Part II pillars.

</div>

### 17.1 Spatial Anchors

A **spatial anchor** is the position — and optional orientation — at which a Gameplay Controller exists in the world. Spatial queries operate over anchors, not over GCs directly, so a purely non-spatial GC (an inventory, a party roster, a global rules controller) simply has no anchor and is invisible to spatial queries.

``` typescript
struct SpatialAnchor {
  /**
   * The world position. The coordinate frame, units, and handedness are engine-defined; this
   * specification treats positions as opaque points and requires only that the §17.2 queries behave
   * as specified over them.
   */
  Position: Vector3;

  /** Optional facing, used by directional queries (cones, forward line-of-sight). Identity if absent. */
  Orientation?: Quaternion;

  /** The GC this anchor represents. */
  Owner: GameplayController;
}
```

The Avatar (§4.2) is the canonical source of a GC’s anchor: a spatially-present GC’s anchor position is its Avatar’s world position. A GC MAY also expose an anchor without an Avatar — for example a ground-targeted area effect anchored at a `WorldOrigin`; `EffectContext.WorldOrigin` (§9.9) is exactly the anchor of a positional effect application.

- A GC’s anchor, when it has one, MUST reflect its Avatar’s current world position at the time a query is evaluated.

- An implementation MUST treat a GC with neither an Avatar nor an explicit position as **non-spatial**: it is never returned by a spatial query and never participates in range, zone, or perception checks.

### 17.2 Spatial Query Model

All spatial gameplay reduces to a small set of **queries** over anchors. An implementation MUST provide a query provider satisfying the contract below; how it indexes anchors to answer them efficiently is its own concern (§17.6).

``` typescript
/** Restricts a query's candidate set before distance/shape tests are applied. */
struct SpatialFilter {
  /** Candidate must own ALL of these tags (§7, hierarchical). Empty = no tag requirement. */
  RequireTags?: GameplayTag[];

  /** Candidate must own NONE of these tags. */
  ExcludeTags?: GameplayTag[];

  /**
   * Affiliation of the candidate relative to the querying GC, resolved by the implementation's team
   * model: Any | Allied | Hostile | Neutral | SelfOnly | ExcludeSelf.
   */
  Affiliation?: Affiliation;

  /** Hard cap on the number of results (0 = unbounded), combined with a query's own ordering. */
  MaxResults?: int;
}

interface SpatialQuery {
  /** Distance between two anchors (or anchor and point), in engine units. */
  Distance(a: SpatialAnchor | Vector3, b: SpatialAnchor | Vector3): float;

  /** Anchors whose position lies within `radius` of `center`, matching `filter`. */
  OverlapSphere(center: Vector3, radius: float, filter: SpatialFilter): SpatialAnchor[];

  /** Anchors within an oriented box, a capsule, or a forward cone (directional shapes use Orientation). */
  OverlapBox(center: Vector3, halfExtents: Vector3, orientation: Quaternion, filter: SpatialFilter): SpatialAnchor[];
  OverlapCapsule(p0: Vector3, p1: Vector3, radius: float, filter: SpatialFilter): SpatialAnchor[];
  OverlapCone(apex: Vector3, direction: Vector3, range: float, halfAngleDeg: float, filter: SpatialFilter): SpatialAnchor[];

  /** Whether `b` is visible from `a` with no occluder between them. Occlusion is engine-defined. */
  LineOfSight(a: Vector3, b: Vector3): boolean;

  /** The `count` nearest anchors to `center` matching `filter`, ordered nearest-first. */
  Nearest(center: Vector3, count: int, filter: SpatialFilter): SpatialAnchor[];
}
```

#### Query semantics (normative)

1.  **Filter, then test.** `SpatialFilter` MUST be applied so only matching anchors are considered. Tag tests use the hierarchical semantics of §7 (a `RequireTags` of `Faction.Enemy` matches `Faction.Enemy.Elite`). `Affiliation` is resolved relative to the querying GC by the implementation’s team model.

2.  **Self handling.** A query MUST exclude the querying GC’s own anchor unless `Affiliation` is `SelfOnly` or otherwise includes self. `ExcludeSelf` is the appropriate default for area effects.

3.  **Determinism.** For a fixed world state and identical inputs, a query MUST return the same set, and ordered queries (`Nearest`) MUST return a stable order, with ties broken deterministically (e.g. by GC id). This is required for the predicted spatial queries of §17.7.

4.  **Non-spatial GCs** (§17.1) are never returned.

5.  **Cost.** Queries are not free. Their tick cadence is governed by the §10.6 spatial task budgets (gameplay-critical hit/target detection every frame; ambient/aura acquisition every 50–100 ms). Implementations SHOULD answer queries from a spatial partition (§17.6) rather than scanning all GCs.

<div class="note">

The remaining subsections build directly on this contract: range and area effects (§17.3) combine `OverlapSphere`/`OverlapCone` with a `MaxRange`; zones (§17.4) are standing region queries that grant tags on entry/exit; perception (§17.5) composes `OverlapSphere` with `LineOfSight`; partitioning (§17.6) is how an engine answers all of the above efficiently; and predicted spatial queries (§17.7) rely on the determinism of semantic rule 3.

</div>

### 17.3 Range and Area Application

The two most common spatial needs are expressed directly on the existing pillars via the §17.2 query model: an ability’s **range** and an effect’s **area** application.

#### Targeting range

An ability MAY declare a `MaxRange` (schema §8.7). When it targets another GC, the activation is valid only while the target’s anchor is within `MaxRange` of the instigator’s anchor (`SpatialQuery.Distance`, §17.2):

- A range-gated activation whose target is out of range MUST fail activation — it does not commit (§8.3). Under prediction the client MAY predict the range check, but the server’s reachability validation (§13.7) is authoritative.

- `MaxRange` absent or `0` means the ability is self-targeted or imposes no range gate.

- Range is measured between anchors (§17.1); an instigator or target without an anchor is, by definition, out of range for a range-gated ability.

#### Area application

By default an effect applies to a single target (`ApplyGameplayEffectToTarget`, §13.7). An effect MAY instead declare an `Area` (schema §9): it is applied to *every* anchor matching a filter within a shape, resolved by a single §17.2 query at the moment of application.

``` typescript
// Resolve the target set once, then apply to each, honoring the §9.6 execution policy.
function ApplyAreaEffect(instigator: GC, origin: Vector3, spec: EffectSpec, area: Area): void {
  const hits = area.Shape === "Cone"
    ? query.OverlapCone(origin, instigator.Facing, resolve(area.Radius), area.HalfAngleDeg, area.Filter)
    : query.OverlapSphere(origin, resolve(area.Radius), area.Filter); // Sphere
  for (const anchor of hits) // set already ordered + capped by MaxTargets
    ApplyGameplayEffectToTarget(anchor.Owner, spec);
}
```

Normative:

1.  The target set MUST be resolved by a single query at application time — an area effect *snapshots* who is in the area then; anchors entering the shape afterwards are not retroactively affected.

2.  `Area.Radius` MAY be `AttributeBased` (§9.4.2), so an upgrade or stat can scale the radius — the capability genre packs previously lacked (they hard-coded a constant radius in a task parameter).

3.  The origin is the application anchor: `EffectContext.WorldOrigin` (§9.9) for a ground-targeted cast, otherwise the instigator’s or target’s anchor.

4.  Each per-target application obeys the effect’s execution policy (§9.6) and the §13.7 authorization checks exactly as a single-target application would; `MaxTargets` caps the set after ordering.

5.  Under client-side prediction an area application is predicted only if its query is deterministic (§17.2 rule 3, §17.7); otherwise it defers to server authority.

### 17.4 Zones and Regions

A **zone** (region) is a standing volume in the world that grants Gameplay Tags to the GCs whose anchor is inside it, and removes them on exit. Zones formalise a pattern the specification previously only illustrated — the biome effects of §16.2 (mud/asphalt applied by vehicle position) and the "zone transition" buff-clearing of §14 — as a first-class, query-driven construct.

``` typescript
struct Region {
  /** Region identity, for authoring and debugging. */
  Name: string;

  /** The volume, as a §17.2 shape anchored in the world. */
  Shape: "Sphere" | "Box" | "Capsule";
  Origin: Vector3;             // sphere / box centre, or capsule reference point
  Radius?: float;              // Sphere and Capsule
  HalfExtents?: Vector3;       // Box
  Orientation?: Quaternion;    // Box
  P0?: Vector3; P1?: Vector3;  // Capsule endpoints

  /** Which GCs the region acts on (§17.2 SpatialFilter); empty = all spatial GCs. */
  Filter?: SpatialFilter;

  /** Tags granted to a GC while its anchor is inside the region; removed on exit. */
  GrantedTags: GameplayTag[];
}
```

#### Membership semantics (normative)

A region’s occupancy is a standing §17.2 query: the anchors inside `Shape` matching `Filter`.

1.  **Grant on entry, remove on exit.** When a GC’s anchor enters a region, the region MUST grant each of its `GrantedTags` to that GC; when the anchor leaves, the region MUST remove them. Grants use the reference-counted tag container of §7.2 — a GC inside two overlapping regions that grant the same tag holds it once per region and keeps it until it leaves both.

2.  **Tags, not direct mutation.** A region affects occupants only by granting tags (§3.1: state flows through tags and effects, never direct mutation). Gameplay reacts to those tags — e.g. a `Zone.Hazard.Fire` tag is the `ApplicationRequiredTags` of a burning Effect, or a `Biome.Snow` tag gates a cold-exposure Effect (as in §16.2).

3.  **Evaluation cadence.** Region membership is re-evaluated on the ambient §10.6 spatial budget (50–100 ms is sufficient for entry/exit). An implementation MAY instead use engine trigger-volume callbacks, provided the observable grant/remove semantics match.

4.  **Zone transition.** Leaving a region removes its granted tags, which in turn expires any Effect gated on them — the mechanism behind the §14 "clear temporary combat buffs on zone transition".

5.  **Persistence.** Region-granted tags are derived from occupancy and MUST NOT be persisted as owned state (§14 treats tags as derived); on load, occupancy is re-evaluated and the correct tags re-granted.

<div class="note">

A region is authored world content — the engine typically owns its placement (a trigger volume, a tilemap cell, a nav area). This section defines the *membership → tag-grant* contract; the authored/serialized representation of regions (a `RegionDefinition`) is provided by the reference implementation alongside the spatial pillar’s engine binding (§15 of the roadmap), not mandated here.

</div>

### 17.5 Perception and Awareness

Perception composes a range query with line-of-sight: an observer becomes *aware* of a target when the target is within the observer’s sense range AND visible to it. It is the basis of aggro, stealth detection, and AI target acquisition.

``` typescript
struct PerceptionConfig {
  /** Maximum sense range; MAY be AttributeBased (§9.4.2), e.g. reduced while blinded. */
  Range: float;

  /** Forward field-of-view half-angle in degrees; omitted = omnidirectional. */
  FovHalfAngleDeg?: float;

  /** Require unobstructed line-of-sight (§17.2) to sense the target. */
  RequireLineOfSight: boolean;

  /** Which GCs are sensed (§17.2 SpatialFilter) — typically Hostile. */
  Filter: SpatialFilter;
}
```

#### Semantics (normative)

Perception is a §17.2 query from the observer’s anchor:

1.  **Composition.** A target is perceived iff it is returned by `OverlapSphere(observerPos, Range, Filter)` — narrowed to `OverlapCone` when `FovHalfAngleDeg` is set — AND, when `RequireLineOfSight`, `LineOfSight(observerPos, targetPos)` is true.

2.  **Awareness as tags.** Perception state MUST be expressed as tags (or an Effect) on the observer, never as hidden state — e.g. acquiring a target grants `State.Perceiving` / triggers an aggro Effect; losing it removes the tag. This is the §17.4 zone pattern with the "region" being the observer’s own dynamic sense volume.

3.  **Cadence.** Perception is an ambient acquisition query and MUST honour the §10.6 budget (50–100 ms); it is not a per-frame gameplay-critical query unless a title requires it.

4.  **No implied symmetry.** A perceiving B does not imply B perceives A; each observer evaluates its own `PerceptionConfig`.

5.  **Determinism.** Like all §17.2 queries, perception is deterministic (for §17.7), though it is typically server-authoritative (AI runs on the server).

### 17.6 Spatial Partitioning

§17.2 defines the query contract; this section governs how an implementation answers it at scale. UGAS does not mandate a structure, but it bounds the cost.

#### Requirements

1.  **Sub-linear queries.** An implementation SHOULD answer `OverlapSphere` / `OverlapCone` / `Nearest` in better than O(n) over all GCs — via a spatial partition (uniform or hierarchical grid, BVH, k-d tree) or the host engine’s physics broadphase. A full scan is permitted only for small worlds.

2.  **Budget alignment.** Query cadence MUST respect the §10.6 spatial tick budgets: hit detection and targeting are gameplay-critical (evaluated the frame they are needed); lingering area effects, auras, and perception are ambient (50–100 ms). The partition exists so the ambient set can be re-queried at that cadence without a per-frame full scan.

3.  **Result bounds.** `SpatialFilter.MaxResults` (and `Area.MaxTargets`, `Nearest.count`) bound worst-case result size; an implementation MUST NOT allocate unboundedly per query (the reference implementation aggregates into reusable buffers, as the §5 attribute kernel does).

4.  **Staleness.** A partition MAY be rebuilt or incrementally updated; between updates an *ambient* query MAY reflect positions up to one ambient tick stale, but a gameplay-critical query MUST use current positions.

#### Non-normative guidance

For most titles a *uniform grid* keyed by `floor(position / cellSize)` (with `cellSize` ≈ the largest common query radius) gives near-O(1) neighbourhood queries and cheap incremental updates — this is what the reference implementation’s optional DOTS backend uses (a parallel spatial hash). Large open worlds benefit from a hierarchical grid or the engine’s broadphase; tile/grid games (§16.4) already *are* a partition — adjacency is a cell-index lookup, not a distance query.

### 17.7 Prediction of Spatial Queries

Client-side prediction (§13.4, §13.8) extends to spatial gameplay only under the determinism guarantee of §17.2 (semantic rule 3). A predicted ability whose activation depends on a spatial query — a range check (§17.3), an area target set (§17.3), a perceived target (§17.5) — MUST resolve that query identically on the predicting client and the authoritative server, or reconcile.

#### Semantics (normative)

1.  **Deterministic inputs.** A predicted query MUST run against state both ends agree on: positions in the prediction’s `CaptureState()` scope (§13.8.3) for the owning GC, and replicated positions for others. Where positions differ across the wire the query may mis-predict and MUST reconcile via §13.5 against the server’s authoritative result.

2.  **Stable ordering.** Ordered results (`Nearest`, and any `MaxTargets` / `MaxResults` truncation) MUST use the deterministic tie-break of §17.2 rule 3 so client and server select the same subset; an ambiguous order MUST NOT pick different targets on each end.

3.  **Cross-GC targets.** A predicted area or targeted effect hitting GCs the client does not own is speculative / local-visual only, reconciled from the server (§13.8.4) — the client MAY show the blast, but non-owned GCs change only on server confirmation.

4.  **Non-predictable queries.** A query depending on state the client cannot reproduce (server-only perception, hidden actors) MUST be marked non-predictable so the dependent activation aborts to server authority — the same escape hatch as §9.5 (randomised ExecutionCalculations) and §13.8.2 (prediction window).

This closes the World & Spatial Model: §17.1–17.2 define anchors and queries; §17.3 range and area; §17.4 zones; §17.5 perception; §17.6 how queries scale; §17.7 how they behave under prediction — the whole pillar resting on the single determinism guarantee of §17.2.

# Part VII: Scene Composition

## 18. Scene Composition

### 18.1 Overview

The pillars so far define gameplay *entities* — attributes (§5), tags (§7), effects (§9), abilities (§8), controllers (§4) — and the world model they act in (§17). They do not define how those entities are *instanced into a running world*: which controllers exist, where they stand, and with what initial state. That is the **content layer**, and it is the seam between an authored gameplay definition and a playable level.

Scene Composition is a portable, engine-agnostic description of that content. A **Scene** declares a set of **Placements** (controller instances at world poses, with startup state), the **Regions** (§17.4) that govern them, and the **Spawn Points** used for dynamic spawning. It composes from the existing pillars rather than introducing new gameplay mechanics: a placement references a §4 controller config, its startup state is expressed as §7 tags and §9 effects, its regions are §17.4 zones, and its runtime state persists through §14.

<div class="note">

Scene Composition is deliberately **not** a level-geometry or rendering format. It carries no meshes, materials, lighting, navigation meshes, or audio — those remain the engine’s scene representation. It is the **gameplay overlay**: the minimal, portable statement of *what gameplay entities exist, where, and in what starting state*, which an engine binding reifies against its own scene. An engine MAY store the overlay inside its native scene format; the contract is the model below, not a file format.

</div>

### 18.2 Placements

A **Placement** instantiates one `GameplayControllerConfig` (§4) at a world pose with optional startup overrides.

``` typescript
struct Placement {
  /** The GameplayControllerConfig to instantiate (§4), by name. */
  Controller: string;

  /** Stable identity for this instance — the key for persistence (§14) and cross-references. */
  InstanceId?: string;

  /** Spawn pose. The Position becomes the instance's spatial anchor (§17.1). */
  Position?: Vector3;
  Rotation?: Quaternion;

  /** Tags granted to the instance on spawn (§7) — team, role, difficulty band, etc. */
  StartupTags?: GameplayTag[];

  /** Effects applied to the instance on spawn (§9) — starting buffs, passives, loadout. */
  StartupEffects?: string[];

  /** Base-value overrides applied after the controller's defaults (§5) — e.g. an elite's Health. */
  AttributeOverrides?: Map<string, number>;

  /** Whether the instance spawns active; false authors a dormant/pre-placed entity. Default true. */
  Enabled?: boolean;
}
```

Normative:

1.  **Instancing.** Loading a Placement MUST create a Gameplay Controller from the named config (§4), fully initialised (its attribute sets, granted abilities, and startup/active effects from the config applied) exactly as if spawned at runtime.

2.  **Anchor.** If a `Position` is given, it becomes the instance’s spatial anchor (§17.1); the instance is registered with the spatial system (§17.2) so queries, areas, zones, and perception see it. A Placement without a `Position` is a non-spatial controller (§17.1) — valid for pure logic actors.

3.  **Startup state order.** After base initialisation, apply in this order: `AttributeOverrides` (base values, §5) → `StartupTags` (§7) → `StartupEffects` (§9). This mirrors the persistence restore order (§14.4) so a placed instance and a restored instance reach the same state.

4.  **Identity.** `InstanceId`, when present, MUST be unique within the loaded world and is the key under which §14 captures and restores this instance. Two Placements with the same `InstanceId` are an authoring error.

### 18.3 Scenes

A **Scene** is the composable, loadable unit of content.

``` typescript
struct Scene {
  /** Unique scene identifier. */
  Name: string;

  /** Parent scenes this one composes on top of, additively (§18.5). */
  Extends?: string[];

  /** Controller instances placed into the world. */
  Placements: Placement[];

  /** Standing zones active while the scene is loaded (§17.4). */
  Regions?: Region[];

  /** Named poses for dynamic spawning at runtime (§18.4). */
  SpawnPoints?: SpawnPoint[];
}
```

#### Load semantics (normative)

Loading a Scene MUST follow this order so that dependencies are satisfied as each step runs:

1.  **Regions first.** Instantiate every `Region` (§17.4) and begin evaluating occupancy. Establishing zones before placements means an instance spawned inside a zone receives its granted tags on its first spatial evaluation, not a frame late.

2.  **Placements next.** Instantiate each Placement in declaration order (§18.2). Declaration order is the tie-break for any order-dependent effect, so scene load is reproducible (§18.6).

3.  **Spawn points last.** Register each `SpawnPoint` (§18.4); they instantiate nothing at load.

Unloading a Scene reverses this: despawn placed instances (releasing their spatial registration and tags), then tear down regions. An instance’s persistable state MAY be captured (§14) before unload so a later reload resumes it.

### 18.4 Spawn Points

A **Spawn Point** is a named pose the running game spawns dynamic entities at — respawns, reinforcement waves, summoned minions, loot. Unlike a Placement it instantiates nothing at load; it is a labelled location gameplay selects at runtime.

``` typescript
struct SpawnPoint {
  /** Spawn point identifier, referenced by spawning logic. */
  Name: string;

  Position: Vector3;
  Rotation?: Quaternion;

  /** Classification tags for selection — team, wave, encounter (§7). */
  Tags?: GameplayTag[];
}
```

Selection is a §17.2 concern: "the nearest friendly spawn to the player" or "a random spawn tagged \`Spawn.Wave.2\`" is an ordinary spatial/tag query over the registered spawn points. The dynamic entity a spawn produces is itself a Placement (§18.2) created at runtime rather than at load.

### 18.5 Composition and Streaming

**Composition.** A Scene MAY `Extends` one or more parent scenes; the result is the additive union of their placements, regions, and spawn points — a base level plus an encounter overlay, or a shared arena plus a mode-specific ruleset. Merge is additive and order-preserving (parents first, in listed order, then this scene). An `InstanceId` or region `Name` that collides across composed scenes is an authoring error; an implementation MUST report it rather than silently pick a winner.

**Streaming.** Large worlds load and unload scenes as chunks. What is *active* is governed by the spatial partition (§17.6) and the ambient budget (§10.6); what *persists* across a load/unload cycle is governed by §14 — an instance keyed by `InstanceId` resumes its captured state when its chunk reloads. Region and perception tags are derived state (§17.4, §17.5): they are re-evaluated on load, never streamed.

### 18.6 Determinism and Persistence

Scene load MUST be deterministic: placements instantiate in declaration order (§18.3) and any randomised startup draws from the seeded stream of §9.5 / §13.8.1, so a given scene loads identically across machines and across a save/reload. This is what lets a replay (§14) or a predicted spawn (§13.8) reach the same world state the authoritative load produced.

Persistence composes directly: a loaded scene’s runtime state is the set of per-instance §14 snapshots keyed by `InstanceId`. Capturing the scene captures each instance’s base values, active effects, and granted abilities; restoring re-instantiates the scene, then applies each snapshot. Derived state — current values, region-granted tags (§17.4), perception (§17.5) — is recomputed, never serialised (§14.2), so a scene reloaded from a save is indistinguishable from one freshly composed and advanced to the same point.

# Mathematical Notation

## Variable Naming Conventions

| Symbol               | Meaning                       |
|----------------------|-------------------------------|
| $V$                  | Value (generic)               |
| $V_{base}$           | Base Value of an Attribute    |
| $V_{current}$        | Current Value of an Attribute |
| $V_{min}$, $V_{max}$ | Minimum/Maximum bounds        |
| $a$                  | Additive modifier magnitude   |
| $p$                  | Percentage modifier magnitude |
| $m$                  | Multiplicative factor         |
| $t$                  | Time variable                 |
| $\Delta_t$           | Time delta                    |
| $n$                  | Count/index variable          |

## Summation and Product Notation

*Summation* ($\sum$): Sum of values over an index range

$$\sum_{i=1}^{n} a_i = a_1 + a_2 + \cdots + a_n$$

*Product* ($\prod$): Product of values over an index range

$$\prod_{k=1}^{n} m_k = m_1 \times m_2 \times \cdots \times m_n$$

## Set Theory Notation for Tags

| Notation    | Meaning                                     |
|-------------|---------------------------------------------|
| T           | A single Tag                                |
| C           | A TagContainer (set of Tags)                |
| T ∈ C       | Tag T is a member of Container C            |
| C₁ ⊆ C₂     | Container C₁ is a subset of C₂              |
| C₁ ∩ C₂     | Intersection of two containers              |
| C₁ ∪ C₂     | Union of two containers                     |
| C₁ ∩ C₂ ≠ ∅ | Containers have at least one common element |

# Complete Schema Reference

## Schema URL Versioning Policy

All `$schema` URLs in UGAS data files use the pattern:

    https://ugas.jbltx.com/{version}/schemas/{schema-name}.json

Where `{version}` is the published UGAS release the data file was authored against (e.g. `v1.0.0-draft.5`). This is the canonical, resolvable URL: it is served by the docs site, and each schema’s own `$id` is set to the same URL, so an authored file’s `$schema` both identifies and (when a network is available) resolves to the exact schema it was validated against. Each released version MUST maintain stable schema URLs — schemas at a given version MUST NOT be modified after release.

Data files SHOULD pin to the exact UGAS version they were authored against. Tooling that processes UGAS data files SHOULD validate against the schema declared in `$schema`; because the `$schema` value is a stable **identifier**, validators MAY resolve it offline (e.g. against the version’s bundled schema set) rather than over the network, and SHOULD fail clearly when the schema cannot be resolved rather than silently skipping validation.

## GameplayController Schema Definition

``` yaml
# Gameplay Controller Interface Schema Definition
# Based on UGAS Specification v1.0.0-draft.5 - Section 4

type: object
required:
  - OwnerActor
  - AttributeSets
properties:
  OwnerActor:
    type: object
    description: Logical owner of the GC (responsible for lifecycle, network authority, persistence)
    properties:
      ActorID:
        type: string
        description: Unique identifier for the owner actor
      ActorType:
        type: string
        description: Type of the owner actor

  AvatarActor:
    type: object
    description: World spatial representation (optional, can be same as Owner)
    properties:
      ActorID:
        type: string
        description: Unique identifier for the avatar actor
      ActorType:
        type: string
        description: Type of the avatar actor

  AttributeSets:
    type: array
    items:
      type: object
      properties:
        Name:
          type: string
          description: AttributeSet identifier
        Attributes:
          type: array
          items:
            type: object
            properties:
              Name:
                type: string
              BaseValue:
                type: number
              CurrentValue:
                type: number
    minItems: 1
    description: Registered attribute containers

  GrantedAbilities:
    type: array
    items:
      type: object
      required:
        - AbilityClass
      properties:
        AbilityClass:
          type: string
          description: Ability class identifier
        Level:
          type: integer
          default: 1
          minimum: 1
          description: Ability level
        InputID:
          type: string
          description: >-
            Input binding identifier. References an Action Name from the input
            layer. When the bound Action triggers, the GC calls TryActivateAbility
            for this grant.
        Handle:
          type: string
          description: Unique handle for this granted ability instance
        bIsActive:
          type: boolean
          default: false
          description: Whether the ability is currently active
    description: All abilities granted to this GC

  ActiveEffects:
    type: array
    items:
      type: object
      required:
        - Handle
        - EffectClass
      properties:
        Handle:
          type: string
          description: Unique identifier for this active effect
        EffectClass:
          type: string
          description: GameplayEffect class reference
        DurationPolicy:
          type: string
          enum: [HasDuration, Infinite]
          description: Duration policy of the originating effect (§14.3)
        RemainingDuration:
          type: number
          description: >-
            Remaining duration in seconds. Present only for HasDuration
            effects (§14.3.1)
        Stacks:
          type: integer
          minimum: 1
          default: 1
          description: Number of effect stacks
        StartTime:
          type: number
          description: Timestamp when effect was applied
        Level:
          type: integer
          minimum: 1
          default: 1
        InstigatorGC:
          type: string
          description: Reference to the GC that caused this effect
        SourceAbility:
          type: string
          description: >-
            Ability that applied this effect (for provenance tracking,
            §14.3.2)
        PeriodicState:
          type: object
          description: >-
            Periodic execution state for effects with Period settings
            (§14.3.3)
          properties:
            PeriodElapsed:
              type: number
              description: Seconds elapsed since last periodic execution
            ExecutionCount:
              type: integer
              minimum: 0
              description: Total periodic executions fired
        CapturedAttributes:
          type: object
          additionalProperties:
            type: number
          description: >-
            Attribute values captured OnApplication, keyed by attribute
            name (§14.3)
        SetByCallerMagnitudes:
          type: object
          additionalProperties:
            type: number
          description: >-
            Runtime-provided magnitudes, keyed by data tag (§14.3)
    description: Currently active effects applied to this GC (serialization protocol §14)

  ActiveActionSets:
    type: array
    items:
      type: string
    description: Currently active ActionSet names (derived from tag evaluation at runtime)

  OwnedTags:
    type: array
    items:
      type: string
      pattern: "^[A-Z][a-zA-Z0-9]*(\\.[A-Z][a-zA-Z0-9]*)*$"
    description: Current semantic state tags (hierarchical dot notation)

  ReplicationMode:
    type: string
    enum: [Minimal, Mixed, Full, None]
    default: Mixed
    description: "Replication strategy: Minimal (only cues & tags for AI), Mixed (full to owner, minimal to others for players), Full (complete to all for single-player/spectators), None (no replication for server-only)"

  bIsActive:
    type: boolean
    default: true
    description: Whether this GC is currently active

  Metadata:
    type: object
    description: Optional metadata for display and debugging
    properties:
      DisplayName:
        type: string
      Description:
        type: string
      Tags:
        type: array
        items:
          type: string
      DebugCategory:
        type: string
```

## Attribute Schema Definition

``` yaml
# Attribute Definition Schema
# Based on UGAS Specification v1.0.0-draft.5 - Appendix B

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
          - type: string
            description: Attribute reference
      Max:
        oneOf:
          - type: number
          - type: string
            description: Attribute reference
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

## AttributeSet Schema Definition

``` yaml
# AttributeSet Definition Schema
# Based on UGAS Specification v1.0.0-draft.5 - Appendix B

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
      $ref: "#/$defs/Attribute"
  Metadata:
    type: object
    properties:
      DisplayName:
        type: string
      Description:
        type: string

$defs:
  Attribute:
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
              - type: string
          Max:
            oneOf:
              - type: number
              - type: string
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

## Ability Schema Definition

``` yaml
# Ability Definition Schema
# Based on UGAS Specification v1.0.0-draft.5 - Appendix B

type: object
required:
  - Name
properties:
  Name:
    type: string
    description: Unique identifier for this ability
  Tags:
    type: object
    properties:
      AbilityTags:
        type: array
        items:
          type: string
        description: Tags that describe this ability
      BlockedByTags:
        type: array
        items:
          type: string
        description: Tags that prevent this ability from running
      BlockAbilitiesWithTags:
        type: array
        items:
          type: string
        description: While this ability is active, block abilities with these tags
      CancelAbilitiesWithTags:
        type: array
        items:
          type: string
        description: Cancel abilities with these tags when this ability activates
      ActivationRequiredTags:
        type: array
        items:
          type: string
        description: Tags required on the GC to activate this ability
      ActivationBlockedTags:
        type: array
        items:
          type: string
        description: Tags that block activation of this ability
      ActivationOwnedTags:
        type: array
        items:
          type: string
        description: Tags granted to the GC while this ability is active
  Cost:
    type: string
    description: Reference to cost GameplayEffect
  Cooldown:
    type: string
    description: Reference to cooldown GameplayEffect
  MaxRange:
    type: number
    minimum: 0
    description: "Maximum targeting range in engine units (§17.3). Absent or 0 means self-targeted / no range gate; a target-requiring activation MUST be within range (§17.2 Distance), validated server-side per §13.7."
  AsyncValidation:
    type: object
    description: Optional asynchronous server-side validation for activation (§8.8). When present and Required is true, an activation that passes the synchronous checks enters PendingConfirmation before Commit instead of committing synchronously.
    properties:
      Required:
        type: boolean
        description: If true, route activation through the PendingConfirmation state and await server validation before Commit. Absent or false keeps the synchronous Validating -> Commit behaviour.
      Kind:
        type: string
        description: Category of asynchronous validation, e.g. AntiCheat | RemoteInventory | Entitlement | Custom.
      TimeoutMs:
        type: number
        description: Maximum time to wait for the validation result before treating it as an asynchronous failure (transition Fail -> Granted, nothing consumed).
      Predicted:
        type: boolean
        description: If true, the owning client MAY speculatively commit and enter Active while the server holds PendingConfirmation, reconciling via the prediction model (§13.8).
  Tasks:
    type: array
    items:
      type: object
      required:
        - Type
      properties:
        Type:
          type: string
          description: Task type identifier
        Params:
          type: object
          description: Task-specific parameters
        TickInterval:
          type: number
          description: Seconds between task ticks; 0 means every frame. Only meaningful for ticking tasks.
        Priority:
          type: integer
          description: Tick scheduling priority when the per-frame tick budget is exhausted; higher ticks first.
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

## Effect Schema Definition

``` yaml
# GameplayEffect Definition Schema
# Based on UGAS Specification v1.0.0-draft.5 - Appendix B

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
        description: Time interval for periodic execution
      ExecuteOnApplication:
        type: boolean
        default: false
        description: Whether to execute immediately on application
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
    description: >-
      Override conflict resolution priority. When multiple active effects apply an Override
      modifier to the same Attribute, the effect with the highest Priority value wins.
      On equal Priority, last-applied wins (LIFO). Negative values are valid.
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
          description: Custom calculation class reference
  GrantedTags:
    type: array
    items:
      type: string
    description: Tags granted while this effect is active
  ApplicationRequiredTags:
    type: array
    items:
      type: string
    description: Tags required on target for effect to apply
  GrantedAbilities:
    type: array
    items:
      type: object
      properties:
        AbilityClass:
          type: string
          description: Ability class to grant
        Level:
          type: integer
          default: 1
          description: Level of the granted ability
        InputID:
          type: string
          description: Optional input binding
        RemoveOnEffectRemoval:
          type: boolean
          default: true
          description: Remove ability when effect expires
  GameplayCues:
    type: array
    items:
      type: string
    description: Visual/audio cues to trigger
  Area:
    type: object
    description: "Optional area application (§17.3). When present, the effect applies to every anchor matching the filter within the shape (via the §17.2 spatial queries) instead of a single target; the execution policy (§9.6) governs per-target combination."
    required:
      - Shape
    properties:
      Shape:
        type: string
        enum:
          - Sphere
          - Cone
        description: "Query shape centered at the application origin (EffectContext.WorldOrigin, §9.9)."
      Radius:
        $ref: "#/$defs/MagnitudeDefinition"
        description: "Sphere radius / cone range. May be AttributeBased to scale with an attribute (§9.4.2)."
      HalfAngleDeg:
        type: number
        minimum: 0
        maximum: 180
        description: "Cone half-angle in degrees (Cone shape only)."
      RequireTags:
        type: array
        items:
          type: string
        description: "Candidate must own all these tags (§7, hierarchical). Empty = no requirement."
      ExcludeTags:
        type: array
        items:
          type: string
        description: "Candidate must own none of these tags."
      Affiliation:
        type: string
        enum:
          - Any
          - Allied
          - Hostile
          - Neutral
          - SelfOnly
          - ExcludeSelf
        default: ExcludeSelf
        description: "Affiliation of candidates relative to the applying GC (§17.2)."
      MaxTargets:
        type: integer
        minimum: 0
        description: "Cap on affected targets (0 = unbounded), applied after ordering."

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
        description: Static value for ScalableFloat
      Curve:
        type: string
        description: Curve table reference
      CurveInput:
        type: string
        description: Input parameter for curve evaluation
      BackingAttribute:
        type: string
        description: Attribute to use for AttributeBased magnitude
      Source:
        type: string
        enum:
          - Source
          - Target
        description: Which GC to read the backing attribute from
      Coefficient:
        type: number
        default: 1
        description: Multiplicative coefficient
      PreMultiplyAdditive:
        type: number
        default: 0
        description: Value added before multiplication
      PostMultiplyAdditive:
        type: number
        default: 0
        description: Value added after multiplication
      CalculatorClass:
        type: string
        description: Custom calculation class for CustomCalculation type
      DataTag:
        type: string
        description: Tag for SetByCaller data lookup

  Modifier:
    type: object
    required:
      - Attribute
      - Operation
      - Magnitude
    properties:
      Attribute:
        type: string
        description: Target attribute to modify
      Operation:
        type: string
        enum:
          - Add
          - AddPost
          - Multiply
          - Override
        description: >-
          Mathematical operation to apply.
          Add: pre-multiply flat additive (pipeline step 2, before percentage and multiply steps).
          AddPost: post-multiply flat additive (pipeline step 7, after all multiply steps; very rare).
          Multiply: multiplicative factor at step 6 — use a reciprocal magnitude (e.g. 0.5) instead of a Divide operation.
          Override: replaces the computed result at step 8.
      Magnitude:
        $ref: "#/$defs/MagnitudeDefinition"
      Channel:
        type: string
        description: >-
          Optional named aggregation channel. Modifiers in the same channel sum together;
          modifiers in different channels multiply against each other. Used for damage-bucket
          systems (see §16.3). Defaults to the global channel if omitted.
```

## Tag Schema Definition

``` yaml
# Tag Registry Schema
# Based on UGAS Specification v1.0.0-draft.5 - Appendix B

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
          description: Hierarchical tag in dot notation (e.g., State.Debuff.Stunned)
        Description:
          type: string
        AllowMultiple:
          type: boolean
          default: false
        DevComment:
          type: string
```

# References and Citations

## BibTeX Entries

``` bibtex
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

# Document History

| Version | Date          | Author          | Changes               |
|---------|---------------|-----------------|-----------------------|
| 1.0     | February 2026 | Mickael Bonfill | Initial specification |

*End of Specification*
