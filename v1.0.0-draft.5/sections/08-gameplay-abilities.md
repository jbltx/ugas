## 8. Gameplay Abilities

### 8.1 Ability Definition

A Gameplay Ability is a self-contained unit of logic defining an action an Actor can perform. Unlike simple function calls, Abilities are asynchronous, stateful objects with defined lifecycles.

#### Ability Class Structure

``` typescript
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

  /**
   * Tags applied to the owner while this ability is active.
   * Implementations MUST apply these as an auto-generated Infinite GameplayEffect
   * on CommitAbility and remove that effect on EndAbility/CancelAbility.
   * Direct tag mutation is prohibited (see §3.1).
   */
  ActivationOwnedTags: TagContainer;

  /** Cost effect applied on commit */
  CostEffect?: GameplayEffectClass;

  /** Cooldown effect applied on commit */
  CooldownEffect?: GameplayEffectClass;

  /** Called when ability is activated */
  abstract ActivateAbility(context: AbilityContext): void;

  /** Called when ability ends */
  abstract EndAbility(wasCancelled: boolean): void;
}
```

#### AbilitySpec (Instance Data)

``` typescript
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

  /**
   * Handle to the auto-generated Infinite Effect that grants ActivationOwnedTags.
   * Set by CommitAbility; cleared by EndAbility/CancelAbility.
   * Undefined when the ability is not active.
   */
  ActiveOwnedTagsHandle?: ActiveEffectHandle;
}
```

### 8.2 Lifecycle State Machine

The base lifecycle assumes the `Activating (Validating)` checks of §8.3 are synchronous: an ability that passes them proceeds straight to Commit (§8.4). Some activations, however, require **asynchronous** server-side validation (anti-cheat, remote inventory, entitlement/auth) whose result is not known synchronously. The `PendingConfirmation` state models that unresolved authoritative outcome; its full normative treatment, including the client-side prediction path, is in §8.8.

`PendingConfirmation` sits between `Activating (Validating)` and `Commit`. Synchronous-only abilities skip it and go `Validating → Commit` exactly as before; abilities that require asynchronous validation (§8.8) route through it. Under client-side prediction (§13.8) the predicting client may instead **speculatively** enter Active while the authoritative side holds the activation in `PendingConfirmation` until the server confirms or rejects the prediction key — the reject edge rolls the speculative activation back to `Granted` via §13.5.

                        ┌──────────────┐
                        │  NotGranted  │
                        └──────┬───────┘
                               │ Grant
                               ▼
                        ┌──────────────┐
            ┌──────────▶│   Granted    │◀────────────────┐
            │           │  (Inactive)  │◀──────────┐     │
            │           └──────┬───────┘           │     │
            │                  │ TryActivate       │     │
            │                  ▼                   │     │
            │           ┌──────────────┐           │     │
            │           │  Activating  │───────────┤     │
            │           │ (Validating) │  Fail     │     │
            │           └──┬────────┬──┘           │     │
            │   sync-only  │        │ requires      │     │
            │  (§8.3 pass) │        │ async         │     │
            │              │        ▼ validation    │     │
            │              │ ┌────────────────────┐ │     │
            │              │ │ PendingConfirmation │─┘     │
            │              │ │  (awaiting server   │ Fail  │
            │              │ │     validation)     │ (async│
            │              │ └─────────┬───────────┘ reject)│
            │              │           │ Confirm            │
            │              │           │ (async success)    │
            │              ▼           ▼                    │
            │           ┌──────────────────┐                │
            │           │      Commit      │ ───────────────┘
            │           │ (cost/cooldown)  │  RejectPrediction
            │           └────────┬─────────┘  -> rollback (§13.5)
            │                    │ proceed
            │                    ▼
            │           ┌──────────────────┐
            │           │      Active      │   Client prediction (§13.8):
            │           │   (Executing)    │   client enters Active SPECULATIVELY
            │           │                  │   while server stays in
            │           └────────┬─────────┘   PendingConfirmation until the
            │                    │ End/Cancel   prediction key resolves.
            │                    ▼              ConfirmPrediction -> no change;
            │           ┌──────────────────┐    RejectPrediction -> rollback to
            └───────────│      Ending      │    Granted via §13.5.
                        └──────────────────┘

