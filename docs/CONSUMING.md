# Consuming UGAS programmatically

This guide is for building UGAS into another project — an engine, IDE, web app, or an AI
assistant that scaffolds games. UGAS publishes **static, checksummed artifacts** you vendor at
build time; no runtime dependency on our uptime, and everything works offline (browser, CI,
air-gapped).

Everything below lives under `https://ugas.jbltx.com/<version>/` (the canonical host). Pin a
`<version>` such as `v1.0.0-draft.4`; discover versions from
[`versions.json`](https://ugas.jbltx.com/versions.json) (`latest` alias + per-version status
and changelog).

## The artifacts

| Artifact | What it is |
|----------|------------|
| `index.json` | **Start here.** Manifest of every resource at this version: `id`, `kind`, `path`, `url`, `mediaType`, `bytes`, `sha256`. |
| `sections/index.json` + `sections/<NN>-<slug>.md` | The spec pre-chunked into individually-fetchable sections with stable ids (`effects`, `attributes`, …). Load one section instead of the whole spec. |
| `SPEC.md` | The whole spec in one Markdown file (if you'd rather not chunk). |
| `genres/index.json` | Every genre pack: `scope`, `signatureMechanic`, `specPath`, and its `entities[]` (`id`, `type`, `path`). |
| `genres/<pack>/entities/*.yaml` | Copy-and-extend template entities for a genre. |
| `schemas/<type>.json` / `.yaml` | Per-type JSON Schemas (Draft-07). |
| `schemas/bundle.json` | All schemas in one self-contained document; validate any entity **offline** against it. |
| `schemas/manifest/*.schema.json` | Meta-schemas for the manifests above, so you can validate what you vendor. |
| `conformance/valid/` + `conformance/invalid/` | Labelled corpus to test your loader/validator against. |
| `rag/chunks.jsonl` + `rag/llms-index.json` | Finer retrieval chunks + an author-intent → chunk-id map for RAG/intent routing. |
| `llms.txt` / `llms-full.txt` | Human/agent index and a single-fetch everything file (at the docs root, not versioned). |

## Playbook

1. **Pin a version** and fetch its `index.json`. That manifest tells you every resource and
   its checksum — you never have to scrape.
2. **Vendor a snapshot** of what you need — the spec sections, the JSON schemas (or just
   `bundle.json`), and the genre pack(s) for your target genres — into your own resource tree.
   Prefer vendoring over runtime fetch if you run in a browser, in CI, or offline.
3. **Expose the resources behind an on-demand read tool**, addressed by section/pack id, so
   your agent lazy-loads one section at a time instead of the whole spec.
4. **Write a thin "router"**: a topic → resource-id index (start from `rag/llms-index.json`),
   the four-pillar completeness checklist, and — if you realize into an engine — your
   engine-specific realization mapping. Keep it short; the spec content lives in the loaded
   resources, not the prompt.
5. **Delegate single-entity authoring/validation** to a focused role that owns the schemas,
   and **validate every emitted entity** against the schema named by its `$schema` (resolve it
   offline against `bundle.json`) before use.
6. **Keep authoring separate from realization.** Author engine-agnostic UGAS data first; map it
   to your engine (objects, scripts, calculation seams) as a distinct step, and name the engine
   seams (`ExecCalc_*`) explicitly so they're implementable.
7. **Refresh via manifest diff.** On a new UGAS version, diff `index.json` (compare `sha256`s)
   to see exactly what changed and re-vendor only those pieces.

## Validating an entity offline

Every authored entity carries a `$schema` id like
`https://ugas.jbltx.com/<version>/schemas/<type>.json`. That value is a stable *identifier*;
you do not need to fetch it. Load `schemas/bundle.json` once and validate against it — the
bundle dispatches on the entity's `$schema` and resolves all internal `$ref`s with no network:

```python
import json, yaml
from jsonschema import Draft7Validator

bundle = json.load(open("bundle.json"))
validator = Draft7Validator(bundle)          # internal #/$defs refs resolve in-document
entity = yaml.safe_load(open("my_effect.yaml"))
errors = list(validator.iter_errors(entity))  # [] == valid
```

Run the shipped `conformance/` corpus through the same code to confirm your validator agrees:
every `valid/` entity should pass and every `invalid/` entity should fail.

## Authoring skills

The `gameplay-creator-assistant` and `ugas-schema-author` skills (installable from this repo)
author UGAS data from natural-language intent. Their I/O is pluggable — a **fetch adapter**
(network / bundled resource / local checkout) and an **output adapter** (write files / return
data / hand to an engine step) — so a browser or no-egress agent can reuse the authoring logic
by pointing the fetch adapter at vendored artifacts. They resolve the target version at runtime
from `versions.json` rather than hard-coding it, and stamp the canonical `ugas.jbltx.com`
`$schema` on everything they emit.

> The `unity-tools` skill in this repo is a Unity-Editor bridge, not part of the consumer
> packaging; its packaging/distribution is tracked separately.
