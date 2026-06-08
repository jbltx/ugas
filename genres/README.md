# UGAS Genre Packs

The core [UGAS specification](../SPEC.adoc) is deliberately genre-agnostic. A **genre
pack** makes it practical to bootstrap a real game — by humans or AI agents — by bundling
two **additive** artifacts per genre:

1. an **additional spec** that extends (never replaces) the core spec with genre-specific
   Attributes, Tags, Abilities, and Effects; and
2. a **template**: ready-to-use, schema-conformant entity files.

See the [genre taxonomy](taxonomy.adoc) for the full map of genres/subgenres and how the
prioritized packs are positioned within the broader space.

## Layout contract

Each pack is one self-contained directory under `genres/`, named in kebab-case:

```
genres/
  README.md            <- this file (convention + index)
  _template/           <- copyable skeleton pack
  <genre>/
    spec.adoc          <- additional genre spec (extends the core spec)
    entities/
      *.yaml           <- template entities, each $schema-tagged with real values
    README.md          <- what the pack is + how to use it
```

## Rules

- **Additive only.** A genre `spec.adoc` MUST NOT redefine, override, or contradict any
  concept in [`SPEC.adoc`](../SPEC.adoc). It only adds genre-specific definitions and links
  back to core sections.
- **Entities must validate.** Every `.yaml`/`.json` under `genres/` must be a schema
  instance carrying a root `$schema` key that ends in one of the six core schemas
  (e.g. `…/schemas/attribute.json`). Use the version placeholder:
  `$schema: https://raw.githubusercontent.com/jbltx/ugas/%%UGAS_VERSION%%/schemas/<name>.json`.
  Only such entity files may live under `genres/` — `scripts/validate_schema_examples.py`
  validates the whole tree and fails on a missing/unknown `$schema`.
- **No placeholder scalars.** Use real values; tokens like `string` or `float` fail validation.
- **Consistent docs.** Reuse the core AsciiDoc header attributes (see `_template/spec.adoc`).
  Each `spec.adoc` is built to its own `genres/<genre>/index.html` by the docs workflows.

## Authoring a new pack

1. Copy `_template/` to `genres/<your-genre>/`.
2. Rename and fill in `spec.adoc`, the `entities/`, and `README.md`.
3. Run `python scripts/validate_schema_examples.py` — it must pass.

## Consuming a pack

Users and AI agents (e.g. the `ugas-schema-author` skill, and the planned gameplay-creator
assistant skill) can load a pack's `entities/` directly as a starting point and extend them.

## Pack index

| Pack | Status | Spec |
|------|--------|------|
| `_template` | Skeleton (reference only) | [`_template/spec.adoc`](_template/spec.adoc) |
| `rpg` | Role-Playing (RPG) — seeded by the ARPG case study | [`rpg/spec.adoc`](rpg/spec.adoc) |