### 8.3 Activation Requirements

Before an Ability can activate, the following checks MUST pass:

1.  *Granted Check*: Ability must be granted to the GC

2.  *Not Already Active*: Ability must not currently be active (unless configured for multiple instances)

3.  *Required Tags*: Owner must have all tags in `ActivationRequiredTags`

4.  *Blocked Tags*: Owner must NOT have any tags in `ActivationBlockedTags`

5.  *Cost Verification*: If CostEffect is defined, owner must have sufficient resources

6.  *Cooldown Verification*: Cooldown tag must not be present

``` typescript
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

1.  Cost Effect is applied (resources consumed)

2.  Cooldown Effect is applied (cooldown tag granted)

3.  Activation Owned Tags are granted

4.  Ability proceeds to execution

``` typescript
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

  // Grant activation tags via an auto-generated Infinite Effect.
  // Direct tag mutation is prohibited (§3.1); all tag state flows through Effects.
  if (!spec.AbilityClass.ActivationOwnedTags.IsEmpty()) {
    const ownedTagsSpec = MakeOwnedTagsEffect(spec.AbilityClass.ActivationOwnedTags, spec.Level);
    spec.ActiveOwnedTagsHandle = ApplyGameplayEffectToSelf(ownedTagsSpec);
  }

  return true;
}
```

### 8.5 Costs and Cooldowns as Effects

Costs and Cooldowns are NOT separate variables but are implemented as specialized Gameplay Effects.

#### Cost Effect Pattern

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
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

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
Name: "GE_Fireball_Cooldown"
DurationPolicy: HasDuration
Duration:
  Type: ScalableFloat
  Value: 5.0  # 5 second cooldown
GrantedTags:
  - "Cooldown.Ability.Fireball"
```

This pattern enables external modification of costs and cooldowns. For example, a "Mana Efficiency" buff could apply a multiplier to all cost effects:

``` yaml
$schema: https://ugas.jbltx.com/v1.0.0-draft.5/schemas/gameplay_effect.json
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
      Value: -0.25  # -25% mana cost
```

### 8.6 Cancellation and Interruption

Abilities may be cancelled by:

1.  *Self-Cancellation*: Ability logic calls EndAbility(true)

2.  *External Cancel*: Another system calls CancelAbility on the GC

3.  *Cancel Tags*: An Effect grants a tag in the Ability’s `CancelAbilitiesWithTags` set

4.  *Owner Death*: Owner’s Health reaches zero

``` typescript
function CancelAbility(handle: AbilitySpecHandle): void {
  const spec = GetAbilitySpec(handle);
  if (!spec.IsActive) return;

  // Remove activation tags by removing the Effect that granted them.
  // Direct tag mutation is prohibited (§3.1).
  if (spec.ActiveOwnedTagsHandle) {
    RemoveActiveGameplayEffect(spec.ActiveOwnedTagsHandle);
    spec.ActiveOwnedTagsHandle = undefined;
  }

  // Call ability's end handler
  spec.AbilityInstance.EndAbility(true /* wasCancelled */);

  // Cleanup active tasks
  CancelAllAbilityTasks(handle);

  spec.IsActive = false;
}
```

### 8.7 Schema Definition

``` yaml
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

  AsyncValidation:                # Optional: async server validation (§8.8)
    Required: boolean             # If true, route through PendingConfirmation
    Kind: string                  # AntiCheat | RemoteInventory | Entitlement | Custom
    TimeoutMs: number             # Max wait before treating as async failure
    Predicted: boolean            # If true, client may speculatively Activate (§13.8)

  Tasks:                          # Sequential task definitions
    - Type: string                # Task type name
      Params: object              # Task-specific parameters

  Metadata:
    DisplayName: string
    Description: string
    Icon: string
```

### 8.8 Asynchronous Validation and Predicted Activation

