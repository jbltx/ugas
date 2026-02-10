---
title: "5. Attributes"
sidebar_position: 2
---

### 5.1 Attribute Data Structure

An Attribute MUST implement the following data structure:

```typescript
struct Attribute {
  /** Permanent value, modified only by Instant effects */
  BaseValue: float;

  /** Dynamically calculated value including all active modifiers */
  CurrentValue: float;

  /** Collection of active modifiers affecting this attribute */
  Modifiers: ModifierStack;

  /** Static configuration for this attribute */
  Metadata: AttributeMetadata;
}

struct AttributeMetadata {
  /** Unique identifier for this attribute */
  Name: string;

  /** Attribute category */
  Category: AttributeCategory;

  /** Minimum allowed value (optional) */
  MinValue?: float | AttributeReference;

  /** Maximum allowed value (optional) */
  MaxValue?: float | AttributeReference;

  /** Replication configuration */
  ReplicationMode: AttributeReplicationMode;
}

enum AttributeCategory {
  /** Consumable values (Health, Mana, Stamina) */
  Resource,

  /** Derived statistics (Damage, Defense, Speed) */
  Statistic,

  /** Meta-attributes used for calculations only */
  Meta
}
```

### 5.2 Dual-Value Pattern

Every Attribute MUST implement the dual-value pattern consisting of Base Value and Current Value. This distinction is the primary mechanism for handling temporary modifications.

**Base Value**
: The permanent, persistent value of the Attribute. Base Values are modified ONLY by Instant effects and represent permanent changes such as leveling, permanent upgrades, or instant damage/healing.

**Current Value**
: The dynamically calculated result of the Base Value plus all active temporary Modifiers. Current Values are ephemeral and automatically recalculated when Modifiers are added or removed.

| Component | Modification Source | Persistence |
|-----------|---------------------|-------------|
| Base Value | Instant Effects only | Persistent (saved) |
| Current Value | All Modifier types | Ephemeral (calculated) |

### 5.3 Modifier Pipeline

The Current Value calculation MUST follow a standardized pipeline to ensure mathematical consistency across implementations.

#### Formula

The Current Value $V_{current}$ is calculated as:

$$V_{current} = \max\left( V_{min},\ \min\left( V_{max},\ \left( V_{base} + \sum a_i \right) \times \left( 1 + \sum p_j \right) \times \prod m_k + \sum b_l \right) \right)$$

Where:
- $V_{base}$ = Base Value
- $a_i$ = Flat additive modifiers (Add operations)
- $p_j$ = Additive percentage modifiers (expressed as decimals, e.g., +10% = 0.1)
- $m_k$ = Multiplicative factors (Multiply operations)
- $b_l$ = Bonus flat (Add operations)
- $V_{min}$ = Minimum value constraint
- $V_{max}$ = Maximum value constraint

Note that clamping is not mandatory, in that case the formula can be simplified as:

$$V_{current} = \left( V_{base} + \sum a_i \right) \times \left( 1 + \sum p_j \right) \times \prod m_k + \sum b_l$$

#### Order of Operations

The order of operations is CRITICAL for deterministic results:

1. Sum all flat additive modifiers (Add)
2. Apply flat additions to Base Value
3. Sum all additive percentage modifiers
4. Apply percentage modification
5. Multiply all multiplicative factors together
6. Apply multiplicative factors
7. Add the sum of all flat bonus modifiers (very rare use cases, usually there is none)
8. Apply Override modifiers (if any, replacing the result)
9. Apply clamping constraints

#### Example Calculation

Given:
- Base Value: 100
- Add Modifier 1: +20
- Add Modifier 2: +10
- Additive Percentage 1: +10% (0.1)
- Additive Percentage 2: +15% (0.15)
- Multiplicative 1: 1.5×
- Multiplicative 2: 2.0×
- No Bonus Flat

Calculation:
```
Step 1-2: 100 + 20 + 10 = 130
Step 3-4: 130 × (1 + 0.1 + 0.15) = 130 × 1.25 = 162.5
Step 5-6: 162.5 × 1.5 × 2.0 = 487.5
```

Current Value = 487.5

### 5.4 Clamping and Bounds

Attributes MAY define minimum and maximum constraints. Constraints can be:

**Static Values**
: Fixed numeric bounds that do not change.

```yaml
Clamping:
  Min: 0.0
  Max: 100.0
```

**Dependent Attribute References**
: Bounds referencing other Attributes, enabling dynamic constraints.

```yaml
Clamping:
  Min: 0.0
  Max: "MaxHealth"  # References another attribute
```

When a constraint references another Attribute:
1. The referenced Attribute's Current Value is used as the bound
2. Changes to the referenced Attribute trigger recalculation of dependent Attributes
3. Circular dependencies MUST NOT be created

### 5.5 Attribute Metadata

Attribute Metadata defines static configuration:

**Category**
- `Resource`: Consumable values that are spent and recovered (Health, Mana, Stamina)
- `Statistic`: Derived values used in calculations (Damage, Defense, CritChance)
- `Meta`: Internal values used only for calculations, not displayed to players

**Replication Flags**
- `None`: Not replicated
- `OwnerOnly`: Replicated only to owning client
- `All`: Replicated to all clients

### 5.6 OnAttributeChanged Event

Any change to an Attribute—whether to Base Value or Current Value—MUST trigger an OnAttributeChanged event.

#### Event Payload

```typescript
struct AttributeChangedEvent {
  /** The attribute that changed */
  Attribute: AttributeReference;

  /** Previous current value */
  OldValue: float;

  /** New current value */
  NewValue: float;

  /** The effect that caused the change (if any) */
  CausalEffect?: ActiveEffectHandle;

  /** Source of the change */
  Source?: AbilitySystemComponent;

  /** Target of the change */
  Target: AbilitySystemComponent;
}
```

#### Subscription Model

Observers SHOULD register for attribute change notifications:

```typescript
interface IAttributeChangeObserver {
  OnAttributeChanged(event: AttributeChangedEvent): void;
}

// Registration
GC.RegisterAttributeChangeObserver(
  attribute: AttributeReference,
  observer: IAttributeChangeObserver
): void;

// Unregistration
GC.UnregisterAttributeChangeObserver(
  attribute: AttributeReference,
  observer: IAttributeChangeObserver
): void;
```

### 5.7 Schema Definition

```yaml
Attribute:
  Name: string              # Required: Unique identifier
  DefaultBaseValue: float   # Required: Initial base value
  Category: enum            # Optional: Resource | Statistic | Meta
  Clamping:                 # Optional: Value constraints
    Min: float | string     # Static value or attribute reference
    Max: float | string     # Static value or attribute reference
  ReplicationMode: enum     # Optional: None | OwnerOnly | All
  Metadata:                 # Optional: Additional configuration
    DisplayName: string     # Human-readable name
    Description: string     # Tooltip description
    UICategory: string      # UI grouping
```

---
