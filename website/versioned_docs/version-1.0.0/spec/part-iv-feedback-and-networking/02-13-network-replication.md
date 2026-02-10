---
title: "13. Network Replication"
sidebar_position: 2
---

### 13.1 Replication Architecture

UGAS defines a client-server replication model where:

- The server is authoritative for all gameplay state
- Clients receive replicated state updates
- Clients may predict state changes locally
- Server reconciles predicted state with authoritative state

```
┌──────────────────┐            ┌──────────────────┐
│      SERVER      │            │      CLIENT      │
│                  │            │                  │
│  ┌────────────┐  │  Replicate │  ┌────────────┐  │
│  │    GC      │──┼───────────▶│  │    GC      │  │
│  │(Authority) │  │            │  │  (Proxy)   │  │
│  └────────────┘  │            │  └────────────┘  │
│                  │            │                  │
│                  │  Predict   │                  │
│                  │◀───────────┼──(Local Input)   │
│                  │            │                  │
│                  │ Reconcile  │                  │
│                  │───────────▶│                  │
└──────────────────┘            └──────────────────┘
```

### 13.2 Replication Modes

| Mode | Effects | Cues | Tags | Attributes | Use Case |
|------|---------|------|------|------------|----------|
| `Minimal` | None | All | All | None | AI entities, distant actors |
| `Mixed` | Owner only | All | All | Owner only | Player characters |
| `Full` | All | All | All | All | Single-player, debugging |

**Minimal Mode**
: Only Cue triggers and Tag changes are replicated. Effects and Attributes are server-only. Suitable for AI entities where clients don't need full state.

**Mixed Mode**
: Full replication to the owning client; minimal replication to others. The standard mode for player characters in multiplayer games.

**Full Mode**
: Complete replication to all clients. Used for single-player games or debugging. Higher bandwidth cost.

### 13.3 Bandwidth Optimization

#### Delta Compression

Only changed values are transmitted:

```typescript
struct ReplicatedAttributeSet {
  /** Bitmask of changed attributes since last update */
  DirtyMask: uint32;

  /** Only changed attribute values */
  ChangedValues: float[];
}
```

#### Dirty Bit Tracking

Attributes track their dirty state:

```typescript
function SetBaseValue(attribute: Attribute, newValue: float): void {
  if (attribute.BaseValue !== newValue) {
    attribute.BaseValue = newValue;
    attribute.bIsDirty = true;
    this.DirtyAttributes.add(attribute);
  }
}
```

#### Quantization

For bandwidth-critical scenarios, attribute values MAY be quantized:

```typescript
struct QuantizedHealth {
  /** 0-255 representing 0-100% health */
  HealthPercent: uint8;
}
```

### 13.4 Client-Side Prediction

To eliminate network latency perception, clients predict ability outcomes locally:

```typescript
function TryActivateAbility_Predicted(handle: AbilitySpecHandle): void {
  // Generate prediction key
  const predictionKey = GeneratePredictionKey();

  // Predict locally
  const success = TryActivateAbility_Local(handle, predictionKey);

  if (success) {
    // Store predicted state
    this.PredictedActivations.set(predictionKey, {
      Handle: handle,
      Timestamp: GetCurrentTime(),
      State: CaptureState()
    });

    // Send to server
    Server_TryActivateAbility(handle, predictionKey);
  }
}
```

### 13.5 Server Reconciliation

When server response differs from prediction:

```typescript
function OnServerActivationResponse(
  predictionKey: PredictionKey,
  serverSuccess: boolean,
  serverState: GameplayState
): void {
  const prediction = this.PredictedActivations.get(predictionKey);

  if (!prediction) return;

  if (!serverSuccess) {
    // Prediction was wrong - rollback
    RollbackToState(prediction.State);
  } else {
    // Prediction was correct - reconcile minor differences
    ReconcileState(serverState);
  }

  this.PredictedActivations.delete(predictionKey);
}
```

#### Rollback and Replay

For significant discrepancies:

1. Revert to last known authoritative state
2. Re-apply all inputs that occurred since that state
3. Blend visually to avoid jarring corrections

```typescript
function RollbackAndReplay(
  authoritativeState: GameplayState,
  inputHistory: Input[]
): void {
  // 1. Revert state
  ApplyState(authoritativeState);

  // 2. Replay inputs
  for (const input of inputHistory) {
    if (input.Timestamp > authoritativeState.Timestamp) {
      SimulateInput(input);
    }
  }

  // 3. Blend if needed
  if (VisualDiscrepancy > Threshold) {
    StartVisualBlend(currentVisual, newSimulatedState);
  }
}
```

### 13.6 Replication Frequency Recommendations

| Actor Type | Update Rate | Notes |
|------------|-------------|-------|
| Player Character | 60-100 Hz | High frequency for responsive feel |
| Important AI | 30-60 Hz | Moderate frequency |
| Distant Actors | 10-20 Hz | Lower frequency acceptable |
| Static Objects | On Change | Event-based only |

---
