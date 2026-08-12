# Complete Schema Reference

## Schema URL Versioning Policy

All `$schema` URLs in UGAS data files use the pattern:

    https://ugas.jbltx.com/{version}/schemas/{schema-name}.json

Where `{version}` is the published UGAS release the data file was authored against (e.g. `v1.0.0-draft.6`). This is the canonical, resolvable URL: it is served by the docs site, and each schema’s own `$id` is set to the same URL, so an authored file’s `$schema` both identifies and (when a network is available) resolves to the exact schema it was validated against. Each released version MUST maintain stable schema URLs — schemas at a given version MUST NOT be modified after release.

Data files SHOULD pin to the exact UGAS version they were authored against. Tooling that processes UGAS data files SHOULD validate against the schema declared in `$schema`; because the `$schema` value is a stable **identifier**, validators MAY resolve it offline (e.g. against the version’s bundled schema set) rather than over the network, and SHOULD fail clearly when the schema cannot be resolved rather than silently skipping validation.

## GameplayController Schema Definition

``` yaml
# Gameplay Controller Interface Schema Definition
# Based on UGAS Specification v1.0.0-draft.6 - Section 4

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
# Based on UGAS Specification v1.0.0-draft.6 - Appendix B

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
# Based on UGAS Specification v1.0.0-draft.6 - Appendix B

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
# Based on UGAS Specification v1.0.0-draft.6 - Appendix B

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
# Based on UGAS Specification v1.0.0-draft.6 - Appendix B

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
# Based on UGAS Specification v1.0.0-draft.6 - Appendix B

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
