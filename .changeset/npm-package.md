---
'ugas': minor
---

[Added] UGAS is published to npm as `@ugas/spec`, at the spec version, on every GitHub release (drafts under the `next` dist-tag). The package ships the same files as `ugas.jbltx.com/v<version>/` at the same paths (schemas with `bundle.json`, spec sections, genre packs, conformance corpus, RAG artifacts, `index.json`), and exports `VERSION`, `SCHEMA_IDS`, the schemas and bundle, a `files()` listing over the manifest, TypeScript types generated from the schemas, and `checkReferences`, a JavaScript port of `scripts/check_example_references.py` that a parity test holds to the Python checker.
