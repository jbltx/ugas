// The built package (packages/spec/build): exports, version, schema ids and the file listing.
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import * as ugas from '../build/dist/index.js';

const BUILD = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'build');
const ROOT = path.resolve(BUILD, '..', '..', '..');
const pkg = JSON.parse(readFileSync(path.join(BUILD, 'package.json'), 'utf8'));

test('VERSION is the repo version and the npm version', () => {
  const root = JSON.parse(readFileSync(path.join(ROOT, 'package.json'), 'utf8')).version;
  assert.equal(ugas.VERSION, process.env.UGAS_VERSION?.replace(/^v/, '') || root);
  assert.equal(pkg.version, ugas.VERSION);
  assert.equal(ugas.manifest.version, ugas.VERSION);
});

test('SCHEMA_IDS match each schema $id and the bundle covers every type', () => {
  assert.ok(ugas.ENTITY_TYPES.length >= 11);
  for (const type of ugas.ENTITY_TYPES) {
    const id = `https://ugas.jbltx.com/v${ugas.VERSION}/schemas/${type}.json`;
    assert.equal(ugas.SCHEMA_IDS[type], id);
    assert.equal(ugas.schemaId(type), id);
    assert.equal(ugas.schemas[type].$id, id);
    assert.ok(ugas.bundle.$defs[type], `bundle has no $defs.${type}`);
  }
});

test('no unresolved version placeholder ships', () => {
  for (const r of ugas.files()) {
    if (/\.(json|ya?ml|md|adoc)$/.test(r.path)) {
      assert.ok(!readFileSync(path.join(BUILD, r.path), 'utf8').includes('%%UGAS_VERSION%%'), r.path);
    }
  }
});

test('files() lists every packaged file with a matching sha256', () => {
  const all = ugas.files();
  assert.equal(all.length, ugas.manifest.resources.length);
  for (const r of all) {
    assert.ok(!r.path.startsWith('v'), r.path);
    const buf = readFileSync(ugas.fileUrl(r.path));
    assert.equal(createHash('sha256').update(buf).digest('hex'), r.sha256, r.path);
  }
  const bundles = ugas.files({ kind: 'schema-bundle' });
  assert.deepEqual(bundles.map((r) => r.path), ['schemas/bundle.json']);
  assert.ok(ugas.files({ kind: ['spec-section'] }).length >= 20);
});

test('every exports subpath target exists', () => {
  for (const [subpath, target] of Object.entries(pkg.exports)) {
    const targets = typeof target === 'string' ? [target] : Object.values(target);
    for (const t of targets) {
      if (t.includes('*')) assert.ok(existsSync(path.join(BUILD, path.dirname(t))), subpath);
      else assert.ok(existsSync(path.join(BUILD, t)), `${subpath} -> ${t}`);
    }
  }
});

test('the published package.json has no dev-only fields', () => {
  assert.equal(pkg.scripts, undefined);
  assert.equal(pkg.devDependencies, undefined);
  assert.equal(pkg.private, undefined);
  assert.deepEqual(pkg.publishConfig, { access: 'public', provenance: true });
});
