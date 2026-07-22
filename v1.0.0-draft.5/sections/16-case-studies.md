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
