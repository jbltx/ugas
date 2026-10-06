---
'ugas': patch
---

[Fixed] Every genre pack, and the `_template` skeleton, now resolves as a standalone entity set. The packs referenced 145 tags, cost and cooldown Effects, and Input Actions they did not ship. Each pack's tag registry now declares every tag its entities use, and the cost and cooldown Effects its abilities name now ship as files in `entities/`. CI runs `check_example_references.py` on each pack, and the npm package's parity test now also requires every pack to resolve. The pack guide gains a matching "Entities must resolve as a set" rule.
