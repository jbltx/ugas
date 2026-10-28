# Preamble

Copyright 2026 Mickael Bonfill

This Specification is released under the [MIT License](https://opensource.org/licenses/MIT). Permission is hereby granted, free of charge, to any person obtaining a copy of this Specification and associated documentation files, to deal in the Specification without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Specification, and to permit persons to whom the Specification is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Specification.

The author makes no, and expressly disclaims any, representations or warranties, express or implied, regarding this Specification, including, without limitation: merchantability, fitness for a particular purpose, non-infringement of any intellectual property, correctness, accuracy, completeness, timeliness, and reliability. Under no circumstances will the author or contributors be liable for any damages, whether direct, indirect, special or consequential damages for lost revenues, lost profits, or otherwise, arising from or in connection with this Specification or the use or other dealings in this Specification.

All product names, game titles, engine names, and company names mentioned in this Specification are trademarks or registered trademarks of their respective owners. They are used for identification and illustration only. Their use does not imply any affiliation with, sponsorship by, or endorsement from their owners. This Specification is an independent work and is not affiliated with any of the companies named in it.

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

``` mermaid
flowchart TB
    accTitle: The four UGAS pillars
    accDescr: Inside the Gameplay Controller, the data, semantic, and logic layers connect to the mutation layer.
    subgraph GC[Gameplay Controller]
        Data["Data layer<br/>Attributes<br/>Attribute Sets"]
        Semantic["Semantic layer<br/>Gameplay Tags<br/>Tag Containers"]
        Logic["Logic layer<br/>Gameplay Abilities<br/>Ability Tasks"]
        Mutation["Mutation layer<br/>Gameplay Effects<br/>Modifiers<br/>Execution Calcs"]
        Data --> Mutation
        Semantic --> Mutation
        Logic --> Mutation
    end
```

Data Layer (Attributes)  
Numeric state representation. Attributes store quantitative values such as Health, Mana, Strength, and Speed. All numeric gameplay state MUST be represented through Attributes.

Semantic Layer (Tags)  
Qualitative state representation. Tags describe "what kind" or "in what state" an Actor exists. Tags enable logic gating, ability requirements, and state queries without coupling to specific implementations.

Logic Layer (Abilities)  
Behavioral definitions. Abilities encapsulate the asynchronous, stateful logic of actions Actors can perform. Abilities coordinate with Tasks for complex, multi-stage execution.

Mutation Layer (Effects)  
State change mechanism. Effects are the ONLY authorized mechanism for modifying Attributes or Tags. This restriction ensures all state changes are tracked, predicted, and synchronized. Ability implementations MUST NOT call `Tags.AddTag()`, `Tags.RemoveTag()`, or any equivalent direct tag mutation API. All tag state changes MUST flow through a `GameplayEffect` applied via the GC’s effect application pipeline. This is a deliberate departure from UE4 GAS (which permits "loose tags") and is the property that makes replication of tag state tractable.

### 3.2 Component Relationships

``` mermaid
flowchart TB
    accTitle: UGAS component relationships
    accDescr: The owner owns the Gameplay Controller and the avatar possesses it. The controller contains attribute sets, ability specs, a tag container, and active effects. Abilities use tasks and effects carry modifiers.
    Avatar["Actor (Avatar)"] -->|possesses| GC[Gameplay Controller]
    Owner[Owner Actor] ---|owns| GC
    GC ---|contains| Attributes[Attribute Sets]
    GC --> Abilities["Abilities (Specs)"]
    GC --> Tags["Tags (Container)"]
    GC --> Effects["Effects (Active)"]
    Abilities --> Tasks
    Effects --> Modifiers
```

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

``` mermaid
flowchart TB
    accTitle: Shared owner and avatar
    accDescr: An AI enemy contains a Gameplay Controller whose owner and avatar both reference that same enemy.
    subgraph Enemy[AI Enemy]
        GC["Gameplay Controller<br/>Owner: this<br/>Avatar: this"]
    end
```

#### Split-Actor Configuration

For player-controlled characters in networked games, the Owner and Avatar SHOULD be separate to ensure GC persistence across respawns:

``` mermaid
flowchart LR
    accTitle: Separate owner and avatar
    accDescr: The Player State persists for the entire session and owns the Gameplay Controller. Its avatar reference points to the Player Character, which is destroyed on death.
    subgraph Owner[Player State]
        GC["Gameplay Controller<br/>Owner: this<br/>Persists entire session"]
    end
    GC -->|Avatar reference| Avatar["Player Character<br/>(destroyed on death)"]
```

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

This applies only to **Instant** effects. A durational (Infinite / HasDuration) effect’s `Multiply` modifiers are Current-Value modifiers (§5.3) and are never written to the Base Value — including on the periodic ticks of a periodic durational effect, whose executions apply only `Add` / `AddPost` / `Override` to the Base Value (a periodic `Multiply`-to-base would double-count against the effect’s own Current-Value contribution and compound every tick). A percentage change that must be **permanent** is authored as an Instant `Multiply`; a percentage change that lasts **while an effect is active** is a durational `Multiply` in the Current-Value pipeline.

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

Given: - Base Value: 100 - `Add` Modifier 1: +20 - `Add` Modifier 2: +10 - `Multiply` Modifier 1: +0.10, `Channel: "Gear"` - `Multiply` Modifier 2: +0.15, `Channel: "Gear"` - `Multiply` Modifier 3: +0.50, `Channel: "Legendary"` - `Multiply` Modifier 4: +1.00, no `Channel` (implicit singleton) - No `AddPost`, no `Override`

Calculation:

    Step 1:   flat = 20 + 10 = 30
    Step 2:   value = 100 + 30 = 130
    Step 3:   channels → "Gear" = 1 + 0.10 + 0.15 = 1.25
                         "Legendary" = 1 + 0.50 = 1.50
                         <singleton> = 1 + 1.00 = 2.00
    Step 4:   value = 130 × 1.25 × 1.50 × 2.00 = 487.5
    Step 5:   value += 0  (no AddPost)
    Step 6:   no Override
    Step 7:   clamp to the attribute's bounds

Current Value = 487.5

Note that the two `Gear` modifiers **add** their magnitudes into a single ×1.25 factor rather than compounding as `1.10 × 1.15`, while the separate channels multiply — this is the power-creep control described above. A modifier with no `Channel` is its own singleton, not a member of a shared global channel.

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

Rule 1 means the **clamped** Current Value — §5.3 places clamping inside the definition of the Current Value (step 7 of the pipeline), so a bound resolves to the value a reader of the referenced Attribute would observe, not to its unclamped pipeline result. Resolving against the unclamped result would let a dependent Attribute exceed the very bound it references: if `MaxHealth` is itself capped at `200` and carries a `+500` buff, `Health` bounded by `Max: "MaxHealth"` MUST be limited to `200`, not to `700`.

Because a Current Value includes the referenced Attribute’s active modifiers, a bound is **temporary** when they are. An Instant Effect that writes the Base Value while a referenced bound is temporarily reduced is clamped to the reduced bound (§5.2), and that write is permanent — the Base Value does not recover when the modifier expires. Implementations SHOULD surface this in tooling, as it is a common source of surprise.

> *Note:* When a resolved `Min` exceeds a resolved `Max`, `Min` wins. This follows from the §5.3 formula $max(V_{min}, min(V_{max}, x))$, in which the `Min` clamp is applied last. Dynamic bounds make the case reachable, so implementations MUST NOT reverse the order.

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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/attribute_set.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/attribute_set.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/attribute_set.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/attribute_set.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_tag.json
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

  /** Runtime attempt identity is separate from the reusable grant Handle. */
  AttemptId?: uint64;
  State: AbilityState;
  ValidationDeadline?: number; // server monotonic milliseconds
  TerminalOutcome?: "Accepted" | "Rejected" | "Cancelled";

  /** Is currently active? PendingConfirmation is false. */
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

``` mermaid
flowchart TB
    accTitle: Gameplay Ability lifecycle
    accDescr: Granting enables activation. Synchronous checks may fail or route to asynchronous confirmation or commit. Failed validation or commit returns to Granted. Successful commit enters Active; ending or cancellation returns through Ending to Granted.
    NotGranted -->|Grant| Granted
    Granted -->|TryActivate| Validating["Validating<br/>Synchronous checks"]
    Validating -->|Fail| Granted
    Validating -->|Pass| AsyncRequired{"Async required?"}
    AsyncRequired -->|Yes| PendingConfirmation
    AsyncRequired -->|No| Commit[Recheck + Commit]
    PendingConfirmation -->|Fail / cancel| Granted
    PendingConfirmation -->|Success| Commit
    Commit -->|Fail| Granted
    Commit -->|Success| Active
    Active -->|End / Cancel| Ending
    Ending --> Granted
```

- Predicting client: capture first, then speculative Commit/Active.

- Server: remain PendingConfirmation until validation and recheck succeed.

- Success AND failure: reconcile authoritative state and replay eligible later inputs (§13.5).

- Cancelled/ended local presentation is never resurrected by a late response.

### 8.3 Activation Requirements

Before an Ability can activate, the following checks MUST pass:

1.  *Granted Check*: Ability must be granted to the GC

2.  *No Conflicting Activation*: A single-instance ability must be neither active nor pending validation. Multiple-instance abilities require separate attempt state for each instance.

3.  *Required Tags*: Owner must have all tags in `ActivationRequiredTags`

4.  *Blocked Tags*: Owner must NOT have any tags in `ActivationBlockedTags`

5.  *Cost Verification*: If CostEffect is defined, owner must have sufficient resources

6.  *Cooldown Verification*: Cooldown tag must not be present

``` typescript
function CanActivateAbility(spec: AbilitySpec): boolean {
  if (!IsStillGranted(spec) || HasConflictingActiveOrPendingAttempt(spec)) return false;
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

Commit is the serialized point at which authoritative resources are consumed and cooldowns begin. Recheck mutable activation requirements immediately before it, excluding only the current attempt from the pending-conflict check. Check and commit MUST run on the same GC mutation executor, without a yield between them. A failed commit MUST leave no partial cost, cooldown, or activation-tag effects and MUST NOT enter Active. Speculative client commit is reversible through §13.5. Once authoritative commit succeeds:

1.  Cost Effect is applied (resources consumed)

2.  Cooldown Effect is applied (cooldown tag granted)

3.  Activation Owned Tags are granted

4.  Ability proceeds to execution

``` typescript
function CommitAbility(spec: AbilitySpec): boolean {
  // Internal GC transaction: defer callbacks until the attempt is terminal (§8.8).
  // On any failure roll back staged effects and return false.
  const transaction = BeginCommitTransaction(spec);
  if (!RecheckMutableRequirements(spec, spec.AttemptId)) return transaction.Fail();
  // Apply cost
  if (spec.AbilityClass.CostEffect) {
    const costSpec = MakeOutgoingSpec(spec.AbilityClass.CostEffect, spec.Level);
    if (!transaction.StageEffect(costSpec)) return transaction.Fail();
  }

  // Apply cooldown
  if (spec.AbilityClass.CooldownEffect) {
    const cooldownSpec = MakeOutgoingSpec(spec.AbilityClass.CooldownEffect, spec.Level);
    if (!transaction.StageEffect(cooldownSpec)) return transaction.Fail();
  }

  // Grant activation tags via an auto-generated Infinite Effect.
  // Direct tag mutation is prohibited (§3.1); all tag state flows through Effects.
  if (!spec.AbilityClass.ActivationOwnedTags.IsEmpty()) {
    const ownedTagsSpec = MakeOwnedTagsEffect(spec.AbilityClass.ActivationOwnedTags, spec.Level);
    // On commit publish its handle as spec.ActiveOwnedTagsHandle.
    if (!transaction.StageOwnedTagsEffect(ownedTagsSpec)) return transaction.Fail();
  }

  return transaction.Commit();
}
```

### 8.5 Costs and Cooldowns as Effects

Costs and Cooldowns are NOT separate variables but are implemented as specialized Gameplay Effects.

#### Cost Effect Pattern

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_effect.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_effect.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_effect.json
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
    TimeoutMs: number             # Positive monotonic ms; omitted uses finite adapter default
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

An activation may require an asynchronous server-side decision (anti-cheat, remote inventory, or entitlement). The optional `AsyncValidation` marker selects this path. When `Required` is absent or false, activation retains the synchronous §8.3 → §8.4 path. `Predicted` defaults to false; true requires `Required: true`. `Kind` remains an extensible adapter-defined string.

#### 8.8.1 The PendingConfirmation State

An activation passing §8.3 with `AsyncValidation.Required == true` MUST enter `PendingConfirmation` before authoritative Commit. While pending it MUST NOT consume cost, start cooldown, grant ActivationOwnedTags, or execute authoritative gameplay Tasks. `IsActive` is false, but the pending attempt blocks another activation of a single-instance ability. Presentation-only wind-up is permitted. Multiple-instance abilities require distinct attempt records; one shared `spec.State` cannot represent several concurrent validations.

Every activation has an immutable attempt ID distinct from its grant handle, even without client prediction. Callbacks, timeout/cancel messages, and prediction keys identify that attempt. IDs MUST NOT be reused within an epoch; stale messages cannot apply to a new attempt on the same grant. Ungrant, owner death/destruction, or disconnect MUST retire affected pending attempts and release their timers/reservations according to the adapter contract.

An explicit `TimeoutMs` MUST be finite and greater than zero. If omitted, the adapter MUST supply and document a finite positive default. The server sets the deadline from its own monotonic clock at entry to pending. Timeout is elapsed real time, unaffected by gameplay pause or time scale. Async success at or after the deadline is failure, even if the timeout callback has not yet run. Client prediction has its separate, usually shorter, §13.8.2 window.

#### 8.8.2 Transition Table

| From                | To                  | Trigger                                                                                          |
|---------------------|---------------------|--------------------------------------------------------------------------------------------------|
| Validating          | Commit → Active     | Synchronous-only checks and commit succeed.                                                      |
| Validating          | PendingConfirmation | Async required; synchronous checks pass; reserve an attempt ID.                                  |
| Validating          | Granted             | Check/commit fails; no partial mutation survives.                                                |
| PendingConfirmation | Commit → Active     | Matching attempt succeeds before deadline, mutable requirements still pass, and commit succeeds. |
| PendingConfirmation | Granted (Fail)      | Validation failure, deadline expiry, failed recheck, or failed commit.                           |
| PendingConfirmation | Granted (Cancel)    | Cancellation, interruption, ungrant, or owner teardown wins before commit.                       |
| Speculative Active  | Reconciled state    | Authoritative success or failure via §13.5; local cost/timing may differ.                        |

Pending failure/cancellation consumes no authoritative resources. All exits terminalize the attempt exactly once. A terminal result cannot change merely because another callback arrives. A rejected parent attempt rejects dependent predicted children per §13.8.4.

#### 8.8.3 Path A — Server-Authoritative Async Validation (No Prediction)

Validation completion, timeout, cancellation, and commit MUST be serialized on the GC mutation executor. Checking an ID/state on a worker thread and committing later is not sufficient. After the wait, recheck grant/owner validity, tags, cost, cooldown, target eligibility, and any validation-result expiry. Ignore only the current attempt in the pending-conflict check. The recheck and §8.4 transaction cannot yield; two abilities cannot spend the same last resource.

``` typescript
function StartAsyncActivation(spec: AbilitySpec, request: ActivationRequest): void {
  // Runs on the GC mutation executor; SubmitOnce retransmits share request identity.
  if (ReturnExistingOutcomeIfDuplicate(request)) return;
  if (!CanActivateAbility(spec)) { RejectOnce(request); return; }
  const attempt = RegisterPendingAttempt(spec, request, EffectiveTimeout(spec));
  // Register pending state and timer BEFORE invoking a possibly synchronous callback.
  BeginAsyncValidation(attempt.Id, result =>
    GC.EnqueueMutation(() => ResolveValidation(spec, attempt.Id, result)));
}

function ResolveValidation(spec: AbilitySpec, id: AttemptId, result: ValidationResult): void {
  const attempt = GetPendingAttempt(spec, id);
  if (!attempt) return; // A cancelled, B pending: A's result cannot act on B.
  if (!result.ok || MonotonicMillis() >= attempt.Deadline ||
      !RecheckMutableRequirements(spec, id) || !CommitAbility(spec)) {
    TerminalizeBeforeCallbacks(attempt, Rejected); // invalidate ID; cancel timer; cleanup
    PublishOutcomeOnce(attempt);
    return;
  }
  TerminalizeBeforeCallbacks(attempt, Accepted);
  ActivateAbility(spec);
  PublishOutcomeOnce(attempt); // complete group update, including authoritative state
}
```

Commit stages effects and defers reentrant callbacks until terminalization. Cancellation processed before commit invalidates the attempt first, then attempts to abort the remote validation. Aborting is best effort: late results MUST be discarded. Cancellation processed after successful commit follows §8.6’s active-ability cancellation policy, including its cost/cooldown rules; it cannot retroactively turn success into an uncommitted attempt.

Remote inventory reservations or purchases require an adapter-defined idempotent reserve/commit/release protocol using the attempt ID. A local gameplay rollback cannot undo an external service transaction. The adapter MUST not treat an irreversible remote operation as speculative client work.

#### 8.8.4 Path B — Client-Side Prediction

When `AsyncValidation.Predicted == true`, the owning client MAY speculatively commit while the server holds PendingConfirmation. Use exactly the §13.4 request/prediction procedure: capture before any mutation, check eligibility and finite limits, then submit once whether or not prediction was possible. A window guard MUST NOT return before authority submission. The authoritative server commits only after successful validation and rechecking requirements.

Both success and rejection feed the §13.5 reconciliation procedure, using the attempt’s group and authoritative state revision. Success does not mean “no change”: cooldown timing, cost, targets, or intervening server state may differ. Rejection removes the speculative cost, cooldown, tags, and dependent effects. Do not restore an old attempt snapshot over later confirmed changes; rebuild the eligible replay suffix instead.

A group result includes all Sub outcomes (§13.8.4). Parent success with child failure is permitted, but accepted children require accepted ancestors. Pending validation prevents a terminal group result and cannot advance the resolved-input watermark.

#### 8.8.5 Interaction with Cancellation, Interruption, and the Prediction Window

Cancel a pending authoritative attempt by matching ID, invalidate it before cleanup, stop its timer, and emit at most one terminal result. It has no committed cost/cooldown to reverse and no ActivationOwnedTags effect to remove. Stale success, cancellation, and timer callbacks MUST NOT affect a later attempt on the same grant.

Client cancellation stops speculative presentation and sends an idempotent cancel for that attempt. The server determines whether cancel or commit won; replicated state may still show a cost/cooldown if commit won. A late confirmation MUST NOT resurrect an ended/cancelled local activation or emit its cues again. Terminal and presentation-retirement information survives local rollback until safe to retire under §13.8.5.

Prediction expiry restores authoritative state and retires speculation; it does not cancel the remote request. Late authority may update state once but cannot execute the activation a second time. An ability whose expected validation delay exceeds the prediction window SHOULD use Path A to avoid routine visual correction.

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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_effect.json
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

3.  **Stream positioning (reproducibility).** One runtime-owned stream belongs to each activation Sub. All calculations/effects caused by that activation share its cursor; creating a fresh stream for every `Execute()` is forbidden. Effects retain the stream if they outlive their originating ability. Schedule draws by simulation step, effect application order (or stable handle order for simultaneous periodic ticks), calculation declaration order, and §17.2 target order. Async callback arrival order MUST NOT determine draw order. Snapshot the stream state and raw-draw count; restore them before replay, without allocating a new seed or Sub. The runtime releases a stream only after its last consumer finishes and no retained checkpoint needs it.

4.  **Non-predictable opt-out (escape hatch).** An Execution Calculation that genuinely requires non-reproducible or server-only randomness — for example, a roll that MUST NOT be inferable client-side, or one seeded from a source the client cannot reproduce — MUST declare itself non-predictable by setting `Predictable = false` (equivalently, carrying a `RequiresServerAuthority` marker). When such a calculation participates in an activation, that activation MUST abort prediction and fall back to awaiting server authority for the random outcome, exactly as in the prediction-window fallback of §13.8.2; the authoritative result then replicates normally. Known non-predictable dependencies MUST be checked before speculative commit. A dependency discovered later unwinds speculation using §13.8.5 and preserves the original authoritative request; it MUST NOT lose or duplicate that input.

5.  **Single-player / non-networked.** The same `context.RNG` path is used when there is no server: the stream is seeded from a local source (e.g. a per-session or per-activation seed) instead of `PredictionKey.Seed`. No `RandomFloat()`-style ambient global is permitted for gameplay-affecting rolls even offline, so that calculation behavior is identical in shape across networked and standalone play and remains reproducible for replays and tests.

`context.RNG` is a small `DeterministicRNG` interface that conforming implementations MUST provide on the Execution Calculation `context`:

``` typescript
interface DeterministicRNG {
  /** Next uniform float in [0, 1). Advances the stream by one draw. */
  NextFloat(): float;

  /**
   * Next integer in [minInclusive, maxExclusive). Rejection sampling can
   * consume multiple raw draws; all of them advance the stored cursor.
   * Bounds are signed 32-bit integers, with maxExclusive also allowing 2^31.
   * Invalid bounds fail before consuming a draw.
   */
  NextInt(minInclusive: int, maxExclusive: int): int;
}
```

<div class="note">

The seed itself is owned by the networking layer, not by the Execution Calculation: §13.8.1 defines `PredictionKey.Seed` as server-coordinated and forbids client-chosen seeds (this prevents seed substitution, not selective timing using known seeds). §9.5 only defines the *consumption* contract — how a calculation draws from that seed via `context.RNG`. A calculation MUST NOT read `PredictionKey.Seed` directly or reconstruct its own RNG; it MUST go through `context.RNG` so stream positioning stays consistent with §13.8.1.

</div>

#### 9.5.1 Deterministic RNG Profile

Predicting peers MUST agree on a versioned profile covering seed derivation, initialization, integer widths, output conversion, and execution ordering. The reference profile is `ugas-pcg32-v1` (PCG XSH-RR 64/32). An unsupported/mismatched profile disables prediction; server authority remains available. Alternative profiles require explicit agreement.

All state/seed arithmetic below wraps modulo 2^64; output arithmetic wraps modulo 2^32. Shifts are unsigned logical shifts. The server group Seed initializes state; Sub selects `increment = (Sub << 1) | 1`. Initialize state to zero, step once, add Seed modulo 2^64, and step again. Initialization’s two steps do not count as gameplay draws. Sub ranges from 0 through 65534; the reserved NONE value is not a stream selector. Encode 64-bit values as unsigned decimal strings in JSON (never lossy JSON numbers); a binary encoding uses eight little-endian bytes. Stream state consists of profile, state, increment, and raw-draw count.

``` python
MASK64 = (1 << 64) - 1
MASK32 = (1 << 32) - 1

def step(state, increment):
    old = state
    state = (old * 6364136223846793005 + increment) & MASK64
    x = (((old >> 18) ^ old) >> 27) & MASK32
    rotation = old >> 59
    word = ((x >> rotation) | (x << ((-rotation) & 31))) & MASK32
    return state, word
```

`NextFloat()` consumes one word and returns `(word >> 8) / 16777216`, exactly representable as a binary32 value in \[0, 1). `NextInt(min, max)` requires integer bounds with -2^31 ⇐ min \< max ⇐ 2^31. Compute span = max - min using at least 64 bits and threshold = 2^32 modulo span. Draw words until word \>= threshold, then return min + (word modulo span). Every rejected candidate advances the raw-draw count. Invalid bounds fail without drawing. Adapters MAY bound RNG work; exhausting that budget MUST fail/fall back, never bias a result by replacing rejection sampling with a modulo-only draw.

With Seed 42 and Sub 54, the first six raw words are `a15c02b7`, `7b47f409`, `ba1d3330`, `83d2f293`, `bfa4784b`, `cbed606e` (hexadecimal). The fixtures in `conformance/behavior/` include these words, float/integer conversion, rejected integer candidates, and checkpoint restoration. Standalone play uses the same interface with an injected local seed/cursor. Matching random draws does not guarantee matching damage if captured attributes differ; ordinary authoritative reconciliation still applies.

### 9.6 Execution Policies

Execution Policies define how multiple instances of the same Effect interact. This model replaces traditional "stacking" concepts with clearer behavioral semantics.

| Policy          | Behavior                                                                |
|-----------------|-------------------------------------------------------------------------|
| `RunInParallel` | All instances execute simultaneously; magnitude stacks N times          |
| `RunInSequence` | Instances queue; executes one after another                             |
| `RunInMerge`    | Single logical instance; durations merge (earliest start to latest end) |

#### RunInParallel

Each instance of the effect runs simultaneously, applying N times the magnitude.

``` mermaid
gantt
    accTitle: Effects running in parallel
    accDescr: Three eight-second instances start at seconds zero, two, and four. At second five, all three are active and the combined magnitude is three times the base.
    title RunInParallel — illustrative time in seconds
    dateFormat HH:mm:ss
    axisFormat %S
    tickInterval 2second
    todayMarker off
    Instance 1 : 00:00:00, 8s
    Instance 2 : 00:00:02, 8s
    Instance 3 : 00:00:04, 8s
```

Combined magnitude at t=5: 3× base

Use case: Stackable damage-over-time effects, multiple buff sources

#### RunInSequence

Instances queue and execute one after another.

``` mermaid
gantt
    accTitle: Effects running in sequence
    accDescr: Three eight-second instances execute one after another, with each starting when the preceding instance ends.
    title RunInSequence — illustrative time in seconds
    dateFormat HH:mm:ss
    axisFormat %S
    tickInterval 4second
    todayMarker off
    Instance 1 : first, 00:00:00, 8s
    Instance 2 : second, after first, 8s
    Instance 3 : after second, 8s
```

Use case: Channeled effects, crowd control chains

*Chaining mechanism:* The GC owns the queue for each `RunInSequence` effect class. When the active instance’s duration expires (or it is manually removed), the GC automatically dequeues and begins the next instance, resetting the duration timer. Ability authors do not manage this transition; applying the same effect class while one is already active is sufficient to enqueue. The `OnEffectApplied` / `OnEffectRemoved` delegates fire for each instance individually, so callers can observe the moment one stun ends and the next begins.

#### RunInMerge

Multiple applications merge into a single logical instance with combined duration.

``` mermaid
gantt
    accTitle: Effects merged into one duration
    accDescr: Three eight-second applications start at seconds zero, two, and four. The merged logical instance spans the earliest start at zero through the latest end at twelve seconds.
    title RunInMerge — illustrative time in seconds
    dateFormat HH:mm:ss
    axisFormat %S
    tickInterval 2second
    todayMarker off
    section Applications
    Instance 1 : 00:00:00, 8s
    Instance 2 : 00:00:02, 8s
    Instance 3 : 00:00:04, 8s
    section Logical instance
    Merged : 00:00:00, 12s
```

Use case: Buff refreshing, grace periods

### 9.7 Tag Grants

Effects MAY grant Tags while active:

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_effect.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_effect.json
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
   * `PredictionKey.Seed` (§13.8.1) and positioned per the activation Sub and its shared raw-draw cursor
   * (§9.5.1) so client and server agree; offline it is seeded from a local
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

``` mermaid
stateDiagram-v2
    accTitle: Ability Task lifecycle
    accDescr: A task is instantiated from Inactive to Ready, then activated. Active tasks may tick, complete when triggered, or be cancelled when the ability is cancelled or the owner dies.
    Inactive --> Ready: Instantiate
    Ready --> Active: Activate
    Active --> Active: Tick (if needed)
    Active --> Completed: Trigger / Complete
    Active --> Cancelled: Cancel
```

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

``` mermaid
flowchart TB
    accTitle: Input integration pipeline
    accDescr: Device input passes through a modifier pipeline to an action identified by InputID, then through an action set context to ability activation.
    Device[Device Input] --> Modifiers[Modifier Pipeline]
    Modifiers --> Action["Action (InputID)"]
    Action --> ActionSet["Action Set (context)"]
    ActionSet --> Ability[Ability Activation]
```

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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_effect.json
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

``` mermaid
sequenceDiagram
    accTitle: Server authority and client prediction
    accDescr: The server replicates its authoritative Gameplay Controller to the client proxy. The client predicts from local input and sends it to the server, which reconciles the client with authoritative state.
    participant Server as Server GC (Authority)
    participant Client as Client GC (Proxy)
    Server->>Client: Replicate
    Note over Client: Local input / prediction
    Client->>Server: Predicted input
    Server->>Client: Reconcile
```

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

A client MAY predict an owned GC’s ability activation when it has the replayable state, server-assigned seed, and capacity required by §13.8. Prediction is optional; submitting an otherwise valid input to authority MUST NOT depend on being able to predict it.

``` typescript
function TryActivateAbility_Predicted(handle: AbilitySpecHandle): void {
  const request = NewActivationRequest(handle); // stable attempt ID, even without prediction
  if (CanPredict(request)) {
    const before = CaptureState();             // BEFORE cost, tags, tasks, or effects
    RegisterPrediction(request, before);
    if (!TryActivateAbility_Local(handle, request.Key)) {
      RestorePredictionState(before);          // undo partial speculative work, silently
      RetireLocalSpeculation(request);
    }
  }
  SubmitOnce(request); // authority fallback also submits; retransmits reuse the same ID
}
```

`CanPredict` includes the window/capacity checks, synchronous activation requirements, replayable tasks and external inputs, and the predictability of known calculations. If a non-predictable dependency is discovered after execution starts, the client MUST unwind the affected speculation (§13.8.5), retain the same request identity, and await its authoritative result. It MUST NOT resubmit a second logical activation.

### 13.5 Server Reconciliation

Confirmation does not imply identical state: costs, targets, cooldown timing, or intervening server effects can differ. Success and failure both use the authoritative update protocol of §13.8.6. Restoring an old per-ability snapshot over current state is insufficient when predictions overlap.

``` typescript
function OnAuthoritativeUpdate(update: PredictionUpdate): void {
  if (!ValidateEpochOwnerRevisionAndOutcomes(update)) return;
  AcceptTerminalOutcomes(update);              // once; receipt is not resolution
  const suffix = FindCompleteReplaySuffix(update);
  InstallAuthoritativeState(update.State);     // includes unrelated server-originated effects
  if (suffix == null || !WithinReplayBudget(suffix)) {
    DiscardSpeculationAndPresentation();
    AwaitResynchronization();                  // never replay a truncated history
    return;
  }
  for (const frame of suffix) {
    ReplayOwningGC(frame, update.Outcomes);    // original IDs; no RPCs or duplicate cues
  }
}
```

Replay MUST exclude inputs already incorporated in the checkpoint, rejected attempts and all their dependent descendants. Applying a newer update MUST NOT erase unrelated confirmed state. Old/duplicate revisions cannot overwrite newer state. Visual blending MAY hide corrections, but cannot change the authoritative gameplay result.

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

If any check fails, the server MUST reject the application and MUST reconcile any prediction the client has already applied locally (via the standard reconciliation path in §13.5).

#### Predicted applications

When a client applies an effect locally as part of a prediction (using a `PredictionKey`), the local application is speculative only. The authoritative application — or its rejection — is determined by the server. Implementations MUST treat predicted effect applications as unconfirmed until the server acknowledges the prediction key. When the predicted effect targets a GC the predicting client does not own, the additional cross-GC rules of §13.8.4 apply.

``` typescript
// Client: speculative application
const predictionKey = GeneratePredictionKey();
const specHandle = MakeOutgoingSpec(GE_Damage, level, predictionKey);
ApplyGameplayEffectToTarget(target.GC, specHandle, predictionKey);
// For a non-owned target this creates only a presentation overlay (§13.8.4).

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
  RecordSubOutcome(predictionKey, Accepted); // publish the complete group result (§13.8.6)
}
```

#### Authoritative-only effects

Some effects MUST only ever be applied by the server (e.g., spawn effects, death effects, anti-cheat corrections). These effects SHOULD be tagged with `Gameplay.Effect.AuthoritativeOnly` and implementations MUST refuse to apply them on a client even if a prediction key is present.

### 13.8 Prediction Model (Normative)

This section defines the contract used by §13.4–§13.7 and §8.8. An adapter MUST document its finite limits, supported replay state and negotiated RNG profile. Unsupported prediction falls back to authority; it does not authorize dropping the activation request.

#### 13.8.1 PredictionKey

``` typescript
struct PredictionKey {
  ClientId: uint32;        // bound to the authenticated connection, never trusted from payload
  Epoch: uint64;           // server-issued connection generation
  OwnerGC: GCIdentity;     // stable identity, not a recycled object address
  Base: uint32;            // monotonic per connection epoch, one per independent input
  Sub: uint16;             // 0 for root; 1..65534 for dependent activations
  ParentSub: uint16;       // NONE (65535) only for root
  Seed: uint64;            // server-assigned seed for Base
}
const NONE = 65535;
```

The correlation identity is `(ClientId, Epoch, OwnerGC, Base, Sub)`. `Seed` is validated against the server’s assignment, not used to make a substituted key a new identity. The server MUST reject wrong owners/epochs, unknown parents, cycles, duplicate Sub values with different payloads, and values outside negotiated limits. Identical retransmissions MUST return the existing outcome without committing again. Renew the epoch before Base wrap; never allocate `NONE` as a Sub. An exhausted group falls back to authority without reusing keys. Retire old epochs so delayed packets cannot refer to a new activation.

Independent inputs, including two in one simulation frame, obtain distinct Base values. Same-frame activations caused by a root’s attribute/tag/event changes share its Base and Seed, allocate increasing Sub values, and record the actual parent. A later-frame activation depending on an unresolved earlier group MUST run authoritatively unless the adapter supplies an explicit, bounded causal-dependency extension; the core ParentSub field only names a parent within the same Base.

Seed derivation  
The server MUST supply seeds before prediction, either by distributing upcoming seeds or by sharing a root seed and an agreed derivation function. The server MUST validate the assigned seed and RNG profile on each request. Missing or mismatched seed/profile disables prediction. Calculations MUST consume the runtime stream specified in §9.5, never create their own stream. Knowing future seeds can permit selective input timing; server-originated seeds do not prevent this. Hidden or reward-sensitive randomness MUST use server authority.

#### 13.8.2 Prediction Window (Maximum Depth)

| Limit                 | Recommended default | Measurement                                                                            |
|-----------------------|---------------------|----------------------------------------------------------------------------------------|
| `MaxPredictionMillis` | 250 ms              | Local monotonic elapsed time since the oldest speculative frame.                       |
| `MaxPredictionFrames` | 16                  | Number of simulated steps since the confirmed checkpoint, including empty-input steps. |

Both limits MUST be finite and positive; the first reached stops speculation. At equality, the client MUST NOT advance further speculative simulation. Check limits before each step and activation, and expire speculation even when no new input arrives. A title MAY configure other limits (including for §13.6’s high latency guidance), but MUST retain finite bounds. Wall-clock adjustments and game-time pause/scale MUST NOT extend the real-time limit.

At expiry the client MUST discard speculative gameplay and presentation, restore the latest confirmed baseline, and await authoritative state. Expiry is not a server rejection or a cancellation. A delayed success may still update replicated cost/cooldown/state; it MUST NOT execute the request twice or resurrect an ended local presentation. Ordinary authority-only requests continue within finite transport/pending-request limits. If those are exhausted, report backpressure explicitly; never silently drop an accepted input or allocate indefinitely.

Adapters MUST also bound actions per frame, children per group, bytes per journal record, pending requests, and snapshot storage. Frames alone do not bound arbitrarily many actions. Limits MUST be advertised/documented; overflow uses authority or explicit backpressure. Clock-only expiry checks MUST NOT append simulation steps to replay history. An adapter that simulates multiple substeps within one frame MUST include those substeps in a finite replay-work budget; a frame limit alone does not bound them.

#### 13.8.3 CaptureState() Scope

Capture the owning GC before the first mutation of each speculative root. Child activations share that root checkpoint. A snapshot MUST be a deep copy or an equivalent immutable checkpoint/undo journal; references to mutable live state are insufficient.

| State          | Required contents                                                                                                                                                 |
|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Attributes     | Base and Current values for registered Attribute Sets.                                                                                                            |
| Effects        | Active and queued effect instances, captured magnitudes, handles, remaining duration, periodic phase/count, execution-policy state, and grant provenance (§14.3). |
| Abilities      | Grants, active/pending phases, attempt IDs, activation-owned effect handles, cooldown/charge state, and resumable task state.                                     |
| Tags           | Owned-tag counts and the effect/ability handles responsible for those counts.                                                                                     |
| Replay context | Simulation frame, input sequence, simulation time, RNG state/raw-draw cursors, and deterministic scheduler state necessary to resume the above.                   |

Reuse §14.3 effect records where their semantics match, but a prediction snapshot is a runtime checkpoint, not a §14 save file. It additionally preserves Current values and live execution state. Pending remote operations are identified by attempt ID; restoring a snapshot MUST NOT restart a remote validation or undo an authoritative cancellation/outcome.

Restoration MUST NOT reapply Instant effects, re-consume costs, send RPCs, invoke gameplay callbacks, or emit cues. Replayable task implementations MUST supply capture/restore behavior; otherwise the dependent activation is non-predictable. Replayed gameplay events needed to rebuild local state run in a replay context that suppresses external side effects and duplicate presentation. Cancellation/ended-presentation records survive rollback.

World/physics state and other GCs are excluded. Spatial query inputs/results belong in the journal (§17.7); they do not expand the GC checkpoint into a world snapshot. Snapshot cost scales with the owning GC’s state size, not just the number of activations. An adapter MAY use delta checkpoints, but MUST preserve these semantics and its declared memory bound.

#### 13.8.4 Multi-Ability and Cross-GC Prediction

A Base resolves with one complete set of terminal outcomes for its Sub keys. A parent may succeed while a child fails, but a child MUST NOT succeed if any ancestor failed. Parent rejection rejects its descendants. The client applies the complete group result atomically; this does not require reversing already committed server effects on unrelated GCs. A group with pending async validation is not terminal. Receipt acknowledgements are not confirmation. Malformed/partial outcome sets MUST trigger resynchronization, not partial reconciliation.

A client predicting an effect on a GC it does not own MAY create a presentation overlay keyed by the prediction identity. It MUST NOT mutate that target’s gameplay Attributes/Tags, run target gameplay callbacks, or use the overlay to trigger another gameplay prediction. Confirm replaces the overlay with replicated presentation; reject, local cancellation, or expiry removes it. Repeated results cannot remove or emit presentation twice. Corrections to the target GC arrive by ordinary replication, never the owner’s rollback. Effects marked `Gameplay.Effect.AuthoritativeOnly` are excluded even from speculative application (§13.7).

#### 13.8.5 Input History, Rollback Retention, and Replay Bounds

``` typescript
struct PredictedInputRecord {
  Sequence: uint64;        // monotonic input-step sequence, echoed by authority
  Frame: uint64;
  SampledAt: number;       // LOCAL monotonic milliseconds; never compared to server time
  DeltaTime: number;       // simulation seconds advanced by this step
  Actions: OrderedInput[]; // action values plus activation requests and original keys
  ExternalInputs: ReplayInputs; // recorded query inputs/results or other reproducible inputs
}
```

Keep one record per simulated step, including idle steps that advance effects/tasks. Retain a complete suffix after the restore checkpoint within BOTH window limits and the configured record/action/byte limits. Replaying MUST use the recorded DeltaTime, input order, keys, seeds, and RNG positions; allocating new identities or reading current wall-clock time changes the simulation. No RPCs, remote validation calls, or duplicate presentation may escape replay. Recheck activation requirements against the corrected state before each replayed activation. An ineligible activation and its dependent descendants MUST NOT spend resources or grant tags/cooldowns; remove their speculation while retaining the original authoritative request. Other eligible branches may still replay.

If the required suffix is absent, exceeds either limit, depends on non-replayable external state, or cannot resume its tasks, install authoritative state and await a fresh checkpoint. Do not replay a truncated suffix or invent missing steps. A locally failed/aborted prediction is unwound before later independent speculation is rebuilt; its dependent children are dropped.

The replay ring is separate from bounded unresolved-request metadata. A request may remain unresolved longer than the prediction window, but its speculative state may not. Discard expired replay data while retaining request identity until resolution or epoch retirement. Keep terminal outcomes through a contiguous resolved-input watermark; receipt of a request or resolution of a later input cannot advance past an earlier pending input. If retaining identities would exceed the finite request budget, apply backpressure/resynchronize the epoch.

Replay is owning-GC-only: it never advances physics, the world, other GCs, or external services. An adapter MUST bound total replay work by the window and per-step action limits.

#### 13.8.6 Authoritative Updates and Recovery

``` typescript
struct PredictionUpdate {
  Epoch: uint64;
  OwnerGC: GCIdentity;
  Revision: uint64;             // monotonically increasing authoritative state revision
  CheckpointFrame: uint64;
  CheckpointSequence: uint64;   // input boundary represented by State
  ResolvedThrough: uint64;      // contiguous terminal-input watermark, NOT packet receipt
  Outcomes: GroupOutcome[];     // complete per-Base sets of (Sub, ParentSub, Accepted/Rejected)
  IncludedAttempts: AttemptId[];// executions already represented in State (including later inputs)
  State: PredictionSnapshot;    // owning GC only, including server-originated changes
}
```

An adapter MUST map the checkpoint to the client’s input journal without comparing clocks. It MUST identify all incorporated attempts, including commits beyond a still-pending input, so replay never charges them again. Outcomes/identities omitted because they precede the acknowledged resolved watermark need not be repeated. A fresh checkpoint plus watermark must suffice to recover after packet loss; a delta requires its declared base revision.

Only accept a matching epoch/owner and a newer revision with valid, dependency-closed outcomes and nondecreasing watermarks. A duplicate result is idempotent; an older state cannot overwrite newer state. If an unresolved attempt predates the supplied replay boundary and cannot be reconstructed from that checkpoint, use authority recovery rather than replay it against an incompatible state. Lost results are retransmitted under the same request ID or recovered from a fresh authoritative checkpoint. Disconnect retires the epoch and clears local speculation; reconnect requires a new epoch/checkpoint before predicting. The resolved-input watermark MUST NOT exceed the highest input sequence allocated in that epoch. An invalid watermark triggers resynchronization without retiring request identities or advancing input allocation.

Example: input 10 predicts cost 10 from Mana 100, then input 11 predicts cost 20. Authority rejects input 10 and includes an unrelated Mana +5 effect in its checkpoint (Mana 105). Replaying still-eligible input 11 once yields Mana 85, not 80 or 100. If input 11 is already included, use the authoritative Mana directly without charging it again. If input 11’s child fails, discard only that child’s branch. If the checkpoint’s replay suffix is missing or the window expires, show the authoritative baseline and wait; do not keep the old speculative cost.

The portable examples under `conformance/behavior/` exercise this protocol’s bounded reference model. They do not substitute for engine-specific task/physics/transport integration tests.

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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_effect.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_effect.json
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
    // (§13.8.1) and positioned at the activation Sub's shared cursor (§9.5.1); see the
    // "Randomness in Execution Calculations" rule in §9.5. (This calculation
    // stays Predictable; a roll that must be server-only would instead set
    // Predictable = false: check before speculative commit, or unwind and
    // await the SAME authoritative request if discovered later (§13.4).)
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/attribute_set.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_effect.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/attribute_set.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_effect.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_effect.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/gameplay_effect.json
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
$schema: https://ugas.jbltx.com/v1.0.0-draft.11/schemas/attribute_set.json
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

1.  **Deterministic inputs.** A predicted query MUST run against state both ends agree on: positions in the recorded query inputs/results in the prediction journal (§13.8.5), including sampled owner and replicated target positions. World/physics positions are NOT part of the GC snapshot (§13.8.3). Replay MUST use the recorded inputs, not resample the current world. Missing/non-replayable inputs disable prediction. Where sampled positions differ across the wire the query may mispredict and MUST reconcile via §13.5 against the server’s authoritative result.

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

| Symbol               | Meaning                                                          |
|----------------------|------------------------------------------------------------------|
| $V$                  | Value (generic)                                                  |
| $V_{base}$           | Base Value of an Attribute                                       |
| $V_{current}$        | Current Value of an Attribute                                    |
| $V_{min}$, $V_{max}$ | Minimum/Maximum bounds                                           |
| $a$                  | Pre-multiply additive modifier magnitude (`Add`)                 |
| $b$                  | Post-multiply additive modifier magnitude (`AddPost`)            |
| $m$                  | Signed bonus magnitude of a `Multiply` modifier (`+0.25` = +25%) |
| $t$                  | Time variable                                                    |
| $\Delta_t$           | Time delta                                                       |
| $n$                  | Count/index variable                                             |

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

Where `{version}` is the published UGAS release the data file was authored against (e.g. `v1.0.0-draft.11`). This is the canonical, resolvable URL: it is served by the docs site, and each schema’s own `$id` is set to the same URL, so an authored file’s `$schema` both identifies and (when a network is available) resolves to the exact schema it was validated against. Each released version MUST maintain stable schema URLs — schemas at a given version MUST NOT be modified after release.

Data files SHOULD pin to the exact UGAS version they were authored against. Tooling that processes UGAS data files SHOULD validate against the schema declared in `$schema`; because the `$schema` value is a stable **identifier**, validators MAY resolve it offline (e.g. against the version’s bundled schema set) rather than over the network, and SHOULD fail clearly when the schema cannot be resolved rather than silently skipping validation.

## GameplayController Schema Definition

``` yaml
# Gameplay Controller Interface Schema Definition
# Based on UGAS Specification v1.0.0-draft.11 - Section 4

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
# Based on UGAS Specification v1.0.0-draft.11 - Appendix B

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
# Based on UGAS Specification v1.0.0-draft.11 - Appendix B

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
# Based on UGAS Specification v1.0.0-draft.11 - Appendix B

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
        exclusiveMinimum: 0
        description: "Positive server monotonic timeout in milliseconds (§8.8). When omitted the adapter MUST supply a documented finite positive default; expiry fails without commit."
      Predicted:
        type: boolean
        description: "If true, Required MUST be true. The owning client MAY predict while authority validates; inability to predict still submits the same authority request (§8.8)."
    allOf:
      - if:
          required: [Predicted]
          properties:
            Predicted:
              const: true
        then:
          required: [Required]
          properties:
            Required:
              const: true
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
# Based on UGAS Specification v1.0.0-draft.11 - Appendix B

