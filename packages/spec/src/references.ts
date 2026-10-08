/**
 * Cross-entity reference checks: a port of scripts/check_example_references.py.
 *
 * Every schema-supported cross-entity reference (an effect's Modifiers[].Attribute, an
 * ability's Cost, a tag a scene uses, ...) must name an entity in the same set. Schema
 * validation cannot catch this: each entity is valid on its own. The rules, their order
 * and the message text match the Python checker; test/parity.test.mjs holds both to that
 * on the shipped examples, every genre pack and the Python test fixtures.
 */

/** One entity to check, and where it came from (used as the issue's path). */
export interface EntitySource {
  path: string;
  entity: unknown;
}

/** A reference that names nothing in the checked set. */
export interface ReferenceIssue {
  path: string;
  message: string;
}

export interface CheckReferencesOptions {
  /**
   * Name of the set being checked, e.g. the directory name. When given it appears in
   * messages ("names no effect in examples/"), as it does in the Python checker.
   */
  scope?: string;
}

type Dict = Record<string, unknown>;
type Kind =
  | 'attribute'
  | 'attribute set'
  | 'effect'
  | 'ability'
  | 'scene'
  | 'input action'
  | 'input action set'
  | 'input modifier';

const ABILITY_TAG_FIELDS = [
  'AbilityTags',
  'BlockedByTags',
  'BlockAbilitiesWithTags',
  'CancelAbilitiesWithTags',
  'ActivationRequiredTags',
  'ActivationBlockedTags',
  'ActivationOwnedTags',
];
const EFFECT_TAG_FIELDS = ['GrantedTags', 'ApplicationRequiredTags', 'GameplayCues'];

const isDict = (v: unknown): v is Dict => typeof v === 'object' && v !== null && !Array.isArray(v);
const items = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const mapping = (v: unknown): Dict => (isDict(v) ? v : {});
/** Python's dict.get: a missing key and an explicit null are both None. */
const get = (d: unknown, key: string): unknown => (isDict(d) && d[key] !== undefined ? d[key] : null);

