// The JS checkReferences must report exactly what scripts/check_example_references.py
// reports — same issues, same order, same text — on the Python test fixtures, the shipped
// examples and every genre pack. Needs python3 with PyYAML (PYTHON overrides the binary).
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { parseAllDocuments } from 'yaml';
import { checkReferences, formatIssue } from '../build/dist/references.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const captured = JSON.parse(
  execFileSync(process.env.PYTHON || 'python3', [path.join(HERE, 'capture_python.py')], {
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
  }),
);

// PyYAML reads YAML 1.1; `yaml` defaults to 1.2. Match the Python loader.
const parse = (file) =>
  file.path.toLowerCase().endsWith('.json')
    ? [JSON.parse(file.text)]
    : parseAllDocuments(file.text, { version: '1.1' }).map((d) => d.toJS());

test('the capture saw every Python fixture', () => {
  assert.ok(captured.fixtures >= 8, `only ${captured.fixtures} fixtures captured`);
});

// Parity alone would pass if both checkers agreed on a broken set: the shipped examples
// and every genre pack must also resolve.
test('the shipped examples and every genre pack resolve as a set', () => {
  const shipped = captured.cases.filter((c) => !c.name.startsWith('python fixture'));
  assert.ok(shipped.some((c) => c.name.startsWith('genres/')), 'no genre pack captured');
  for (const c of shipped) assert.deepEqual(c.errors, [], c.name);
});

for (const c of captured.cases) {
  test(`parity: ${c.name}`, () => {
    const entities = c.files.flatMap((f) => parse(f).map((entity) => ({ path: f.path, entity })));
    const js = checkReferences(entities, { scope: c.scope }).map(formatIssue);
    assert.deepEqual(js, c.errors);
  });
}
