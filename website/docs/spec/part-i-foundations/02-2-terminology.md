---
title: "2. Terminology"
sidebar_position: 2
---

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
