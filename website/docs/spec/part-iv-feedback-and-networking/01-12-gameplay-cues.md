---
title: "12. Gameplay Cues"
sidebar_position: 1
---

### 12.1 Design Philosophy

Gameplay Cues enforce strict separation between Mechanics and Aesthetics. This separation provides:

- **Server Optimization**: Headless servers load no visual/audio resources
- **Client Customization**: Visual settings don't affect gameplay
- **Network Efficiency**: Cues are not replicated; only trigger tags are
- **Platform Adaptation**: Different platforms can have different cue implementations

### 12.2 Cue Trigger Mechanism

Cues are triggered by Tags following the `GameplayCue.*` convention:

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/gameplay_effect.json
Name: "GE_FireDamage"
DurationPolicy: Instant
Modifiers:
  - Attribute: "Health"
    Operation: Add
    Magnitude:
      Type: ScalableFloat
      Value: -25.0
GameplayCues:
  - "GameplayCue.Impact.Fire"
```

When the Effect is applied:
1. Server applies the Effect and modifies attributes
2. `GameplayCue.Impact.Fire` tag is communicated to clients
3. Clients' Cue Managers instantiate the fire impact VFX/SFX

### 12.3 Cue Types

**Burst Cues** (Fire-and-Forget)
: Triggered once, play to completion, clean themselves up.

```typescript
class GC_Impact_Fire extends GameplayCueBurst {
  OnExecute(context: CueContext): void {
    SpawnParticleSystem("PS_FireImpact", context.HitLocation);
    PlaySound("SFX_FireImpact", context.HitLocation);
  }
}
```

**Looping Cues** (Duration-Bound)
: Persist while the triggering Effect is active.

```typescript
class GC_Status_Burning extends GameplayCueLooping {
  private ParticleComponent: ParticleSystem;

  OnAdd(context: CueContext): void {
    this.ParticleComponent = SpawnLoopingParticle("PS_BurningLoop", context.Target);
    StartLoopingSound("SFX_BurningLoop", context.Target);
  }

  OnRemove(): void {
    this.ParticleComponent.Destroy();
    StopLoopingSound("SFX_BurningLoop");
  }
}
```

### 12.4 Cue Manager

The Cue Manager is a client-side system responsible for:

1. Receiving cue trigger notifications
2. Matching tags to Cue implementations
3. Instantiating and managing Cue resources
4. Pooling frequently-used Cues for performance

```typescript
class GameplayCueManager {
  private CueRegistry: Map<Tag, GameplayCueClass>;
  private ActiveLoopingCues: Map<ActiveEffectHandle, GameplayCue[]>;

  HandleCueNotify(tag: Tag, context: CueContext, type: CueNotifyType): void {
    const cueClass = this.CueRegistry.get(tag);
    if (!cueClass) return;

    switch (type) {
      case Execute:
        const burstCue = this.InstantiateCue(cueClass);
        burstCue.OnExecute(context);
        break;

      case Add:
        const loopingCue = this.InstantiateCue(cueClass);
        loopingCue.OnAdd(context);
        this.ActiveLoopingCues.get(context.EffectHandle).push(loopingCue);
        break;

      case Remove:
        const activeCues = this.ActiveLoopingCues.get(context.EffectHandle);
        for (const cue of activeCues) {
          cue.OnRemove();
        }
        this.ActiveLoopingCues.delete(context.EffectHandle);
        break;
    }
  }
}
```

### 12.5 Server Optimization

On headless servers:

1. Cue Manager is NOT instantiated
2. Cue assets are NOT loaded
3. Cue trigger tags are still processed for replication
4. Memory footprint is significantly reduced

Implementations SHOULD support a headless mode flag:

```typescript
if (!IsHeadlessServer()) {
  this.CueManager = new GameplayCueManager();
  this.CueManager.LoadCueAssets();
}
```

---
