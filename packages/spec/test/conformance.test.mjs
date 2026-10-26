// The packaged bundle, compiled by a stock Draft-07 validator, accepts conformance/valid and
// rejects conformance/invalid: the README's "validate with Ajv" holds.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { test } from 'node:test';
import Ajv from 'ajv';
import { parse } from 'yaml';
import { bundle, fileUrl, files } from '../build/dist/index.js';

const validate = new Ajv({ strict: false, allErrors: true }).compile(bundle);
const corpus = files({ kind: 'conformance' });

test('the conformance corpus is packaged', () => {
  assert.ok(corpus.some((r) => r.path.startsWith('conformance/valid/')));
  assert.ok(corpus.some((r) => r.path.startsWith('conformance/invalid/')));
});

for (const r of corpus) {
  assert.match(r.path, /^conformance\/(valid|invalid)\//, 'entity corpus must only contain entities');
  const shouldPass = r.path.startsWith('conformance/valid/');
  test(`${shouldPass ? 'accepts' : 'rejects'} ${r.path}`, () => {
    const entity = parse(readFileSync(fileUrl(r.path), 'utf8'), { version: '1.1' });
    assert.equal(validate(entity), shouldPass, JSON.stringify(validate.errors));
  });
}

const behavior = files({ kind: 'behavioral-conformance' });
const packagedRequire = createRequire(new URL('../build/package.json', import.meta.url));
const behaviorSchema = JSON.parse(readFileSync(fileUrl('conformance/behavior/format.schema.json'), 'utf8'));
const validateBehavior = new Ajv({ strict: false, allErrors: true }).compile(behaviorSchema);

test('behavior fixtures have their own manifest kind and accessible subpaths', async () => {
  assert.ok(behavior.length > 0);
  const ids = new Set();
  for (const resource of behavior) {
    assert.match(resource.path, /^conformance\/behavior\//);
    assert.ok(!corpus.some((entity) => entity.path === resource.path));
    const fixture = JSON.parse(readFileSync(fileUrl(resource.path), 'utf8'));
    assert.ok(validateBehavior(fixture), JSON.stringify(validateBehavior.errors));
    assert.ok(!ids.has(fixture.id), `duplicate behavior ID ${fixture.id}`);
    ids.add(fixture.id);
    const exportedPath = packagedRequire.resolve(`@ugas/spec/${resource.path}`);
    const imported = await import(pathToFileURL(exportedPath), { with: { type: 'json' } });
    assert.equal(imported.default.id, fixture.id);
  }
});
