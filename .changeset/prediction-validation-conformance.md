---
'ugas': minor
---

[Fixed] Make prediction snapshots precede mutation, reconcile complete group outcomes against authoritative checkpoints, retain later eligible inputs and server effects, and bound replay/request storage separately. Define expiry, idempotent recovery, and cross-GC presentation isolation; align spatial-query replay with the GC-only snapshot scope.

[Added] Define the `ugas-pcg32-v1` deterministic RNG profile, shared activation cursors, checkpoint restoration, and unbiased integer sampling. A missing or non-predictable dependency uses the same authoritative activation request instead of dropping or duplicating input.

[Fixed] Identify asynchronous validation by activation attempt, serialize cancellation/timeout/commit, recheck mutable requirements, and preserve the winner of races. Explicit `TimeoutMs` values must now be positive, and `Predicted: true` requires `Required: true`; omitted settings remain supported with a documented finite adapter timeout default.

[Added] Publish versioned behavioral conformance fixtures separately from entity-schema fixtures, with a Python reference runner, external adapter-result verification, package discovery, and CI coverage. Adapters must agree on RNG profiles and treat atomic group reconciliation as applying one complete dependency-consistent outcome set, not an all-or-nothing server transaction.

[Fixed] Reject null adapter observations instead of running the reference model. Recheck affordability and parent eligibility during prediction/replay, retire cancelled-presentation records with resolved requests, and reject future resolution watermarks before they can discard subsequent inputs. Add regression scenarios and repeated-retirement checks for these cases.
