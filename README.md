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
| [SPEC.adoc](SPEC.adoc) | Full technical specification             |
| [genres/](genres/README.md) | Genre packs: per-genre additional specs + ready-to-use templates |
| [docs/CONSUMING.md](docs/CONSUMING.md) | Consuming UGAS programmatically: manifests, pre-chunked spec, offline schema bundle, and the vendoring playbook |

## Using the npm package

Each spec release is published to npm as [`@ugas/spec`](https://www.npmjs.com/package/@ugas/spec)
once the owner approves it, at the same version (`@ugas/spec@1.0.0-draft.7` is UGAS `v1.0.0-draft.7`). Drafts go out under the
`next` dist-tag.

```sh
npm install @ugas/spec@next
```

```ts
import { VERSION, SCHEMA_IDS, schemas, bundle, files, checkReferences } from '@ugas/spec';
import type { GameplayEffect, EntityByType } from '@ugas/spec';

VERSION;                          // '1.0.0-draft.7'
SCHEMA_IDS.gameplay_effect;       // 'https://ugas.jbltx.com/v1.0.0-draft.7/schemas/gameplay_effect.json'
files({ kind: 'spec-section' });  // [{ path: 'sections/05-attributes.md', sha256, ... }, ...]
checkReferences([{ path: 'damage.yaml', entity }]); // [{ path, message }] for each dangling reference
```

- The files are the ones the site publishes, at the same relative paths: `schemas/`
  (with `bundle.json`), `sections/`, `genres/`, `conformance/`, `rag/` and the `index.json`
  manifest. Import them by subpath, e.g. `@ugas/spec/schemas/bundle.json`.
- The TypeScript types are generated from the JSON schemas, one per entity type.
- `checkReferences` is a port of [`scripts/check_example_references.py`](scripts/check_example_references.py);
  a parity test runs both on the examples, the genre packs and the Python fixtures.

The package lives in [`packages/spec/`](packages/spec/README.md); [RELEASING.md](RELEASING.md)
covers how it is published.

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
| [schemas/examples/max_health_attribute.yaml](schemas/examples/max_health_attribute.yaml) | Example Attribute used as a clamping bound |
| [schemas/examples/mana_attribute.yaml](schemas/examples/mana_attribute.yaml) | Example Attribute with static bounds |
| [schemas/examples/damage_effect.yaml](schemas/examples/damage_effect.yaml) | Example Gameplay Effect Definition |
| [schemas/examples/mana_cost_effect.yaml](schemas/examples/mana_cost_effect.yaml) | Example ability Cost Effect |
| [schemas/examples/fireball_cooldown_effect.yaml](schemas/examples/fireball_cooldown_effect.yaml) | Example ability Cooldown Effect |
| [schemas/examples/fireball_ability.yaml](schemas/examples/fireball_ability.yaml) | Example Gameplay Ability Definition |
| [schemas/examples/tag_registry.yaml](schemas/examples/tag_registry.yaml) | Example Gameplay Tag Registry Definition |
| [schemas/examples/onfoot_actions.yaml](schemas/examples/onfoot_actions.yaml) | Example Input Actions for the OnFoot set |
| [schemas/examples/mouse_sensitivity_modifier.yaml](schemas/examples/mouse_sensitivity_modifier.yaml) | Example Input Modifier |

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

See [SPEC.adoc](SPEC.adoc) Section 14 for implementation examples.

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
  version = {1.0.0-draft.8},
  year = {2026},
  month = {February},
  url = {https://github.com/jbltx/ugas}
}
```

## Trademarks

UGAS is an independent project. It is not affiliated with, sponsored by, or endorsed by any
company or product named in this repository. Unreal Engine, Unity, Godot, Genie, and the game
titles cited as genre examples are trademarks or registered trademarks of their respective
owners. They are named only to describe engine targets and to point at well-known gameplay
patterns.

## License

MIT

## Author

Mickael Bonfill ([@jbltx](https://github.com/jbltx))
