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
