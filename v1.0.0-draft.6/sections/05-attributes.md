## 5. Attributes

### 5.1 Attribute Data Structure

An Attribute MUST implement the following data structure:

``` typescript
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

Base Value  
The permanent, persistent value of the Attribute. Base Values are modified ONLY by Instant effects and represent permanent changes such as leveling, permanent upgrades, or instant damage/healing.

Current Value  
The dynamically calculated result of the Base Value plus all active temporary Modifiers. Current Values are ephemeral and automatically recalculated when Modifiers are added or removed.

| Component     | Modification Source  | Persistence            |
|---------------|----------------------|------------------------|
| Base Value    | Instant Effects only | Persistent (saved)     |
| Current Value | All Modifier types   | Ephemeral (calculated) |

#### Instant Modifiers on the Base Value

An Instant effect applies each of its Modifiers **directly to the Base Value**, in authored order, according to the operation:

- `Add` / `AddPost` — add the (signed) magnitude to the Base Value.

- `Override` — set the Base Value to the magnitude.

- `Multiply` — scale the Base Value by `(1 + m)(1 + m)`, the same signed-bonus convention the Current-Value pipeline uses (§5.3): a magnitude of `+1.0` doubles the Base Value, `-0.25` removes 25%. Channel grouping is a Current-Value concept and does not apply to a Base-Value write — each Instant `Multiply` scales the Base Value independently, in authored order.

The result is then clamped to the Attribute’s declared bounds. These per-operation rules are **total**: an implementation MUST NOT silently drop any operation (a `Multiply` on an Instant effect is a Base-Value scale, not a no-op). An Instant `Multiply` with magnitude `0` is the identity (`times 1times 1`).

This applies only to **Instant** effects. A durational (Infinite / HasDuration) effect’s `Multiply` modifiers are Current-Value modifiers (§5.3) and are never written to the Base Value — including on the periodic ticks of a periodic durational effect, whose executions apply only `Add` / `AddPost` / `Override` to the Base Value (a periodic `Multiply`-to-base would double-count against the effect’s own Current-Value contribution and compound every tick). A percentage change that must be **permanent** is authored as an Instant `Multiply`; a percentage change that lasts **while an effect is active** is a durational `Multiply` in the Current-Value pipeline.

### 5.3 Modifier Pipeline

The Current Value calculation MUST follow a standardized pipeline to ensure mathematical consistency across implementations.

#### Formula

The Current Value $V_{current}$ is calculated as:

$$V_{current} = \max\left( V_{min},\ \min\left( V_{max},\ \left( V_{base} + \sum a_i \right) \times \prod_{c \in C} \left(1 + \sum_{k \in c} m_k\right) + \sum b_l \right) \right)$$

Where: - $V_{base}$ = Base Value - $a_i$ = Pre-multiply flat additive modifiers (`Add` operations) - $C$ = the set of distinct Channel values among active `Multiply` modifiers; each modifier without a `Channel` belongs to its own unique implicit singleton channel - $m_k$ = signed bonus magnitude for each `Multiply` modifier (e.g., `+0.25` for a +25% bonus, `−0.25` for a 25% penalty) - $b_l$ = Post-multiply flat additive modifiers (`AddPost` operations; very rare) - $V_{min}$, $V_{max}$ = clamping constraints

Note that clamping is not mandatory; the simplified form is:

$$V_{current} = \left( V_{base} + \sum a_i \right) \times \prod_{c \in C} \left(1 + \sum_{k \in c} m_k\right) + \sum b_l$$

#### Channel Aggregation

The channel product $\prod_{c \in C}\!\left(1 + \sum_{k \in c} m_k\right)$ is how the "damage bucket" design is expressed at the pipeline level:

- *Same channel → bonuses ADD.* All `Multiply` modifiers sharing a `Channel` value contribute their magnitudes additively. The channel’s effective factor is `1 + sum of magnitudes`. Two +20% bonuses in the same channel yield ×1.40, not ×1.44.

- *Different channels → factors MULTIPLY.* Each channel produces one effective factor; those factors are multiplied together. A ×1.40 channel and a ×1.30 channel yield ×1.82.

- *No channel → isolated singleton.* A `Multiply` modifier without a `Channel` is in its own implicit channel, so its contribution is `1 + magnitude` — independent of all other modifiers.

This is the primary tool for preventing linear power creep: bonuses from the same source category (e.g., "damage bonuses from gear") are additive within a channel, while bonuses from categorically different sources (e.g., "gear bonuses" vs. "legendary powers") are multiplicative across channels.

#### Order of Operations

The order of operations is CRITICAL for deterministic results:

1.  Sum all flat additive modifiers (`Add`): `flat = ΣAdd`

2.  Apply flat additions to Base Value: `value = Base + flat`

3.  Group `Multiply` modifiers by `Channel`. For each channel, sum the magnitudes: `channel_factor = 1 + Σm_k`

4.  Multiply all channel factors together and apply: `value *= Π channel_factor`

5.  Add sum of all post-multiply flat additive modifiers (`AddPost`): `value += ΣAddPost`

6.  Apply `Override` modifiers (if any, replacing the result) — see conflict resolution below

7.  Apply clamping constraints

#### Override Conflict Resolution

When multiple active Override modifiers target the same Attribute simultaneously, implementations MUST resolve the conflict deterministically using the following ordered rules:

1.  *Priority wins*: The Override modifier from the `GameplayEffect` with the highest `Priority` value replaces the result. Lower-priority Overrides are ignored for that Attribute.

2.  *Last-applied wins on tie*: If two or more competing Override modifiers share the same `Priority`, the one from the most recently applied effect wins (LIFO order, determined by application timestamp).

`Priority` defaults to `0`. Effects intended to be overrideable by other effects should use lower priority values (e.g. `-10`); effects that must always dominate should use higher values (e.g. `100`).

> *Example:* A "Freeze" effect sets `MoveSpeed` Override to `0` at Priority `10`. A "Slow\` effect also sets an Override to `50` at Priority `5`. The Freeze wins because `10 > 5`. If a "Root" effect then sets an Override to `0` at Priority `10`, it ties with Freeze — the more recently applied effect’s Override is used, but the end result is identical.

#### Example Calculation

Given: - Base Value: 100 - `Add` Modifier 1: +20 - `Add` Modifier 2: +10 - `Multiply` Modifier 1: +0.10, `Channel: "Gear"` - `Multiply` Modifier 2: +0.15, `Channel: "Gear"` - `Multiply` Modifier 3: +0.50, `Channel: "Legendary"` - `Multiply` Modifier 4: +1.00, no `Channel` (implicit singleton) - No `AddPost`, no `Override`

Calculation:

    Step 1:   flat = 20 + 10 = 30
    Step 2:   value = 100 + 30 = 130
    Step 3:   channels → "Gear" = 1 + 0.10 + 0.15 = 1.25
                         "Legendary" = 1 + 0.50 = 1.50
                         <singleton> = 1 + 1.00 = 2.00
    Step 4:   value = 130 × 1.25 × 1.50 × 2.00 = 487.5
    Step 5:   value += 0  (no AddPost)
    Step 6:   no Override
    Step 7:   clamp to the attribute's bounds

Current Value = 487.5

Note that the two `Gear` modifiers **add** their magnitudes into a single ×1.25 factor rather than compounding as `1.10 × 1.15`, while the separate channels multiply — this is the power-creep control described above. A modifier with no `Channel` is its own singleton, not a member of a shared global channel.

### 5.4 Clamping and Bounds

Attributes MAY define minimum and maximum constraints. Constraints can be:

Static Values  
Fixed numeric bounds that do not change.

``` yaml
Clamping:
  Min: 0.0
  Max: 100.0