type: object
required:
  - Name
  - DurationPolicy
allOf:
  - if:
      properties:
        DurationPolicy:
          const: HasDuration
    then:
      required:
        - Duration
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
    required:
      - Period
    properties:
      Period:
        type: number
        exclusiveMinimum: 0
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
    allOf:
      - if:
          properties:
            Shape:
              const: Sphere
        then:
          required:
            - Radius
      - if:
          properties:
            Shape:
              const: Cone
        then:
          required:
            - Radius
            - HalfAngleDeg

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
        description: Static value for ScalableFloat. A ScalableFloat needs Value, Curve, or both (§9.4.2).
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
    allOf:
      - if:
          properties:
            Type:
              const: ScalableFloat
        then:
          anyOf:
            - required:
                - Value
            - required:
                - Curve
      - if:
          properties:
            Type:
              const: AttributeBased
        then:
          required:
            - BackingAttribute
      - if:
          properties:
            Type:
              const: CustomCalculation
        then:
          required:
            - CalculatorClass
      - if:
          properties:
            Type:
              const: SetByCaller
        then:
          required:
            - DataTag

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
          Add: pre-multiply flat additive (pipeline step 2, before the multiply steps).
          Multiply: signed bonus aggregated per Channel at step 4 — the channel factor is
          (1 + sum of magnitudes), so +0.25 means +25% and -0.25 means -25%. There is no Divide
          operation: express a 50% reduction as Multiply with magnitude -0.5.
          AddPost: post-multiply flat additive (pipeline step 5, after all multiply steps; very rare).
          Override: replaces the computed result at step 6.
          Step numbers refer to the Current-Value pipeline (§5.3). On an Instant effect each
          modifier instead writes the Base Value directly in authored order, where Multiply scales
          the base by (1 + magnitude) with no channel grouping — so magnitude 0 is the identity
          (§5.2).
      Magnitude:
        $ref: "#/$defs/MagnitudeDefinition"
      Channel:
        type: string
        description: >-
          Optional named aggregation channel for Multiply modifiers. Modifiers sharing a channel
          sum their magnitudes into a single factor of (1 + sum); distinct channels produce factors
          that multiply against each other. Used for damage-bucket systems (see §5.3 Channel
          Aggregation). Omit to place the modifier in its own implicit singleton channel,
          contributing (1 + magnitude) independently of every other modifier — omission does NOT
          pool modifiers into a shared global channel. Ignored on Add, AddPost, and Override
          modifiers.
```

## Tag Schema Definition

``` yaml
# Tag Registry Schema
# Based on UGAS Specification v1.0.0-draft.11 - Appendix B

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
