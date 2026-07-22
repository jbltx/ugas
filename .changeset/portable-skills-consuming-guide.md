---
'ugas': minor
---

[Added] Consumer playbook and portable authoring skills (P2 of the Unity Studio integration feedback):

- **`docs/CONSUMING.md`** — how to consume UGAS programmatically: the artifact map (manifest, pre-chunked sections, genre index, offline schema bundle, conformance corpus, RAG index), a 7-step vendoring playbook, an offline-validation snippet, and the manifest-diff refresh flow. Linked from the README.
- [Changed] `gameplay-creator-assistant` no longer hard-pins `v1.0.0-draft.1`: it **resolves the target version at runtime** from `versions.json` (`latest`, or a user pin). Adds a **bundled-resource fetch adapter** (for browser/no-egress consumers) alongside network and local-checkout, an **output adapter** concept, and a first-class **"author engine-agnostic data vs realize in an engine"** section. Fetch guidance is now manifest-driven (`index.json`, `sections/`, `genres/index.json`, `schemas/bundle.json`).
- [Changed] Both skills stamp the canonical `https://ugas.jbltx.com/<version>/schemas/<type>.json` on emitted entities (was `raw.githubusercontent.com`), and document that the `%%UGAS_VERSION%%` placeholder is repo-only — consumer output must carry a concrete resolved version, never the placeholder.
