---
title: "7. Gameplay Tags"
sidebar_position: 4
---

### 7.1 Hierarchical Naming Convention

Gameplay Tags use hierarchical dot-notation to represent semantic categories:

```
Category.Subcategory.Leaf
```

Examples:
- `State.Debuff.Stunned.Magic`
- `Ability.Type.Melee.Slash`
- `DamageType.Physical.Blunt`
- `Cooldown.Ability.Fireball`
- `GameplayCue.Impact.Fire`

#### Naming Rules

1. Each segment MUST use PGCalCase
2. Hierarchies SHOULD NOT exceed 5 levels
3. Leaf tags SHOULD be specific; parent tags SHOULD be categorical
4. Reserved prefixes:
   - `GameplayCue.*` - Cue trigger tags
   - `Cooldown.*` - Cooldown tracking tags
   - `State.*` - Actor state tags
   - `Ability.*` - Ability classification tags
   - `DamageType.*` - Damage classification tags

### 7.2 Tag Container

A Tag Container is a collection of tags associated with an entity.

#### Internal Representation

Implementations SHOULD use an efficient representation:

```typescript
struct TagContainer {
  /** Set of explicit tags */
  ExplicitTags: Set<Tag>;

  /** Cached parent tags (computed from explicit tags) */
  ParentTags: Set<Tag>;

  /** Combined explicit and parent tags */
  AllTags: Set<Tag>;
}
```

#### Operations

```typescript
interface TagContainer {
  /** Adds a tag to the container */
  AddTag(tag: Tag): void;

  /** Removes a tag from the container */
  RemoveTag(tag: Tag): void;

  /** Checks if the container has any tags */
  IsEmpty(): boolean;

  /** Returns the count of explicit tags */
  Count(): number;

  /** Clears all tags */
  Clear(): void;
}
```

### 7.3 Query Operations

| Operation | Semantics | Example |
|-----------|-----------|---------|
| `MatchesTag(T)` | Returns true if T or any child of T is present | Checking for any type of "Stunned" status |
| `MatchesTagExact(T)` | Returns true only if T exactly is present | Specific immunity to "Stunned.Magic" but not "Stunned.Physical" |
| `HasAny(Container)` | Returns true if intersection is non-empty | Spell that affects "Undead" OR "Demon" types |
| `HasAll(Container)` | Returns true if container is a subset | Combo requiring "Chilled" AND "Vulnerable" |
| `HasNone(Container)` | Returns true if intersection is empty | Ability blocked by any "Immunity" tag |

#### Query Examples

```typescript
// Container has: State.Debuff.Stunned.Magic, Status.Burning

container.MatchesTag("State.Debuff.Stunned")     // true (parent match)
container.MatchesTag("State.Debuff.Stunned.Magic") // true (exact match)
container.MatchesTag("State.Debuff.Stunned.Physical") // false

container.MatchesTagExact("State.Debuff.Stunned") // false (not exact)
container.MatchesTagExact("State.Debuff.Stunned.Magic") // true

container.HasAny(["Status.Frozen", "Status.Burning"]) // true
container.HasAll(["State.Debuff.Stunned.Magic", "Status.Burning"]) // true
container.HasAll(["Status.Burning", "Status.Frozen"]) // false
```

### 7.4 Tag Inheritance and Implicit Tags

When a tag is added to a container, all parent tags are implicitly present:

```
Adding: State.Debuff.Stunned.Magic

Implicit parents:
  - State
  - State.Debuff
  - State.Debuff.Stunned
```

This enables hierarchical queries where checking for `State.Debuff` matches any debuff type.

### 7.5 State Representation via Tags

Tags are the primary method for representing Actor states. Instead of boolean flags:

```typescript
// Avoid this pattern
if (actor.isStunned && !actor.isImmune) { ... }

// Use tag queries
if (actor.Tags.MatchesTag("State.Debuff.Stunned") &&
    !actor.Tags.MatchesTag("Status.Immune.Stun")) { ... }
```

This decouples the "How" of a state (animation, logic freeze) from the "What" of the state (the Tag).

### 7.6 Schema Definition

```yaml
TagDefinition:
  Tag: string                     # Full hierarchical tag name
  Description: string             # Human-readable description
  AllowMultiple: boolean          # Can multiple instances exist? (default: false)
  DevComment: string              # Developer notes
```

Tag definitions MAY be collected in a tag registry:

```yaml
$schema: https://raw.githubusercontent.com/jbltx/ugas/v1.0/schemas/gameplay_tag.json
Tags:
  - Tag: "State.Debuff.Stunned"
    Description: "Actor is unable to perform actions"

  - Tag: "State.Debuff.Stunned.Magic"
    Description: "Stun caused by magical effect"

  - Tag: "State.Debuff.Stunned.Physical"
    Description: "Stun caused by physical impact"

  - Tag: "Status.Immune.Stun"
    Description: "Actor is immune to stun effects"
```

---
