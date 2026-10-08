---
'ugas': patch
---

[Fixed] The `gameplay_effect` schema accepts a `ScalableFloat` magnitude that reads a `Curve` instead of a `Value`, as §9.4.2 allows. Draft.8 required `Value`, so a curve-only magnitude failed validation. A `ScalableFloat` now needs `Value`, `Curve`, or both. A new `conformance/valid/effect_scalable_float_curve.yaml` case covers it, and the invalid case now has neither field.
