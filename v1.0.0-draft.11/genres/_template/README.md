# UGAS Genre Pack: &lt;Genre Name&gt;

> One-line summary of the genre this pack targets.

This is the skeleton genre pack. Copy `genres/_template/` to `genres/<your-genre>/`
(kebab-case) and replace the contents.

## What's in this pack

| File | Purpose |
|------|---------|
| `spec.adoc` | Additional genre specification — extends, never replaces, the core spec |
| `entities/*.yaml` | Ready-to-use, schema-conformant template entities |
| `README.md` | This file |

## How to use

1. Read `spec.adoc` for the genre-specific design.
2. Copy the entity files in `entities/` into your project and adapt them.
3. They validate against the core `schemas/*.yaml`, so AI agents (e.g. the
   `ugas-schema-author` skill) can load and extend them directly.

## Published spec

<!-- Link to the built HTML once published, e.g. v<version>/genres/<genre>/index.html -->
