---
title: "6. Attribute Sets"
sidebar_position: 3
---

### 6.1 Purpose and Composition

An Attribute Set is a logical container grouping related Attributes. Attribute Sets provide:

- **Modularity**: Actors can mix and match sets based on capabilities
- **Organization**: Related Attributes are defined together
- **Reusability**: Common sets can be shared across Actor types
- **Serialization Boundary**: Sets define units for save/load operations

### 6.2 Set Registration with GC

Attribute Sets MUST be registered with an GC before use:

```typescript
/**
 * Registers an attribute set with this GC.
 * @param attributeSet - The set to register
 */
GC.RegisterAttributeSet(attributeSet: AttributeSet): void;

/**
 * Unregisters an attribute set from this GC.
 * @param attributeSet - The set to unregister
 */
GC.UnregisterAttributeSet(attributeSet: AttributeSet): void;

/**
 * Retrieves a registered attribute set by type.
 * @returns The attribute set, or null if not registered
 */
GC.GetAttributeSet<T extends AttributeSet>(): T | null;
```

### 6.3 Modular Design Patterns

#### Combat Attribute Set

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/attribute_set.json
Name: "CombatAttributeSet"
Attributes:
  - Name: "Health"
    DefaultBaseValue: 100.0
    Category: Resource
    Clamping:
      Min: 0.0
      Max: "MaxHealth"

  - Name: "MaxHealth"
    DefaultBaseValue: 100.0
    Category: Statistic
    Clamping:
      Min: 1.0

  - Name: "Mana"
    DefaultBaseValue: 50.0
    Category: Resource
    Clamping:
      Min: 0.0
      Max: "MaxMana"

  - Name: "MaxMana"
    DefaultBaseValue: 50.0
    Category: Statistic
    Clamping:
      Min: 0.0

  - Name: "AttackPower"
    DefaultBaseValue: 10.0
    Category: Statistic

  - Name: "Defense"
    DefaultBaseValue: 5.0
    Category: Statistic
```

#### Movement Attribute Set

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/attribute_set.json
Name: "MovementAttributeSet"
Attributes:
  - Name: "MoveSpeed"
    DefaultBaseValue: 600.0
    Category: Statistic
    Clamping:
      Min: 0.0

  - Name: "JumpVelocity"
    DefaultBaseValue: 800.0
    Category: Statistic

  - Name: "GravityScale"
    DefaultBaseValue: 1.0
    Category: Statistic

  - Name: "AirControl"
    DefaultBaseValue: 0.5
    Category: Statistic
    Clamping:
      Min: 0.0
      Max: 1.0
```

#### Vehicle Attribute Set

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/attribute_set.json
Name: "VehicleAttributeSet"
Attributes:
  - Name: "EngineTorque"
    DefaultBaseValue: 500.0
    Category: Statistic

  - Name: "MaxSpeed"
    DefaultBaseValue: 200.0
    Category: Statistic

  - Name: "TireGrip"
    DefaultBaseValue: 1.0
    Category: Statistic

  - Name: "Fuel"
    DefaultBaseValue: 100.0
    Category: Resource
    Clamping:
      Min: 0.0
      Max: "MaxFuel"

  - Name: "MaxFuel"
    DefaultBaseValue: 100.0
    Category: Statistic
```

### 6.4 Cross-Set Dependencies

Attributes MAY reference Attributes from other registered sets:

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/attribute_set.json
Name: "DerivedStatsSet"
Dependencies:
  - "CombatAttributeSet"
Attributes:
  - Name: "EffectiveHealth"
    DefaultBaseValue: 0.0
    Category: Meta
    DerivedFrom:
      Expression: "Health * (1 + Defense / 100)"
```

Cross-set references are resolved at runtime. Implementations MUST:

1. Validate all dependencies exist before registration
2. Ensure proper recalculation order when dependencies change
3. Prevent circular dependency chains

### 6.5 Schema Definition

```yaml
AttributeSet:
  Name: string                    # Required: Unique set identifier
  Dependencies: [string]          # Optional: Required attribute sets
  Attributes: [Attribute]         # Required: List of attributes
  Metadata:                       # Optional: Additional configuration
    DisplayName: string
    Description: string
```

---