```

Dependent Attribute References  
Bounds referencing other Attributes, enabling dynamic constraints.

``` yaml
Clamping:
  Min: 0.0
  Max: "MaxHealth"  # References another attribute
```

When a constraint references another Attribute: 1. The referenced Attribute’s Current Value is used as the bound 2. Changes to the referenced Attribute trigger recalculation of dependent Attributes 3. Circular dependencies MUST NOT be created

Rule 1 means the **clamped** Current Value — §5.3 places clamping inside the definition of the Current Value (step 7 of the pipeline), so a bound resolves to the value a reader of the referenced Attribute would observe, not to its unclamped pipeline result. Resolving against the unclamped result would let a dependent Attribute exceed the very bound it references: if `MaxHealth` is itself capped at `200` and carries a `+500` buff, `Health` bounded by `Max: "MaxHealth"` MUST be limited to `200`, not to `700`.

Because a Current Value includes the referenced Attribute’s active modifiers, a bound is **temporary** when they are. An Instant Effect that writes the Base Value while a referenced bound is temporarily reduced is clamped to the reduced bound (§5.2), and that write is permanent — the Base Value does not recover when the modifier expires. Implementations SHOULD surface this in tooling, as it is a common source of surprise.

> *Note:* When a resolved `Min` exceeds a resolved `Max`, `Min` wins. This follows from the §5.3 formula $max(V_{min}, min(V_{max}, x))$, in which the `Min` clamp is applied last. Dynamic bounds make the case reachable, so implementations MUST NOT reverse the order.

### 5.5 Attribute Metadata

Attribute Metadata defines static configuration:

*Category* - `Resource`: Consumable values that are spent and recovered (Health, Mana, Stamina) - `Statistic`: Derived values used in calculations (Damage, Defense, CritChance) - `Meta`: Internal values used only for calculations, not displayed to players

*Replication Flags* - `None`: Not replicated - `OwnerOnly`: Replicated only to owning client - `All`: Replicated to all clients

### 5.6 OnAttributeChanged Event

Any change to an Attribute—whether to Base Value or Current Value—MUST trigger an OnAttributeChanged event.

#### Event Payload

``` typescript
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
  Source?: GameplayController;

  /** Target of the change */
  Target: GameplayController;
}
```

#### Subscription Model

Observers SHOULD register for attribute change notifications:

``` typescript
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

``` yaml
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
