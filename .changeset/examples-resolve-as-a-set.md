---
'ugas': patch
---

[Fixed] The core examples in `schemas/examples/` now resolve as a set. Adds the `MaxHealth` and `Mana` Attributes, the Fireball's `ManaCostEffect_25` cost and `FireballCooldown_5s` cooldown Effects (§8.5), the OnFoot set's missing Input Actions and its `MouseSensitivity` modifier, and registers every tag the examples use, scene and input tags included. A new CI check, `scripts/check_example_references.py`, fails when an example names an Attribute, Attribute Set, Effect, Ability, Scene, Input Action, Action Set, Modifier or tag that the set does not define, across every reference field the schemas support. A scene Placement's `Controller` is not checked: UGAS defines no named controller config to resolve it against.
