---
'ugas': patch
---

[Changed] Spec §5.2 — define how an Instant effect applies each modifier operation to the Base Value, resolving the previously-undefined Instant × `Multiply` case. An Instant `Multiply` scales the Base Value by `(1 + magnitude)` (the §5.3 signed-bonus convention: `+1.0` doubles, `-0.25` removes 25%), then clamps to the attribute's bounds. The per-operation rules are stated as *total* — an implementation MUST NOT silently drop any operation. A durational (Infinite/HasDuration) effect's `Multiply` modifiers remain Current-Value modifiers and are never written to the Base Value, including on the periodic ticks of a periodic durational effect (which apply only `Add`/`AddPost`/`Override` to base). Surfaced by the real-world RPG harness evaluation, where an Instant `Multiply` was a silent no-op.