The lifecycle of §8.2 assumes the §8.3 activation checks are synchronous. Some activations require **asynchronous** server-side validation whose result is not available in the activating frame — for example server-side anti-cheat confirmation, a resource check against a remote inventory service, or multi-step authentication for a premium consumable. Under the client-side prediction this specification mandates (§13.4–§13.8), the client predicts success synchronously and goes Active, but the server MAY reject the activation after its asynchronous validation resolves. Without a modeled state for the unresolved authoritative outcome, that late rejection has no defined transition — the race condition this section resolves.

This section introduces an explicit lifecycle state, `PendingConfirmation`, for an activation that has passed the synchronous §8.3 checks but whose authoritative outcome is not yet known. It is additive to §8.2–§8.7 and MUST NOT contradict them, and it builds on the networking model of §13.5, §13.7, and §13.8 without modifying it. Where this section uses MUST/SHOULD/MAY it carries the same RFC-2119 force as the rest of this specification.

#### 8.8.1 The PendingConfirmation State

`PendingConfirmation` denotes an activation that has passed the synchronous §8.3 checks but whose authoritative result is still outstanding pending asynchronous validation. While an activation is in `PendingConfirmation`:

1.  It MUST NOT have committed (§8.4). Cost and Cooldown Effects MUST NOT have been applied, and `ActivationOwnedTags` MUST NOT have been granted, on the side that is awaiting confirmation. Commit is reached only on confirmation.

2.  It MUST NOT be executing ability Tasks that produce authoritative gameplay mutations. An implementation MAY run non-authoritative presentation work (e.g. a wind-up animation or a local-visual cue) while pending, consistent with the speculative/local-visual rule of §13.7 and §13.8.4.

3.  `spec.IsActive` MUST be `false` on the authoritative side while pending; the ability is not yet Active in the §8.2 sense. (Under prediction, the predicting client MAY report a **speculative** Active locally — see §8.8.4.)

An ability is eligible for `PendingConfirmation` only when it is marked as requiring asynchronous validation. The OPTIONAL `AsyncValidation` block of the §8.7 schema is the normative marker: when `AsyncValidation.Required` is `true`, an activation that passes the §8.3 checks MUST enter `PendingConfirmation` before Commit rather than committing synchronously. When the marker is absent or `Required` is `false`, the ability retains the synchronous §8.2 behaviour (`Validating → Commit`) unchanged. An implementation MAY represent the marker by other means, but the resulting semantics MUST match this section.

#### 8.8.2 Transition Table

The following transitions are added to §8.2. All other §8.2 transitions are unchanged.

| From                    | To                   | Trigger / Condition                                                                                                                                                                                                                      |
|-------------------------|----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Activating (Validating) | Commit               | Synchronous §8.3 checks pass AND the ability does NOT require async validation (`AsyncValidation.Required` is absent/false). Unchanged from §8.2.                                                                                        |
| Activating (Validating) | PendingConfirmation  | Synchronous §8.3 checks pass AND the ability requires async validation (`AsyncValidation.Required == true`). No cost/cooldown consumed yet.                                                                                              |
| Activating (Validating) | Granted (via Fail)   | A synchronous §8.3 check fails. Unchanged from §8.2.                                                                                                                                                                                     |
| PendingConfirmation     | Commit → Active      | Asynchronous validation succeeds (server authority), or `ConfirmPrediction(key)` is received (§13.7) for a predicted activation. Cost/Cooldown/`ActivationOwnedTags` are applied at Commit (§8.4).                                       |
| PendingConfirmation     | Granted (via Fail)   | Asynchronous validation fails, `AsyncValidation.TimeoutMs` elapses, or `RejectPrediction(key)` is received (§13.7). No cost/cooldown was consumed. For a predicted speculative Active, the client MUST roll back via §13.5 (see §8.8.4). |
| PendingConfirmation     | Granted (via Cancel) | The activation is cancelled or interrupted while pending (§8.6, §8.8.5).                                                                                                                                                                 |

