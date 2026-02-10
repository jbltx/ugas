---
title: "8. Gameplay Abilities"
sidebar_position: 5
---

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
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/gameplay_effect.json
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
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/gameplay_effect.json
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
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/gameplay_effect.json
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
