---
'ugas': patch
---

[Fixed] `schemas/bundle.json` now rejects an entity with a missing or unknown `$schema`. Its `if`/`then` dispatch had no fallback, so such a document matched no clause and passed. Two new `conformance/invalid/bundle_*` cases cover it.
