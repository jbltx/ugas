# ugas

The [Universal Gameplay Ability System](https://github.com/jbltx/ugas) specification as an
npm package: JSON schemas, the pre-chunked spec, genre packs, the conformance corpus,
TypeScript types for every entity, and the cross-entity reference checker.

The package version is the spec release: `@ugas/spec@1.0.0-draft.7` is UGAS `v1.0.0-draft.7`.
Drafts are published under the `next` dist-tag.

```sh
npm install @ugas/spec@next
```

## What it exports

```ts
import {
  VERSION,        // '1.0.0-draft.7'
  ENTITY_TYPES,   // ['attribute', 'attribute_set', 'gameplay_ability', ...]
  SCHEMA_IDS,     // { gameplay_effect: 'https://ugas.jbltx.com/v1.0.0-draft.7/schemas/gameplay_effect.json', ... }
  schemas,        // per-type JSON Schemas
  bundle,         // schemas/bundle.json: every schema in one offline-resolvable document
  manifest,       // index.json: every packaged file with its kind and sha256
  files,          // files({ kind: 'spec-section' }) -> [{ path: 'sections/05-attributes.md', ... }]
  fileUrl,        // fileUrl('schemas/bundle.json') -> file: URL, for Node
  checkReferences,
} from '@ugas/spec';
import type { GameplayEffect, Attribute, EntityByType, UgasEntity } from '@ugas/spec';
```

Validate an entity against the bundle with any Draft-07 validator, for example Ajv:

```ts
import Ajv from 'ajv';
import { bundle } from '@ugas/spec';

const validate = new Ajv({ strict: false }).compile(bundle); // dispatches on the entity's $schema
validate(entity);
```

`checkReferences` finds the references schema validation cannot: an effect modifying an
attribute that is not defined, an ability whose `Cost` names no effect, a tag missing from
the registry. It takes the whole set at once and returns `{ path, message }[]`, empty when
the set resolves. It is a port of the repo's `scripts/check_example_references.py`, and a
parity test keeps the two in agreement.

```ts
import { checkReferences } from '@ugas/spec';

const issues = checkReferences([
  { path: 'health.yaml', entity: health },
  { path: 'damage.yaml', entity: damage },
]);
```

## Files

Paths match the published site, `https://ugas.jbltx.com/v<version>/<path>`, and are listed
with their sha256 in `index.json`. Import them through the subpath exports, e.g.
`@ugas/spec/schemas/bundle.json`, `@ugas/spec/sections/05-attributes.md`, `@ugas/spec/genres/index.json`.

| Path | What it is |
|------|------------|
| `index.json` | Manifest of every file: `id`, `kind`, `path`, `sha256` |
| `SPEC.md`, `sections/` | The spec in one file, and pre-chunked by section (`sections/index.json`) |
| `schemas/` | `<type>.json` / `.yaml`, `bundle.json`, `examples/`, `manifest/` meta-schemas |
| `genres/` | `index.json`, and per pack `spec.adoc` and `entities/*.yaml` |
| `conformance/` | `valid/` and `invalid/` entities for testing a loader or validator |
| `rag/` | Retrieval chunks and an intent index |

See [Consuming UGAS programmatically](https://github.com/jbltx/ugas/blob/main/docs/CONSUMING.md)
for how the artifacts fit together.

## License

MIT
