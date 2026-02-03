# Universal Gameplay Attribute System (UGAS)

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

| Document | Description |
|----------|-------------|
| [SPEC.md](SPEC.md) | Full technical specification (UGAS v1.0) |

## Core Concepts

### Ability System Component (ASC)

The central hub managing an Actor's gameplay state. The ASC is the authoritative container for Attributes, Tags, Abilities, and Effects.

### Attributes

Numeric values representing quantitative state (Health, Mana, Strength). Implements the dual-value pattern:

```
CurrentValue = (BaseValue + Additions) x (1 + AdditivePercent) x Multiplicatives
```

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

Asynchronous, stateful action units with lifecycle: Grant -> TryActivate -> Commit -> Execute -> End/Cancel

## Quick Start

1. Define your Attribute Sets in YAML
2. Define your Gameplay Effects in JSON
3. Implement the ASC interface for your engine
4. Grant Abilities to Actors
5. Apply Effects through Abilities or directly via ASC

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
  title = {Universal Gameplay Attribute System Specification},
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