/** Python's str() of a YAML/JSON value, so messages read the same in both checkers. */
function pyStr(v: unknown): string {
  if (v === null || v === undefined) return 'None';
  if (v === true) return 'True';
  if (v === false) return 'False';
  if (typeof v === 'string') return v;
  if (typeof v === 'number') return String(v);
  return pyRepr(v);
}
function pyRepr(v: unknown): string {
  if (typeof v === 'string') return `'${v.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;
  if (Array.isArray(v)) return `[${v.map(pyRepr).join(', ')}]`;
  if (isDict(v)) return `{${Object.entries(v).map(([k, x]) => `${pyRepr(k)}: ${pyRepr(x)}`).join(', ')}}`;
  return pyStr(v);
}

/** The entity type named by a `$schema` id: `.../schemas/gameplay_effect.json` -> `gameplay_effect`. */
export function schemaType(entity: unknown): string | null {
  const ref = get(entity, '$schema');
  if (typeof ref !== 'string') return null;
  const last = ref.slice(ref.lastIndexOf('/') + 1);
  return last.endsWith('.json') ? last.slice(0, -'.json'.length) : last;
}

/**
 * Check that every cross-entity reference in `entities` names an entity in that same set.
 * Returns one issue per dangling reference, in the Python checker's order; [] means the
 * set resolves. Entities without a recognised `$schema` are ignored.
 */
export function checkReferences(
  entities: Iterable<EntitySource>,
  options: CheckReferencesOptions = {},
): ReferenceIssue[] {
  const { scope } = options;
  const byType = new Map<string | null, [string, unknown][]>();
  for (const { path, entity } of entities) {
    if (!isDict(entity)) continue;
    const type = schemaType(entity);
    if (!byType.has(type)) byType.set(type, []);
    byType.get(type)!.push([path, entity]);
  }
  const of = (type: string) => byType.get(type) ?? [];

  const attributes: [string, unknown][] = [...of('attribute')];
  for (const [src, aset] of of('attribute_set')) {
    for (const a of items(get(aset, 'Attributes'))) attributes.push([src, a]);
  }
  const names = (type: string) => new Set(of(type).map(([, e]) => get(e, 'Name')));
  const known: Record<Kind, Set<unknown>> = {
    attribute: new Set(attributes.map(([, a]) => get(a, 'Name'))),
    'attribute set': names('attribute_set'),
    effect: names('gameplay_effect'),
    ability: names('gameplay_ability'),
    scene: names('scene'),
    'input action': names('input_action'),
    'input action set': names('input_action_set'),
    'input modifier': names('input_modifier'),
  };
  const registered = new Set<unknown>();
  for (const [, reg] of of('gameplay_tag')) {
    for (const t of items(get(reg, 'Tags'))) registered.add(get(t, 'Tag'));
  }

  const issues: ReferenceIssue[] = [];
  const tagUses: [string, string, unknown][] = [];
  const where = scope === undefined ? '' : ` in ${scope}/`;

  const expect = (src: string, field: string, name: unknown, kind: Kind) => {
    if (!known[kind].has(name)) {
      issues.push({ path: src, message: `${field} '${pyStr(name)}' names no ${kind}${where}` });
    }
  };
  const expectAll = (src: string, field: string, values: unknown, kind: Kind) => {
    for (const name of items(values)) expect(src, field, name, kind);
  };
  const tags = (src: string, field: string, values: unknown) => {
    for (const tag of items(values)) tagUses.push([src, field, tag]);
  };
  const magnitude = (src: string, field: string, mag: unknown) => {
    const m = mapping(mag);
    if (get(m, 'BackingAttribute') !== null) {
      expect(src, `${field}.BackingAttribute`, m.BackingAttribute, 'attribute');
    }
    if (get(m, 'DataTag') !== null) tags(src, `${field}.DataTag`, [m.DataTag]);
  };
  const grants = (src: string, field: string, values: unknown) => {
    for (const grant of items(values)) {
      expect(src, `${field}.AbilityClass`, get(grant, 'AbilityClass'), 'ability');
      if (get(grant, 'InputID') !== null) {
        expect(src, `${field}.InputID`, get(grant, 'InputID'), 'input action');
      }
    }
  };

  for (const [src, attr] of attributes) {
    for (const bound of ['Min', 'Max']) {
      const value = get(mapping(get(attr, 'Clamping')), bound);
      if (typeof value === 'string') {
        expect(src, `${pyStr(get(attr, 'Name'))}.Clamping.${bound}`, value, 'attribute');
      }
    }
  }

  for (const [src, aset] of of('attribute_set')) {
    expectAll(src, 'Dependencies', get(aset, 'Dependencies'), 'attribute set');
  }

  for (const [src, effect] of of('gameplay_effect')) {
    magnitude(src, 'Duration', get(effect, 'Duration'));
    for (const mod of items(get(effect, 'Modifiers'))) {
      expect(src, 'Modifiers.Attribute', get(mod, 'Attribute'), 'attribute');
      magnitude(src, 'Modifiers.Magnitude', get(mod, 'Magnitude'));
    }
    grants(src, 'GrantedAbilities', get(effect, 'GrantedAbilities'));
    for (const field of EFFECT_TAG_FIELDS) tags(src, field, get(effect, field));
    const area = mapping(get(effect, 'Area'));
    magnitude(src, 'Area.Radius', get(area, 'Radius'));
    tags(src, 'Area.RequireTags', get(area, 'RequireTags'));
    tags(src, 'Area.ExcludeTags', get(area, 'ExcludeTags'));
  }

  for (const [src, ability] of of('gameplay_ability')) {
    for (const field of ['Cost', 'Cooldown']) {
      if (get(ability, field) !== null) expect(src, field, get(ability, field), 'effect');
    }
    for (const field of ABILITY_TAG_FIELDS) {
      tags(src, `Tags.${field}`, get(mapping(get(ability, 'Tags')), field));
    }
    for (const task of items(get(ability, 'Tasks'))) {
      for (const [key, raw] of Object.entries(mapping(get(task, 'Params')))) {
        const value = raw === undefined ? null : raw;
        if (key === 'EffectClass') expect(src, 'Tasks.Params.EffectClass', value, 'effect');
        else if (key === 'InputID') expect(src, 'Tasks.Params.InputID', value, 'input action');
        else if (key.endsWith('Tag') && typeof value === 'string') tags(src, `Tasks.Params.${key}`, [value]);
        else if (key.endsWith('Tags')) tags(src, `Tasks.Params.${key}`, value);
      }
    }
  }

  for (const [src, gc] of of('gameplay_controller')) {
    for (const aset of items(get(gc, 'AttributeSets'))) {
      expect(src, 'AttributeSets.Name', get(aset, 'Name'), 'attribute set');
      for (const attr of items(get(aset, 'Attributes'))) {
        expect(src, 'AttributeSets.Attributes.Name', get(attr, 'Name'), 'attribute');
      }
    }
    grants(src, 'GrantedAbilities', get(gc, 'GrantedAbilities'));
    for (const active of items(get(gc, 'ActiveEffects'))) {
      expect(src, 'ActiveEffects.EffectClass', get(active, 'EffectClass'), 'effect');
      if (get(active, 'SourceAbility') !== null) {
        expect(src, 'ActiveEffects.SourceAbility', get(active, 'SourceAbility'), 'ability');
      }
      expectAll(src, 'ActiveEffects.CapturedAttributes', Object.keys(mapping(get(active, 'CapturedAttributes'))), 'attribute');
      tags(src, 'ActiveEffects.SetByCallerMagnitudes', Object.keys(mapping(get(active, 'SetByCallerMagnitudes'))));
    }
    expectAll(src, 'ActiveActionSets', get(gc, 'ActiveActionSets'), 'input action set');
    tags(src, 'OwnedTags', get(gc, 'OwnedTags'));
  }

  for (const [src, scene] of of('scene')) {
    expectAll(src, 'Extends', get(scene, 'Extends'), 'scene');
    for (const placement of items(get(scene, 'Placements'))) {
      tags(src, 'Placements.StartupTags', get(placement, 'StartupTags'));
      expectAll(src, 'Placements.StartupEffects', get(placement, 'StartupEffects'), 'effect');
      expectAll(src, 'Placements.AttributeOverrides', Object.keys(mapping(get(placement, 'AttributeOverrides'))), 'attribute');
    }
    for (const region of items(get(scene, 'Regions'))) {
      tags(src, 'Regions.GrantedTags', get(region, 'GrantedTags'));
      const regionFilter = mapping(get(region, 'Filter'));
      tags(src, 'Regions.Filter.RequireTags', get(regionFilter, 'RequireTags'));
      tags(src, 'Regions.Filter.ExcludeTags', get(regionFilter, 'ExcludeTags'));
    }
    for (const spawn of items(get(scene, 'SpawnPoints'))) tags(src, 'SpawnPoints.Tags', get(spawn, 'Tags'));
  }

  for (const [src, action] of of('input_action')) {
    tags(src, 'Tags.ActionTags', get(mapping(get(action, 'Tags')), 'ActionTags'));
  }

  for (const [src, aset] of of('input_action_set')) {
    expectAll(src, 'Actions', get(aset, 'Actions'), 'input action');
    const activation = mapping(get(aset, 'ActivationTags'));
    tags(src, 'ActivationTags.RequiredTags', get(activation, 'RequiredTags'));
    tags(src, 'ActivationTags.BlockedTags', get(activation, 'BlockedTags'));
  }

  const setActions = new Map<unknown, Set<unknown>>();
  for (const [, aset] of of('input_action_set')) {
    setActions.set(get(aset, 'Name'), new Set(items(get(aset, 'Actions'))));
  }
  for (const [src, imap] of of('input_mapping')) {
    const setName = get(imap, 'ActionSet');
    expect(src, 'ActionSet', setName, 'input action set');
    for (const binding of items(get(imap, 'Bindings'))) {
      const action = get(binding, 'Action');
      expect(src, 'Bindings.Action', action, 'input action');
      // A mapping binds within its Action Set (§11.5), so the action must be a member.
      const members = setActions.get(setName);
      if (members && !members.has(action)) {
        issues.push({
          path: src,
          message: `Bindings.Action '${pyStr(action)}' is not in action set '${pyStr(setName)}'`,
        });
      }
      expectAll(src, 'Bindings.Modifiers', get(binding, 'Modifiers'), 'input modifier');
      tags(src, 'Bindings.Tags.RequiredTags', get(mapping(get(binding, 'Tags')), 'RequiredTags'));
    }
  }

  if (tagUses.length && registered.size === 0) {
    issues.push({
      path: scope === undefined ? '' : `${scope}/`,
      message: 'examples use tags but no tag registry was found',
    });
  } else if (registered.size) {
    const prefixes = [...registered].filter((r): r is string => typeof r === 'string');
    for (const [src, field, tag] of tagUses) {
      // A parent of a registered tag is implicitly registered (§7 hierarchy).
      const parent = `${pyStr(tag)}.`;
      if (!registered.has(tag) && !prefixes.some((r) => r.startsWith(parent))) {
        issues.push({ path: src, message: `${field} tag '${pyStr(tag)}' is not in the tag registry` });
      }
    }
  }
  return issues;
}

/** `path: message`, the line format the Python checker prints. */
export function formatIssue(issue: ReferenceIssue): string {
  return `${issue.path}: ${issue.message}`;
}
