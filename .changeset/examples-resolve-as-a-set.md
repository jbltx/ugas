---
'ugas': patch
---

[Fixed] The core examples in `schemas/examples/` now resolve as a set. Adds the `MaxHealth` and `Mana` Attributes, the Fireball's `ManaCostEffect_25` cost and `FireballCooldown_5s` cooldown Effects (§8.5), and registers every tag the examples use. A new CI check, `scripts/check_example_references.py`, fails when an example names an Attribute, Effect, Ability or tag that the set does not define.
