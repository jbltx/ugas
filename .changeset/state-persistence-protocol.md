---
'ugas': minor
---

[Added] State Persistence protocol (§14): defines how active effect state is serialized and restored — remaining-seconds duration encoding, infinite effect provenance tracking, periodic execution mid-cycle capture, and execution policy queue serialization. Includes a full GC snapshot structure, ordered restoration protocol, and offline duration advancement guidance. Updates GC schema with `DurationPolicy`, `RemainingDuration`, `SourceAbility`, `PeriodicState`, `CapturedAttributes`, and `SetByCallerMagnitudes` fields. Closes #6.
