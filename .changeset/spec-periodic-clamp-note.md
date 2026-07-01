---
'ugas': patch
---

[Clarified] §9.3 Periodic Execution: each periodic execution applies independently to the Base Value and is clamped on its own (§5.4), so multiple periodic (or Instant) Effects on the same clamped Attribute clamp *after each execution* — not over their net sum — making the result order-sensitive at a bound. Adds a worked regen-vs-poison example, a deterministic-ordering recommendation for reproducibility, and designer guidance (combine opposing periodics into one net-magnitude Effect, or clamp on read).