A `PendingConfirmation` activation has, by construction, not consumed cost or cooldown; therefore both the Fail and Cancel exits from `PendingConfirmation` return the ability to `Granted` with no resources spent and no cooldown started.

#### 8.8.3 Path A — Server-Authoritative Async Validation (No Prediction)

This is the pure server-authoritative flow (prediction disabled, or `AsyncValidation.Predicted` not set). After the synchronous §8.3 checks pass, an ability requiring async validation enters `PendingConfirmation` **before** Commit. The server initiates the asynchronous validation (anti-cheat, remote inventory, entitlement/auth). The activation remains pending — no cost, no cooldown, not executing — until the validation resolves:

- On asynchronous **success**, the activation proceeds to Commit (§8.4) and then to Active (§8.2). This is the only point at which cost and cooldown are consumed.

- On asynchronous **failure** (including a `TimeoutMs` expiry), the activation transitions to Fail and back to `Granted`. Because Commit was never reached, no cost or cooldown was consumed and `ActivationOwnedTags` were never granted; no rollback of authoritative gameplay state is required.

``` typescript
// Server-authoritative async validation (no client prediction).
function TryActivateAbility_ServerAsync(spec: AbilitySpec): void {
  // 1. Synchronous §8.3 checks first.
  if (!CanActivateAbility(spec)) {
    Fail(spec); // -> Granted (§8.2)
    return;
  }

  // 2. Synchronous-only ability: commit immediately (unchanged §8.2 path).
  if (!spec.AbilityClass.AsyncValidation?.Required) {
    CommitAbility(spec); // §8.4
    ActivateAbility(spec);
    return;
  }

  // 3. Async ability: enter PendingConfirmation BEFORE commit.
  //    No cost/cooldown consumed; ability is not yet Active.
  spec.State = AbilityState.PendingConfirmation;
  spec.IsActive = false;

  BeginAsyncValidation(spec, spec.AbilityClass.AsyncValidation, (result) => {
    if (spec.State !== AbilityState.PendingConfirmation) {
      return; // Cancelled/interrupted while pending (§8.8.5) — ignore late result.
    }
    if (result.ok) {
      CommitAbility(spec);   // §8.4 — cost/cooldown applied HERE, not before.
      ActivateAbility(spec); // -> Active
    } else {
      Fail(spec);            // -> Granted; nothing was consumed.
    }
  });
}
```

While an activation is pending under Path A, an implementation MUST define how concurrent input and cancellation are treated; the RECOMMENDED behaviour is in §8.8.5.

#### 8.8.4 Path B — Client-Side Prediction

This is the flow when prediction is enabled for the ability (`AsyncValidation.Predicted == true`) and the activation is predicted by the owning client per §13.8. It resolves the race directly: the authoritative side now has a modeled `PendingConfirmation` state to occupy while the client is speculatively Active, so a late server rejection has the defined `RejectPrediction → rollback → Granted` transition rather than an undefined one.

1.  **Client (speculative).** The client runs the synchronous §8.3 checks locally and, if they pass, **predictively commits and enters Active (speculative)**, carrying a `PredictionKey` generated per §13.8.1. Before predicting it MUST capture rollback state via `CaptureState()` (§13.8.3) and it MUST respect the bounded prediction window of §13.8.2. The speculative Active MUST be treated as unconfirmed (§13.7); any effect it applies to a non-owned GC is speculative/local-visual only (§13.8.4).

2.  **Server (authoritative).** The server receives the predicted activation, runs the synchronous checks, and holds the activation in `PendingConfirmation` while its asynchronous validation runs. The server does NOT mirror the client’s speculative Active; it commits only when validation succeeds.

3.  **Confirmation.** On asynchronous success the server emits `ConfirmPrediction(key)` (§13.7). The client’s speculative Active is confirmed with no visible change — the predicted commit becomes authoritative. The server itself transitions `PendingConfirmation → Commit → Active`.

