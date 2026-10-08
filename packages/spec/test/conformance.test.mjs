// The packaged bundle, compiled by a stock Draft-07 validator, accepts conformance/valid and
// rejects conformance/invalid: the README's "validate with Ajv" holds.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
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
  const shouldPass = r.path.startsWith('conformance/valid/');
  test(`${shouldPass ? 'accepts' : 'rejects'} ${r.path}`, () => {
    const entity = parse(readFileSync(fileUrl(r.path), 'utf8'), { version: '1.1' });
    assert.equal(validate(entity), shouldPass, JSON.stringify(validate.errors));
  });
}
