// Compile-only: the published types read the way a consumer uses them.
import { VERSION, SCHEMA_IDS, checkReferences, files, type GameplayEffect, type EntityByType, type UgasEntity, type ReferenceIssue } from 'ugas';
import { checkReferences as fromSubpath } from 'ugas/references';
import type { Attribute } from 'ugas/types';

const effect: GameplayEffect = {
  $schema: SCHEMA_IDS.gameplay_effect,
  Name: 'GE_Damage',
  DurationPolicy: 'Instant',
  Modifiers: [{ Attribute: 'Health', Operation: 'Add', Magnitude: { Type: 'ScalableFloat', Value: -10 } }],
};
const health: EntityByType['attribute'] = { Name: 'Health', DefaultBaseValue: 100 } as Attribute;
const all: UgasEntity[] = [effect, health];
const issues: ReferenceIssue[] = checkReferences(all.map((entity) => ({ path: 'x', entity })));
fromSubpath([]);
const v: string = VERSION;
const n: number = files({ kind: 'schema' }).length;
// @ts-expect-error DurationPolicy is an enum
const bad: GameplayEffect = { Name: 'x', DurationPolicy: 'Sometimes' };
void [issues, v, n, bad];
