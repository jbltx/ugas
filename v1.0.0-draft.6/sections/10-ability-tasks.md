## 10. Ability Tasks

### 10.1 Purpose and Design

Ability Tasks are specialized asynchronous nodes that pause ability execution until a specific trigger condition is met. Tasks enable complex, multi-stage abilities to be written in a linear, readable fashion while executing asynchronously across frames or network ticks.

Tasks leverage the Observer design pattern for efficiency. Instead of polling a condition every frame, the ability registers a task and goes dormant. When the trigger condition is met, the task "wakes up" the ability and execution continues.

### 10.2 Task Lifecycle

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

*Instantiation*: Task is created with configuration parameters *Activation*: Task registers with relevant systems (timers, events, physics) *Tick* (optional): Some tasks require per-frame updates (see §10.6) *Completion*: Trigger condition met; ability execution resumes *Cancellation*: Task is aborted (ability cancelled, owner died)

### 10.3 Predefined Task Categories

| Category    | Trigger            | Example Tasks                        |
|-------------|--------------------|--------------------------------------|
| Temporal    | Timer expiry       | WaitDelay, WaitGameTime              |
| Event-Based | Gameplay event     | WaitGameplayEvent, WaitTagChanged    |
| Input-Based | Input state change | WaitInputRelease, WaitInputPressed   |
| State-Based | Tag change         | WaitTagAdded, WaitTagRemoved         |
| Spatial     | Collision/overlap  | WaitOverlap, WaitForTarget           |
| Animation   | Montage notify     | WaitAnimationEvent, WaitMontageEnded |

#### WaitDelay

Waits for a specified duration.

``` typescript
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

``` typescript
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

``` typescript
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

``` typescript
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

1.  Extend the base AbilityTask class

2.  Implement OnActivate() for setup

3.  Implement cleanup in OnEndTask()

4.  Provide delegate/event outputs for ability continuation

5.  Handle cancellation gracefully

``` typescript
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

1.  All active Tasks are cancelled

2.  Task event subscriptions are cleared

3.  Task resources are released

``` typescript
function EndAbility(wasCancelled: boolean): void {
  // Cancel all active tasks
  for (const task of this.ActiveTasks) {
    task.Cancel();
  }
  this.ActiveTasks.Clear();

  // Remove activation-owned tags by removing the Effect that granted them.
  // This is the normal (non-cancelled) end path; CancelAbility handles the cancel path.
  const spec = GC.GetAbilitySpec(this.Handle);
  if (spec?.ActiveOwnedTagsHandle) {
    GC.RemoveActiveGameplayEffect(spec.ActiveOwnedTagsHandle);
    spec.ActiveOwnedTagsHandle = undefined;
  }

  // Continue with ability end logic...
}
```

### 10.6 Tick Budgeting and Performance

Most tasks are event-driven and impose no per-frame cost: as described in §10.1, an ability registers a task, goes dormant, and is woken only when the trigger fires. A subset of tasks, however, cannot be expressed as a single subscription and require periodic re-evaluation. The clearest example is the *Spatial* category (§10.3): `WaitOverlap` and `WaitForTarget` poll physics queries to detect overlaps or acquire targets.

Ticking tasks scale multiplicatively with both ability complexity and actor count. An ability running five concurrent spatial tasks across 100 simultaneous actors performs 500 physics queries per frame. Without throttling, prioritisation, or visibility into per-task cost, this class of task becomes the dominant performance hazard of the system on large-scale titles, while remaining negligible on small ones.

This section defines RECOMMENDED mechanisms for bounding that cost. The base `AbilityTask` SHOULD expose the controls described below, and the runtime SHOULD honour them when scheduling task ticks. Event-, state-, and input-driven tasks are never ticked and are unaffected.

#### Per-Task Tick Throttling

A ticking task SHOULD support a configurable tick interval rather than ticking every frame. Implementations SHOULD expose a `TickInterval` on the base task, expressed in seconds, where `0` means "tick every frame". When `TickInterval > 0`, the runtime MUST NOT tick the task more frequently than the interval; it SHOULD accumulate elapsed time and evaluate once per elapsed interval.

``` typescript
abstract class AbilityTask {
  // Seconds between Tick() evaluations. 0 = every frame (default).
  TickInterval: float = 0;
  // Higher values tick first when the per-frame budget is exhausted. Default 0.
  Priority: int = 0;

  private accumulated: float = 0;

  // Called by the runtime each frame for tasks that require ticking.
  InternalTick(deltaTime: float): void {
    if (this.TickInterval <= 0) {
      this.Tick(deltaTime);
      return;
    }
    this.accumulated += deltaTime;
    if (this.accumulated >= this.TickInterval) {
      this.Tick(this.accumulated);  // pass real elapsed time, not the nominal interval
      this.accumulated = 0;
    }
  }

  protected abstract Tick(deltaTime: float): void;
}
```

Throttling trades responsiveness for cost. The interval SHOULD be chosen per task according to how quickly the observed condition changes and how tolerant the gameplay is to latency:

| Category                    | Recommended Interval | Rationale                                                                       |
|-----------------------------|----------------------|---------------------------------------------------------------------------------|
| Spatial (gameplay-critical) | Every frame (0)      | Hit detection and targeting where a missed frame is player-visible              |
| Spatial (ambient / AOE)     | 50-100 ms            | Lingering area effects and aura acquisition; sub-frame precision is unnecessary |
| Temporal                    | Every frame (0)      | Driven by the timer subsystem; cost is already O(1) per task                    |
| Animation                   | Every frame (0)      | Must align with notify windows; no polling cost beyond the montage system       |
| Event / State / Input       | n/a (no tick)        | Observer-driven; never ticked (see §10.1)                                       |

#### Task Tick Budget and Priority

Throttling bounds the cost of an individual task but not the aggregate cost across many actors. Implementations SHOULD additionally support a *per-frame tick budget*: an upper bound on the number of task ticks, or on accumulated tick time, that the runtime executes in a single frame.

When the budget is exhausted in a given frame, the runtime SHOULD defer the remaining ticking tasks to a subsequent frame rather than exceeding the budget. Tasks SHOULD declare a `Priority`; when deferring, the runtime SHOULD tick higher-priority tasks first and SHOULD avoid starving any task indefinitely (for example, by ageing deferred tasks toward a higher effective priority). Gameplay-critical tasks, such as player hit detection and targeting, SHOULD be assigned a higher priority than ambient ones.

`TickInterval` and `Priority` are conventional, optional parameters applicable to any task; they appear on the Ability schema’s task entries (see Appendix B, Ability Schema Definition).

#### Profiling Hooks

To make expensive tasks identifiable in production, implementations SHOULD expose profiling hooks around task ticking. At minimum, the runtime SHOULD make the following available per task type:

- Number of active instances

- Aggregate and per-instance tick time

- Effective tick frequency (after throttling)

These metrics SHOULD be surfaced through the host engine’s profiler or an equivalent instrumentation channel, so that integrators can attribute frame cost to specific task types and tune `TickInterval`, `Priority`, and the per-frame budget accordingly.
