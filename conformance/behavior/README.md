# Behavioral conformance

These fixtures exercise the normative prediction (§13.8), deterministic RNG (§9.5.1), and
asynchronous activation (§8.8) contracts. `format.schema.json` defines version 1. Every
fixture has an ID, a model, optional initial settings, and ordered steps. A step invokes an
operation with `args`; `expect` compares the named observation fields recursively (including
array order and JSON type). Booleans are distinct from numbers at every nesting level;
equivalent JSON numbers such as `1` and `1.0` compare equal, and object key order is irrelevant.
Omitted observation fields are unconstrained. `error` expects a specific
validation/budget error; absent `error` requires success. Unknown operations, arguments,
fixture versions, duplicate IDs, and non-finite numbers are rejected.

Run from a source checkout with Python and `jsonschema` installed:

```sh
python scripts/run_behavior_conformance.py
python scripts/test_behavior_conformance.py
python scripts/run_behavior_conformance.py --corpus packages/spec/build/conformance/behavior
```

The reference models in `scripts/behavior_model.py` are a small executable interpretation
of the observable contracts, not an engine runtime. Fixtures contain fixed expectations;
the runner never writes or regenerates them. The Seed 42/Sub 54 raw RNG vector is the
PCG reference sequence; the Sub 55 vector was cross-checked with independent JavaScript
BigInt arithmetic. Integer rejection and float expectations use those fixed raw words.

## Adapter mapping

An engine adapter runs every fixture operation in order and records a JSON object after
each step, including `error: null` on success. Export the observations as
`{fixture_id: [observation_after_step_1, ...]}` and verify them with:

```sh
python scripts/run_behavior_conformance.py --results adapter-results.json
```

The result set must contain exactly the corpus's IDs, with an observation array containing
one object per step. Null results are invalid and never select reference execution.
Map error codes to the fixture's strings at the adapter boundary. Additional observation
fields are allowed. A missing field that the fixture checks is a failure.

- **rng:** Initialize PCG32 with decimal-string `seed` and integer `sub` (defaults 42/54).
  `next` appends a raw unsigned word, float, or bounded integer to `output`. `save`/`restore`
  checkpoint only generator state/cursor, not the observation log. `draws` counts raw words,
  including rejected integer candidates, excluding initialization steps. `state` and
  `increment` are unsigned decimal strings. Calls represent successive calculations sharing
  a stream; replay restores its saved cursor. The reference work budget is 128 raw words per
  integer call, failing instead of producing a biased fallback value.
- **async:** Initial Mana defaults to 100; the finite timeout default is 5000 ms. `start`
  registers a unique attempt ID on a named single-instance ability (`Spell` by default),
  with cost 10 unless overridden. `resolve`, `cancel`, `advance`, and `change` represent
  serialized GC mutations. `advance` uses monotonic milliseconds; `fire_timers: false`
  tests delayed timer dispatch. `change` can alter grant validity, blocking, available Mana,
  or inject a commit failure. Cooldowns persist after active cancellation. Observations
  expose pending/active IDs, terminal outcomes, commit IDs, tags, cooldowns, Mana, and trace.
  The model bounds retained request identities to 64 unless overridden; production adapters
  retire them using their transport epoch/watermark protocol.
- **prediction:** A single owner/epoch starts at Mana 100. A `submit` is a root input Base
  with an ordered list of dependent Sub nodes; each node charges an activation cost and
  grants a cooldown/tag labelled `Base:Sub`. A node's optional target creates presentation
  only; it is a recorded query result, never a mutation of a second GC. `predictable: false`
  represents any failed eligibility check (seed/profile, external input, task, or calculation).
  `late_nonpredictable` and `local_failure` exercise partial-work rollback. Trace `send:N`
  means one logical request; network retransmissions reuse the same identity.
  Prediction and replay recheck each node's affordability and parent eligibility. An
  ineligible node and its descendants are removed from speculative replay, while eligible
  siblings survive; the original server request retains all its nodes until authority
  resolves it. Later checkpoints do not revive branches dropped from the journal.
  `advance` advances monotonic time/frame and optionally distinct simulation milliseconds;
  empty-input simulation steps are retained. With `frames: 0` it only advances the monotonic
  clock and checks expiry: it does not tick gameplay, append a timer record, or reset action
  capacity. `simulation_ms` must then be absent or zero; a positive value fails before any
  mutation. Each advancing call records at most one timer action in a new frame, bounding
  each frame to `max_actions` activation nodes plus one timer action. An optional periodic Mana effect retains
  elapsed simulation time and tick count across replay. `update` supplies authoritative
  state and complete Sub outcomes; it does not simulate the server. In this single-stream
  model, Base also identifies input sequence; `included` identifies wholly incorporated
  groups. `checkpoint_frame` excludes already-incorporated timer steps. `resolved_through`
  is a terminal watermark, while `receipt` is only receipt. `complete_history: false`
  forces recovery. `cancel` retires local presentation; only the server decides the outcome.
  Dedicated cases exercise inclusion before terminal outcomes arrive and a nonzero
  checkpoint that retains later timer steps before a subsequent checkpoint retires them.
  Mutation regressions verify that ignoring inclusion, replaying incorporated ticks, or
  dropping the later timer suffix fails those cases.
  Watermarks beyond the allocated inputs are invalid and force resynchronization without
  retiring requests. Cancelled-presentation records are freed once their request identities
  pass the contiguous resolution watermark and leave the replay journal.
  `reconnect` clears speculation and retires the old epoch. Observe final gameplay state,
  overlays, pending groups, journal group IDs, frame count, readiness, revision and trace.

Production adapters also need tests for their actual task capture/restore, multi-owner
routing, per-byte snapshot limits, spatial inputs, later-frame dependencies, transport
recovery, and external-service transactions. These compact protocol vectors do not claim
to test those engine integrations. Cases are discovered by manifest kind
`behavioral-conformance`; schema-validity cases remain under `conformance/valid` and
`conformance/invalid` and use kind `conformance`.
