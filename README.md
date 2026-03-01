# Universal Gameplay Ability System (UGAS)

> An open, engine-agnostic specification for standardizing gameplay logic across game engines and AI world models.

## Overview

UGAS defines a unified architecture for implementing gameplay abilities, attributes, effects, and state management that can be deployed on platforms ranging from traditional game engines (Unreal Engine, Unity, Godot) to next-generation generative world models such as Google Genie. By decoupling gameplay logic from execution environment, UGAS enables portable, deterministic, and network-ready gameplay systems.

## Key Features

- **Four-Pillar Architecture**: Attributes (numeric state), Tags (semantic state), Abilities (behavioral logic), Effects (mutation logic)
- **Reactive, Data-Driven Design**: Event-driven state changes eliminate polling; all mutations flow through a single tracked layer
- **Dual-Value Attribute Pattern**: Base Values for permanent changes, Current Values for temporary modifiers
- **Execution Policy Model**: Clean semantics for effect interaction (Parallel, Sequence, Merge)
- **Network Replication Support**: Client-side prediction and server reconciliation built into the specification
- **Engine-Agnostic Schemas**: YAML/JSON definitions for cross-engine portability

## Documentation

| Document           | Description                              |
|--------------------|------------------------------------------|
| [SPEC.md](SPEC.md) | Full technical specification (UGAS v1.0) |

## Schema Definitions

| Schema Path                                   | Description                              |
|-----------------------------------------------|------------------------------------------|
| [schemas/gameplay_controller.yaml](schemas/gameplay_controller.yaml) | Gameplay Controller Interface Schema Definition |
| [schemas/attribute.yaml](schemas/attribute.yaml) | Attribute Schema Definition |
| [schemas/attribute_set.yaml](schemas/attribute_set.yaml) | Attribute Set Schema Definition |
| [schemas/gameplay_effect.yaml](schemas/gameplay_effect.yaml) | Gameplay Effect Schema Definition |
| [schemas/gameplay_ability.yaml](schemas/gameplay_ability.yaml) | Gameplay Ability Schema Definition |
| [schemas/gameplay_tag.yaml](schemas/gameplay_tag.yaml) | Gameplay Tag Schema Definition |

| Example Path                                   | Description                              |
|-----------------------------------------------|------------------------------------------|
| [schemas/examples/health_attribute.yaml](schemas/examples/health_attribute.yaml) | Example Attribute Definition |
| [schemas/examples/damage_effect.yaml](schemas/examples/damage_effect.yaml) | Example Gameplay Effect Definition |
| [schemas/examples/fireball_ability.yaml](schemas/examples/fireball_ability.yaml) | Example Gameplay Ability Definition |
| [schemas/examples/tag_registry.yaml](schemas/examples/tag_registry.yaml) | Example Gameplay Tag Registry Definition |

## Core Concepts

### Gameplay Controller (GC)

The central hub managing an Actor's gameplay state. The GC is the authoritative container for Attributes, Tags, Abilities, and Effects.

### Attributes

Numeric values representing quantitative state (Health, Mana, Strength). Implements the dual-value pattern:

$$V_{current} = \max\left( V_{min},\ \min\left( V_{max},\ \left( V_{base} + \sum a_i \right) \times \prod_{c \in C} \left(1 + \sum_{k \in c} m_k\right) + \sum b_l \right) \right)$$


### Gameplay Tags

Hierarchical semantic labels for state representation:

```
State.Debuff.Stunned.Magic
Ability.Type.Melee.Slash
DamageType.Physical.Blunt
```

### Gameplay Effects

The ONLY authorized mechanism for modifying attributes or tags. Three duration policies:

- **Instant**: Permanent Base Value changes
- **HasDuration**: Temporary changes with expiration
- **Infinite**: Temporary changes until explicitly removed

### Gameplay Abilities

Asynchronous, stateful action units with lifecycle: Grant -> TryActivate -> Activating (Validating) -> Commit -> Active (Executing) -> End/Cancel -> Ending

## Quick Start

1. Define your Attribute Sets in YAML
2. Define your Gameplay Effects in JSON
3. Implement the GC interface for your engine
4. Grant Abilities to Actors
5. Apply Effects through Abilities or directly via GC

See [SPEC.md](SPEC.md) Section 14 for implementation examples.

## Case Studies

The specification includes detailed case studies for:

- **Platformer** (Mario-style): Movement attributes, variable-height jump, power-up effects
- **Racing** (Forza-style): Vehicle attributes, biome-based physics, tire temperature modeling
- **ARPG** (Diablo-style): Damage buckets, combat tag queries, procedural itemization
- **Puzzle** (2048-style): Grid cell attributes, move abilities with tasks, undo via effect history

## Citation

```bibtex
@techreport{bonfill_ugas_2026,
  author = {Mickael Bonfill},
  title = {Universal Gameplay Ability System Specification},
  version = {1.0},
  year = {2026},
  month = {February},
  url = {https://github.com/jbltx/ugas}
}
```

## License

TBD

## Author

Mickael Bonfill ([@jbltx](https://github.com/jbltx))
