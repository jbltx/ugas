// The cases of scripts/test_check_example_references.py, against the JS port directly.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { checkReferences } from '../build/dist/references.js';

const BASE = 'https://ugas.jbltx.com/0/schemas/';
const e = (type, fields) => ({ $schema: `${BASE}${type}.json`, ...fields });
const ATTRIBUTE = e('attribute', { Name: 'Health', DefaultBaseValue: 100 });
const REGISTRY = e('gameplay_tag', { Tags: [{ Tag: 'Faction.Enemy' }] });

const run = (...entities) =>
  checkReferences(entities.map((entity, i) => ({ path: `e${i}.yaml`, entity })), { scope: 'fixture' });

function expectIssues(issues, ...needles) {
  const lines = issues.map((i) => `${i.path}: ${i.message}`);
  if (!needles.length) return assert.deepEqual(lines, []);
  for (const n of needles) assert.ok(lines.some((l) => l.includes(n)), `missing ${n} in ${JSON.stringify(lines)}`);
}

test('scene references are checked', () => {
  expectIssues(
    run(ATTRIBUTE, REGISTRY, e('scene', {
      Name: 'Arena',
      Placements: [{ Controller: 'Goblin', StartupTags: ['Faction.Player'], StartupEffects: ['Missing_GE'], AttributeOverrides: { Mana: 10 } }],
      Regions: [{
        Name: 'Pit', Shape: 'Sphere', Origin: [0, 0, 0], Radius: 4,
        Filter: { ExcludeTags: ['State.Immune'] }, GrantedTags: ['Zone.Hazard.Fire'],
      }],
      SpawnPoints: [{ Name: 'Respawn', Tags: ['Spawn.Player'] }],
    })),
    "'Faction.Player'", "'Missing_GE'", "'Mana'", "'Zone.Hazard.Fire'", "'State.Immune'", "'Spawn.Player'",
  );
});

test('effect magnitudes and area tags are checked', () => {
  expectIssues(
    run(ATTRIBUTE, REGISTRY, e('gameplay_effect', {
      Name: 'GE_Blast',
      DurationPolicy: 'Instant',
      Modifiers: [{ Attribute: 'Health', Operation: 'Add', Magnitude: { Type: 'AttributeBased', BackingAttribute: 'AttackPower' } }],
      Area: { Shape: 'Sphere', Radius: { Type: 'SetByCaller', DataTag: 'Data.Radius' }, RequireTags: ['Faction.Enemy'], ExcludeTags: ['State.Dead'] },
    })),
    "'AttackPower'", "'Data.Radius'", "'State.Dead'",
  );
});

test('no registry is fine when no tag is used', () => {
  expectIssues(run(ATTRIBUTE, e('gameplay_effect', {
    Name: 'GE_Hit', DurationPolicy: 'Instant',
    Modifiers: [{ Attribute: 'Health', Operation: 'Add', Magnitude: { Type: 'ScalableFloat', Value: -1 } }],
  })));
});

test('no registry fails once a tag is used', () => {
  const issues = run(ATTRIBUTE, e('gameplay_effect', { Name: 'GE_Hit', DurationPolicy: 'Instant', GrantedTags: ['State.Damaged'] }));
  expectIssues(issues, 'no tag registry');
  assert.equal(issues.at(-1).path, 'fixture/');
});

test('task Params.InputID is checked', () => {
  expectIssues(
    run(REGISTRY, e('input_action', { Name: 'Jump', ValueType: 'Digital' }),
      e('gameplay_ability', { Name: 'GA_Charge', Tasks: [{ Type: 'WaitInputRelease', Params: { InputID: 'Charge' } }] })),
    "Tasks.Params.InputID 'Charge'",
  );
});

test("mapping bindings must be in the mapping's action set", () => {
  expectIssues(
    run(
      e('input_action', { Name: 'Jump', ValueType: 'Digital' }),
      e('input_action', { Name: 'Steer', ValueType: 'Axis1D' }),
      e('input_action_set', { Name: 'OnFoot', Actions: ['Jump'] }),
      e('input_action_set', { Name: 'InVehicle', Actions: ['Steer'] }),
      e('input_mapping', {
        ActionSet: 'OnFoot',
        Bindings: [
          { Action: 'Jump', Inputs: [{ Device: 'Keyboard', Input: 'Space' }] },
          { Action: 'Steer', Inputs: [{ Device: 'Keyboard', Input: 'A' }] },
        ],
      }),
    ),
    "'Steer' is not in action set 'OnFoot'",
  );
});

test('a parent of a registered tag counts as registered', () => {
  expectIssues(run(REGISTRY, e('gameplay_effect', { Name: 'GE', DurationPolicy: 'Instant', GrantedTags: ['Faction'] })));
});

test('without a scope, messages carry no directory', () => {
  const [issue] = checkReferences([{ path: 'a.json', entity: e('gameplay_ability', { Name: 'GA', Cost: 'Nope' }) }]);
  assert.deepEqual(issue, { path: 'a.json', message: "Cost 'Nope' names no effect" });
});
