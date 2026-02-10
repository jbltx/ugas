---
title: "15. Case Studies"
sidebar_position: 2
---

### 15.1 Platformer (Mario-style)

#### Movement Attributes

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/attribute_set.json
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

```typescript
class GA_Jump extends GameplayAbility {
  ActivateAbility(context: AbilityContext): void {
    // Check grounded OR coyote time
    if (!this.Owner.Tags.MatchesTag("State.Grounded") &&
        !this.Owner.Tags.MatchesTag("Status.CoyoteTime")) {
      EndAbility(true);
      return;
    }

    // Apply jump impulse
    this.Owner.Tags.AddTag("State.InAir");
    this.Owner.Tags.RemoveTag("State.Grounded");

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
    // Short press = cut jump short
    if (this.Owner.GetAttribute("VerticalVelocity") > 0) {
      // Apply gravity multiplier for shorter jump
      const cutSpec = MakeOutgoingSpec(GE_JumpCut, 1);
      ApplyGameplayEffectToSelf(cutSpec);
    }
  }

  OnLanded(): void {
    this.Owner.Tags.RemoveTag("State.InAir");
    this.Owner.Tags.AddTag("State.Grounded");
    EndAbility(false);
  }
}
```

#### Power-Up Effects

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/gameplay_effect.json
Name: "GE_SuperMushroom"
DurationPolicy: Infinite
GrantedTags:
  - "State.PowerUp.Super"
Modifiers:
  - Attribute: "Scale"
    Operation: Multiply
    Magnitude:
      Type: ScalableFloat
      Value: 2.0
  - Attribute: "Health"
    Operation: Add
    Magnitude:
      Type: ScalableFloat
      Value: 1.0  # Gain 1 hit point
GameplayCues:
  - "GameplayCue.PowerUp.Super"
```

### 15.2 Racing (Forza-style)

#### Vehicle Attribute Sets

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/attribute_set.json
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

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/gameplay_effect.json
Name: "GE_Biome_Mud"
DurationPolicy: Infinite
ApplicationRequiredTags:
  - "Vehicle"
Modifiers:
  - Attribute: "TireGripMultiplier"
    Operation: Multiply
    Magnitude:
      Type: ScalableFloat
      Value: 0.4
  - Attribute: "MaxSpeed"
    Operation: Add
    Magnitude:
      Type: ScalableFloat
      Value: -30.0  # Reduce top speed
GrantedTags:
  - "Surface.Mud"
---
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/gameplay_effect.json
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

```typescript
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

### 15.3 ARPG (Diablo-style)

#### Damage Bucket Architecture

The "Damage Bucket" system prevents linear power creep by organizing modifiers into multiplicative groups.

```typescript
class ExecCalc_ARPGDamage extends ExecutionCalculation {
  Execute(source, target, context): ModifierResult[] {
    // Bucket A: Main Stat (additive within bucket)
    const mainStatBonus = source.Get("Strength") * 0.01;  // +1% per point

    // Bucket B: Additive Damage Bonuses
    let bucketB = 1.0;
    bucketB += source.Get("DamageBonus_Fire") || 0;
    bucketB += source.Get("DamageBonus_Elite") || 0;
    bucketB += source.Get("DamageBonus_WhileHealthy") || 0;

    // Bucket C: Multiplicative Powers
    let bucketC = 1.0;
    bucketC *= source.Get("LegendaryPowerMultiplier") || 1.0;
    bucketC *= source.Get("SetBonusMultiplier") || 1.0;

    // Vulnerability check
    let vulnerabilityMultiplier = 1.0;
    if (target.Tags.MatchesTag("Status.Vulnerable")) {
      vulnerabilityMultiplier = 1.2;
    }

    // Final calculation: Buckets multiply each other
    const baseDamage = source.Get("WeaponDamage");
    const finalDamage = baseDamage *
                        (1 + mainStatBonus) *  // Bucket A
                        bucketB *               // Bucket B
                        bucketC *               // Bucket C
                        vulnerabilityMultiplier;

    return [{
      Attribute: "Health",
      Operation: Add,
      Magnitude: -finalDamage
    }];
  }
}
```

#### Combat Tag Queries

```typescript
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

```typescript
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

### 15.4 Puzzle (2048-style)

#### Grid Cell Attributes

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/attribute_set.json
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

```typescript
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

      // Mark source for destruction
      merge.SourceCell.Tags.AddTag("Status.PendingDestroy");
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

#### Undo via Effect History

```typescript
class UndoSystem {
  private EffectHistory: HistoryFrame[] = [];

  RecordFrame(): void {
    const frame: HistoryFrame = {
      Timestamp: GetCurrentTime(),
      CellStates: [],
      AppliedEffects: []
    };

    // Capture all cell states
    for (const cell of GetAllCells()) {
      frame.CellStates.push({
        ID: cell.ID,
        Value: cell.GetAttribute("CellValue"),
        X: cell.GetAttribute("GridX"),
        Y: cell.GetAttribute("GridY")
      });
    }

    this.EffectHistory.push(frame);
  }

  Undo(): void {
    if (this.EffectHistory.length < 2) return;

    // Remove current frame
    this.EffectHistory.pop();

    // Get previous frame
    const previousFrame = this.EffectHistory[this.EffectHistory.length - 1];

    // Restore cell states
    for (const cellState of previousFrame.CellStates) {
      const cell = GetCellByID(cellState.ID);
      if (cell) {
        const restoreSpec = MakeOutgoingSpec(GE_RestoreState, 1);
        restoreSpec.SetByCallerMagnitude("Value", cellState.Value);
        restoreSpec.SetByCallerMagnitude("X", cellState.X);
        restoreSpec.SetByCallerMagnitude("Y", cellState.Y);
        ApplyGameplayEffectToTarget(cell.GC, restoreSpec);
      }
    }
  }
}
```

---