4.  **Rejection.** On asynchronous failure (or `TimeoutMs`) the server emits `RejectPrediction(key)` (§13.7). The client MUST roll back the speculative activation via the §13.5 reconciliation path, restoring the `CaptureState()` snapshot of §13.8.3 (which includes ability activation state, so the speculatively-consumed cost/cooldown and granted `ActivationOwnedTags` are reverted), and the ability returns to `Granted`. The authoritative server side, which only ever held `PendingConfirmation`, transitions to Fail → `Granted` without ever having committed.

``` typescript
// Client: predict, then reconcile on the server's confirm/reject.
function TryActivateAbility_Predicted_Async(handle: AbilitySpecHandle): void {
  const spec = GetAbilitySpec(handle);
  if (!CanActivateAbility(spec)) return;       // local synchronous §8.3 checks

  // Window guard (§13.8.2) — do not predict past the bounded window.
  if (!PredictionWindowAllowsNewActivation()) return;

  const key = GeneratePredictionKey();         // §13.8.1
  this.PredictedActivations.set(key, {
    Handle: handle,
    Timestamp: GetCurrentTime(),
    State: CaptureState()                       // §13.8.3 — owning GC only
  });

  // Predictive commit + speculative Active (unconfirmed, §13.7).
  CommitAbility(spec);
  ActivateAbility(spec);                        // speculative Active

  Server_TryActivateAbility(handle, key);       // server holds PendingConfirmation
}

// Client: server outcome of the predicted (async-validated) activation.
function OnServerActivationResponse_Async(key: PredictionKey, ok: boolean): void {
  const prediction = this.PredictedActivations.get(key);
  if (!prediction) return;

  if (!ok) {
    // RejectPrediction: roll back speculative activation via §13.5,
    // restoring the §13.8.3 snapshot. Ability returns to Granted.
    RollbackToState(prediction.State);
  }
  // ConfirmPrediction: no visible change; predicted commit was correct.
  this.PredictedActivations.delete(key);
}
```

Because a predicted activation participates in the prediction model, it is bound by the same group and key rules: if it is part of a multi-ability prediction group it is confirmed or rejected atomically with that `PredictionKey.Base` (§13.8.4), so a chained activation predicted off this one is never left confirmed while this one is rolled back.

#### 8.8.5 Interaction with Cancellation, Interruption, and the Prediction Window

**Cancellation while pending (§8.6).** A `PendingConfirmation` activation MAY be cancelled or interrupted by any of the §8.6 mechanisms (self-cancel, external `CancelAbility`, a cancel tag, or owner death) before its asynchronous validation resolves. On such a cancel the ability MUST leave `PendingConfirmation` and return to `Granted`. Because nothing was committed, the §8.6 teardown is reduced: there are no committed cost/cooldown effects to reverse and no `ActiveOwnedTagsHandle` to remove (it is set only at Commit, §8.4). An implementation MUST NOT consume cost or cooldown as a side effect of cancelling a pending activation.

**In-flight async validation.** When a pending activation is cancelled, an implementation SHOULD attempt to abort the in-flight asynchronous validation, but MUST tolerate a validation result that arrives after the cancel. A late result for an activation that is no longer in `PendingConfirmation` MUST be discarded (it MUST NOT retroactively commit, re-activate, or consume resources). For the predicted Path B, a cancel before resolution MUST still roll back the speculative activation via §13.5 if the server subsequently rejects, and a late `ConfirmPrediction` for an already-cancelled key MUST NOT resurrect the activation.

**Prediction window bound (§13.8.2).** A speculative Active awaiting confirmation is server-unconfirmed predicted state and therefore counts against the bounded prediction window of §13.8.2. A client MUST NOT remain speculatively Active past that window while awaiting confirmation: if the window bound (`MaxPredictionMillis` / `MaxPredictionFrames`) is reached before `ConfirmPrediction`/`RejectPrediction` arrives, the client MUST fall back to awaiting server authority per §13.8.2 — surrendering the speculative outcome and applying authoritative state on the next update — rather than holding the unconfirmed activation indefinitely. An asynchronous validation whose expected latency exceeds the prediction window SHOULD be modelled as server-authoritative (Path A, `Predicted == false`) so the user is not shown a speculative outcome that routinely exceeds the window and rolls back.
