---
'ugas': patch
---

[Changed] Spec §9.2 — clarify that `HasDuration` timers and periodic intervals (§9.3) advance in the runtime's *tick time*, not a built-in notion of "turn", and document the turn/phase-based authoring pattern: a card battler or tactics game advances effects by one fixed turn-step at end-of-turn (a status authored to last `N` expires after `N` turn-steps) and must NOT also advance them with per-frame time, which would age turn-scoped statuses mid-turn. The unit of a duration is whatever unit the title advances the runtime by — real-time titles pass seconds, turn-based titles pass one step per turn — so the effect model serves both without a separate "turns" concept, provided the title drives a single consistent clock. Surfaced by the real-world no-pack deck-builder harness evaluation (F1).
