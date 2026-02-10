---
title: "14. Implementation Examples"
sidebar_position: 1
---

### 14.1 Basic Damage Application

#### Effect Definition

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/gameplay_effect.json
Name: "GE_BasicDamage"
DurationPolicy: Instant
Modifiers:
  - Attribute: "Health"
    Operation: Add
    Magnitude:
      Type: SetByCaller
      DataTag: "Damage.Amount"
GameplayCues:
  - "GameplayCue.Impact.Generic"
```

#### Application Flow

```typescript
function ApplyDamage(target: AbilitySystemComponent, damage: float): void {
  // 1. Create context
  const context = this.GC.MakeEffectContext();
  context.SetEffectCauser(this.Owner);

  // 2. Create spec
  const spec = this.GC.MakeOutgoingSpec(GE_BasicDamage, 1, context);

  // 3. Set damage amount
  spec.SetByCallerMagnitude("Damage.Amount", -damage);  // Negative for subtraction

  // 4. Apply to target
  const handle = this.GC.ApplyGameplayEffectToTarget(target, spec);

  // 5. Check success
  if (handle.IsValid()) {
    OnDamageApplied(target, damage);
  }
}
```

#### Attribute Change Handling

```typescript
class HealthObserver implements IAttributeChangeObserver {
  OnAttributeChanged(event: AttributeChangedEvent): void {
    const oldValue = event.OldValue;
    const newValue = event.NewValue;

    // Update health bar UI
    this.HealthBar.SetPercent(newValue / this.MaxHealth);

    // Show damage number
    const damage = oldValue - newValue;
    if (damage > 0) {
      SpawnDamageNumber(damage, event.Target.GetLocation());
    }

    // Check for death
    if (newValue <= 0) {
      OnDeath(event.CausalEffect);
    }
  }
}
```

### 14.2 Buff/Debuff with Duration

#### Temporary Modifier

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/gameplay_effect.json
Name: "GE_StrengthBuff"
DurationPolicy: HasDuration
Duration:
  Type: ScalableFloat
  Value: 30.0
ExecutionPolicy: RunInMerge  # Refresh duration on reapplication
Modifiers:
  - Attribute: "AttackPower"
    Operation: Multiply
    Magnitude:
      Type: ScalableFloat
      Value: 1.25  # +25% damage
GrantedTags:
  - "Status.Buff.Strength"
GameplayCues:
  - "GameplayCue.Status.StrengthBuff"
```

#### Visual Cue Integration

```typescript
class GC_Status_StrengthBuff extends GameplayCueLooping {
  private AuraEffect: ParticleSystem;
  private BuffIcon: UIWidget;

  OnAdd(context: CueContext): void {
    // Spawn visual aura
    this.AuraEffect = SpawnAttached(
      "PS_StrengthAura",
      context.Target,
      "Spine"
    );

    // Show buff icon in UI
    this.BuffIcon = ShowBuffIcon("Icon_Strength", context.Duration);

    // Play activation sound
    PlaySound("SFX_BuffActivate");
  }

  OnRemove(): void {
    this.AuraEffect.Destroy();
    this.BuffIcon.Remove();
    PlaySound("SFX_BuffExpire");
  }
}
```

### 14.3 Ability with Cast Time

```yaml
Ability:
  Name: "GA_Fireball"

  Tags:
    AbilityTags:
      - "Ability.Type.Spell"
      - "Ability.Element.Fire"
    ActivationOwnedTags:
      - "State.Casting"
    CancelAbilitiesWithTags:
      - "State.Stunned"
    ActivationBlockedTags:
      - "State.Silenced"

  Cost: "GE_Fireball_Cost"
  Cooldown: "GE_Fireball_Cooldown"
```

#### Task-Based Implementation

```typescript
class GA_Fireball extends GameplayAbility {
  CastTime: float = 1.5;
  ProjectileClass: ProjectileClass;

  ActivateAbility(context: AbilityContext): void {
    // 1. Commit resources
    if (!CommitAbility()) {
      EndAbility(true);
      return;
    }

    // 2. Play cast animation
    PlayAnimation("Anim_CastFireball");

    // 3. Wait for cast time
    const waitTask = WaitDelay(this.CastTime);
    waitTask.OnComplete.Subscribe(this.OnCastComplete);

    // 4. Listen for interruption
    const interruptTask = WaitTagAdded("State.Stunned");
    interruptTask.OnTagFound.Subscribe(this.OnInterrupted);
  }

  OnCastComplete(): void {
    // Spawn and launch projectile
    const projectile = SpawnProjectile(
      this.ProjectileClass,
      this.GetAvatarLocation(),
      this.GetAimDirection()
    );
    projectile.SetDamageEffect(GE_FireballDamage);

    EndAbility(false);
  }

  OnInterrupted(): void {
    // Play fizzle effect
    TriggerCue("GameplayCue.Ability.Interrupted");
    EndAbility(true);
  }
}
```

### 14.4 Complex Calculation (Armor Penetration)

```typescript
class ExecCalc_ArmorPenetration extends ExecutionCalculation {
  SourceCaptureDefinitions = [
    { Attribute: "AttackPower", CaptureTime: OnExecution },
    { Attribute: "ArmorPenetrationFlat", CaptureTime: OnExecution },
    { Attribute: "ArmorPenetrationPercent", CaptureTime: OnExecution },
    { Attribute: "CriticalChance", CaptureTime: OnExecution },
    { Attribute: "CriticalDamage", CaptureTime: OnExecution }
  ];

  TargetCaptureDefinitions = [
    { Attribute: "Armor", CaptureTime: OnExecution },
    { Attribute: "DamageReduction", CaptureTime: OnExecution }
  ];

  Execute(source, target, context): ModifierResult[] {
    // Get source stats
    const attackPower = source.Get("AttackPower");
    const armorPenFlat = source.Get("ArmorPenetrationFlat");
    const armorPenPercent = source.Get("ArmorPenetrationPercent");
    const critChance = source.Get("CriticalChance");
    const critDamage = source.Get("CriticalDamage");

    // Get target stats
    const targetArmor = target.Get("Armor");
    const damageReduction = target.Get("DamageReduction");

    // Calculate effective armor
    const armorAfterFlat = Math.max(0, targetArmor - armorPenFlat);
    const effectiveArmor = armorAfterFlat * (1 - armorPenPercent);

    // Armor damage reduction formula
    const armorDR = effectiveArmor / (effectiveArmor + 100);

    // Base damage
    let damage = attackPower * (1 - armorDR);

    // Apply critical hit
    if (RandomFloat() < critChance) {
      damage *= critDamage;
      context.SetTag("Hit.Critical");
    }

    // Apply flat damage reduction
    damage *= (1 - damageReduction);

    return [{
      Attribute: "Health",
      Operation: Add,
      Magnitude: -damage
    }];
  }
}
```

---
