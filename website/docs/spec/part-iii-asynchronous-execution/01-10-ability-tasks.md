---
title: "10. Ability Tasks"
sidebar_position: 1
---

### 10.1 Purpose and Design

Ability Tasks are specialized asynchronous nodes that pause ability execution until a specific trigger condition is met. Tasks enable complex, multi-stage abilities to be written in a linear, readable fashion while executing asynchronously across frames or network ticks.

Tasks leverage the Observer design pattern for efficiency. Instead of polling a condition every frame, the ability registers a task and goes dormant. When the trigger condition is met, the task "wakes up" the ability and execution continues.

### 10.2 Task Lifecycle

```
         ┌─────────────┐
         │  Inactive   │
         └──────┬──────┘
                │ Instantiate
                ▼
         ┌─────────────┐
         │   Ready     │
         └──────┬──────┘
                │ Activate
                ▼
         ┌─────────────┐     Tick (if needed)
    ┌───▶│   Active    │◀────────────────┐
    │    └──────┬──────┘                 │
    │           │                        │
    │           ├────────────────────────┘
    │           │ Trigger/Complete
    │           ▼
    │    ┌─────────────┐
    │    │  Completed  │
    │    └─────────────┘
    │
    │    ┌─────────────┐
    └────│  Cancelled  │
         └─────────────┘
```

**Instantiation**: Task is created with configuration parameters
**Activation**: Task registers with relevant systems (timers, events, physics)
**Tick** (optional): Some tasks require per-frame updates
**Completion**: Trigger condition met; ability execution resumes
**Cancellation**: Task is aborted (ability cancelled, owner died)

### 10.3 Predefined Task Categories

| Category | Trigger | Example Tasks |
|----------|---------|---------------|
| Temporal | Timer expiry | WaitDelay, WaitGameTime |
| Event-Based | Gameplay event | WaitGameplayEvent, WaitTagChanged |
| Input-Based | Input state change | WaitInputRelease, WaitInputPressed |
| State-Based | Tag change | WaitTagAdded, WaitTagRemoved |
| Spatial | Collision/overlap | WaitOverlap, WaitForTarget |
| Animation | Montage notify | WaitAnimationEvent, WaitMontageEnded |

#### WaitDelay

Waits for a specified duration.

```typescript
class WaitDelay extends AbilityTask {
  Duration: float;

  OnActivate(): void {
    this.StartTimer(this.Duration);
  }

  OnTimerComplete(): void {
    this.Completed.Broadcast();
    this.EndTask();
  }
}
```

#### WaitGameplayEvent

Waits for a gameplay event with a matching tag.

```typescript
class WaitGameplayEvent extends AbilityTask {
  EventTag: Tag;
  OnlyTriggerOnce: boolean;

  OnActivate(): void {
    this.Owner.OnGameplayEvent.Subscribe(this.EventTag, this.OnEvent);
  }

  OnEvent(payload: GameplayEventData): void {
    this.EventReceived.Broadcast(payload);
    if (this.OnlyTriggerOnce) {
      this.EndTask();
    }
  }
}
```

#### WaitInputRelease

Waits for an input action to be released.

```typescript
class WaitInputRelease extends AbilityTask {
  InputID: InputID;

  OnActivate(): void {
    this.InputSystem.OnInputReleased.Subscribe(this.InputID, this.OnRelease);
  }

  OnRelease(heldDuration: float): void {
    this.Released.Broadcast(heldDuration);
    this.EndTask();
  }
}
```

#### WaitTagAdded

Waits for a specific tag to be added to the owner.

```typescript
class WaitTagAdded extends AbilityTask {
  WaitTag: Tag;

  OnActivate(): void {
    if (this.Owner.Tags.MatchesTag(this.WaitTag)) {
      this.TagFound.Broadcast();
      this.EndTask();
      return;
    }
    this.Owner.OnTagChanged.Subscribe(this.OnTagChanged);
  }

  OnTagChanged(tag: Tag, added: boolean): void {
    if (added && this.WaitTag.Matches(tag)) {
      this.TagFound.Broadcast();
      this.EndTask();
    }
  }
}
```

### 10.4 Custom Task Implementation

Custom tasks MUST:

1. Extend the base AbilityTask class
2. Implement OnActivate() for setup
3. Implement cleanup in OnEndTask()
4. Provide delegate/event outputs for ability continuation
5. Handle cancellation gracefully

```typescript
class WaitForHealthThreshold extends AbilityTask {
  Threshold: float;
  Comparison: ComparisonType;  // LessThan | LessEqual | Greater | GreaterEqual

  OnActivate(): void {
    // Check immediately
    if (this.CheckThreshold()) {
      this.ThresholdReached.Broadcast();
      this.EndTask();
      return;
    }

    // Subscribe to attribute changes
    this.Owner.OnAttributeChanged.Subscribe("Health", this.OnHealthChanged);
  }

  OnHealthChanged(event: AttributeChangedEvent): void {
    if (this.CheckThreshold()) {
      this.ThresholdReached.Broadcast();
      this.EndTask();
    }
  }

  CheckThreshold(): boolean {
    const health = this.Owner.GetAttributeValue("Health");
    switch (this.Comparison) {
      case LessThan: return health < this.Threshold;
      case LessEqual: return health <= this.Threshold;
      case Greater: return health > this.Threshold;
      case GreaterEqual: return health >= this.Threshold;
    }
  }

  OnEndTask(): void {
    this.Owner.OnAttributeChanged.Unsubscribe("Health", this.OnHealthChanged);
  }
}
```

### 10.5 Task Ownership and Cleanup

Tasks are owned by the Ability that created them. When an Ability ends:

1. All active Tasks are cancelled
2. Task event subscriptions are cleared
3. Task resources are released

```typescript
function EndAbility(wGCancelled: boolean): void {
  // Cancel all active tasks
  for (const task of this.ActiveTasks) {
    task.Cancel();
  }
  this.ActiveTasks.Clear();

  // Continue with ability end logic...
}
```

---
