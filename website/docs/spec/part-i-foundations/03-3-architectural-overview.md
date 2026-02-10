---
title: "3. Architectural Overview"
sidebar_position: 3
---

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
