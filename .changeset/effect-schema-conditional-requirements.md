---
'ugas': patch
---

[Fixed] The `gameplay_effect` schema now rejects effects that cannot execute as described. A `HasDuration` effect requires `Duration`; a `Period` requires `Period`, and it must be greater than zero; each magnitude type requires the field it reads (`ScalableFloat` → `Value`, `AttributeBased` → `BackingAttribute`, `CustomCalculation` → `CalculatorClass`, `SetByCaller` → `DataTag`); and an `Area` requires `Radius`, plus `HalfAngleDeg` for a Cone. Four new `conformance/invalid/` cases cover them.
