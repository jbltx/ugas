# UGAS Schema Definitions

This directory contains formal schema definitions for the Universal Gameplay Ability System (UGAS) specification. These schemas are provided in both JSON Schema and YAML formats for maximum compatibility.

## Schema Files

| Schema | JSON | YAML | Description |
|--------|------|------|-------------|
| **Gameplay Controller** | `gameplay_controller.json` | `gameplay_controller.yaml` | Interface schema for the Gameplay Controller (GC), the central hub managing abilities, effects, attributes, and tags |
| **Attribute** | `attribute.json` | `attribute.yaml` | Schema for individual attribute definitions with base values, clamping, and replication settings |
| **Attribute Set** | `attribute_set.json` | `attribute_set.yaml` | Schema for attribute collections that group related attributes |
| **Gameplay Effect** | `gameplay_effect.json` | `gameplay_effect.yaml` | Schema for effects that modify attributes, grant tags/abilities, with duration and magnitude definitions |
| **Gameplay Ability** | `gameplay_ability.json` | `gameplay_ability.yaml` | Schema for ability definitions with tag-based activation requirements and blocking rules |
| **Gameplay Tag** | `gameplay_tag.json` | `gameplay_tag.yaml` | Schema for the tag registry defining semantic state labels in hierarchical notation |

## Schema Format

All schemas follow standard JSON Schema (Draft 07) and YAML schema conventions:

- **JSON Schemas**: Include `$schema`, `$id`, and `title` metadata
- **YAML Schemas**: Structured for readability with inline comments
- **Cross-references**: Use `$ref` for shared definitions within schemas

## Usage Examples

### Attribute Definition

```yaml
# health_attribute.yaml
Name: Health
DefaultBaseValue: 100.0
Category: Resource
Clamping:
  Min: 0
  Max: MaxHealth  # Reference to another attribute
ReplicationMode: All
Metadata:
  DisplayName: Health Points
  Description: Character's life force
  UICategory: Vital Stats
  Icon: ui/icons/health.png
```

### Gameplay Effect Definition

```yaml
# damage_effect.yaml
Name: DamageEffect
DurationPolicy: Instant
Modifiers:
  - Attribute: Health
    Operation: Add
    Magnitude:
      Type: ScalableFloat
      Value: -25.0
GrantedTags:
  - State.Damaged
GameplayCues:
  - GameplayCue.Character.Damage
```

### Gameplay Ability Definition

```yaml
# fireball_ability.yaml
Name: FireballAbility
Tags:
  AbilityTags:
    - Ability.Magic.Fireball
  ActivationRequiredTags:
    - State.CanCast
  ActivationBlockedTags:
    - State.Silenced
    - State.Stunned
  ActivationOwnedTags:
    - State.Casting
Cost: ManaCostEffect
Cooldown: FireballCooldownEffect
Metadata:
  DisplayName: Fireball
  Description: Launch a ball of fire at the target
  Icon: ui/icons/fireball.png
```

### Gameplay Tag Registry

```yaml
# tag_registry.yaml
Tags:
  - Tag: State.Combat
    Description: Entity is in combat
    AllowMultiple: false

  - Tag: State.Debuff.Stunned
    Description: Entity is stunned and cannot act
    AllowMultiple: false

  - Tag: Ability.Magic.Fireball
    Description: Fireball ability identifier
    AllowMultiple: false
```

### Gameplay Controller Instance

```json
{
  "OwnerActor": {
    "ActorID": "player_001",
    "ActorType": "PlayerState"
  },
  "AvatarActor": {
    "ActorID": "character_001",
    "ActorType": "PlayerCharacter"
  },
  "AttributeSets": [
    {
      "Name": "VitalAttributes",
      "Attributes": [
        {
          "Name": "Health",
          "BaseValue": 100.0,
          "CurrentValue": 100.0
        },
        {
          "Name": "MaxHealth",
          "BaseValue": 100.0,
          "CurrentValue": 100.0
        }
      ]
    }
  ],
  "GrantedAbilities": [
    {
      "AbilityClass": "FireballAbility",
      "Level": 1,
      "InputID": "Ability1",
      "Handle": "ability_handle_001",
      "bIsActive": false
    }
  ],
  "ActiveEffects": [],
  "OwnedTags": ["State.Idle"],
  "ReplicationMode": "Mixed",
  "bIsActive": true
}
```

## Schema Validation

### JSON Schema Validation

Using Python:
```python
import json
import jsonschema

# Load schema and data
with open('schemas/gameplay_effect.json') as f:
    schema = json.load(f)

with open('my_effect.json') as f:
    data = json.load(f)

# Validate
jsonschema.validate(data, schema)
```

Using Node.js (with `ajv`):
```javascript
const Ajv = require('ajv');
const ajv = new Ajv();

const schema = require('./schemas/gameplay_effect.json');
const data = require('./my_effect.json');

const validate = ajv.compile(schema);
const valid = validate(data);

if (!valid) console.log(validate.errors);
```

### YAML Schema Validation

YAML files can be validated by loading them and comparing against the schema structure, or by converting to JSON and using JSON Schema validation.

## Specification Reference

These schemas are based on the **Universal Gameplay Ability System Specification v1.0**, particularly:

- **Section 4**: Gameplay Controller - `gameplay_controller.{json,yaml}`
- **Section 5**: Attributes - `attribute.{json,yaml}`
- **Section 6**: Attribute Sets - `attribute_set.{json,yaml}`
- **Section 7**: Gameplay Tags - `gameplay_tag.{json,yaml}`
- **Section 8**: Gameplay Abilities - `gameplay_ability.{json,yaml}`
- **Section 9**: Gameplay Effects - `gameplay_effect.{json,yaml}`
- **Appendix B**: Complete Schema Reference

## Notes

1. **Single Source of Truth**: While SPEC.md contains the authoritative specification, these machine-readable schemas enable automated validation and tooling.

2. **Format Choice**:
   - Use JSON schemas for strict validation in programming contexts
   - Use YAML schemas for human-readable configuration files

3. **Extensions**: Implementations may extend these schemas with additional properties while maintaining backward compatibility with the core specification.

4. **Versioning**: Schema files follow the UGAS specification version. Any breaking changes will result in new schema files with version suffixes.

## License

These schemas are part of the UGAS specification and follow the same license as the parent repository.
