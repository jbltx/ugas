## 18. Scene Composition

### 18.1 Overview

The pillars so far define gameplay *entities* — attributes (§5), tags (§7), effects (§9), abilities (§8), controllers (§4) — and the world model they act in (§17). They do not define how those entities are *instanced into a running world*: which controllers exist, where they stand, and with what initial state. That is the **content layer**, and it is the seam between an authored gameplay definition and a playable level.

Scene Composition is a portable, engine-agnostic description of that content. A **Scene** declares a set of **Placements** (controller instances at world poses, with startup state), the **Regions** (§17.4) that govern them, and the **Spawn Points** used for dynamic spawning. It composes from the existing pillars rather than introducing new gameplay mechanics: a placement references a §4 controller config, its startup state is expressed as §7 tags and §9 effects, its regions are §17.4 zones, and its runtime state persists through §14.

<div class="note">

Scene Composition is deliberately **not** a level-geometry or rendering format. It carries no meshes, materials, lighting, navigation meshes, or audio — those remain the engine’s scene representation. It is the **gameplay overlay**: the minimal, portable statement of *what gameplay entities exist, where, and in what starting state*, which an engine binding reifies against its own scene. An engine MAY store the overlay inside its native scene format; the contract is the model below, not a file format.

</div>

### 18.2 Placements

A **Placement** instantiates one `GameplayControllerConfig` (§4) at a world pose with optional startup overrides.

``` typescript
struct Placement {
  /** The GameplayControllerConfig to instantiate (§4), by name. */
  Controller: string;

  /** Stable identity for this instance — the key for persistence (§14) and cross-references. */
  InstanceId?: string;

  /** Spawn pose. The Position becomes the instance's spatial anchor (§17.1). */
  Position?: Vector3;
  Rotation?: Quaternion;

  /** Tags granted to the instance on spawn (§7) — team, role, difficulty band, etc. */
  StartupTags?: GameplayTag[];

  /** Effects applied to the instance on spawn (§9) — starting buffs, passives, loadout. */
  StartupEffects?: string[];

  /** Base-value overrides applied after the controller's defaults (§5) — e.g. an elite's Health. */
  AttributeOverrides?: Map<string, number>;

  /** Whether the instance spawns active; false authors a dormant/pre-placed entity. Default true. */
  Enabled?: boolean;
}
```

Normative:

1.  **Instancing.** Loading a Placement MUST create a Gameplay Controller from the named config (§4), fully initialised (its attribute sets, granted abilities, and startup/active effects from the config applied) exactly as if spawned at runtime.

2.  **Anchor.** If a `Position` is given, it becomes the instance’s spatial anchor (§17.1); the instance is registered with the spatial system (§17.2) so queries, areas, zones, and perception see it. A Placement without a `Position` is a non-spatial controller (§17.1) — valid for pure logic actors.

3.  **Startup state order.** After base initialisation, apply in this order: `AttributeOverrides` (base values, §5) → `StartupTags` (§7) → `StartupEffects` (§9). This mirrors the persistence restore order (§14.4) so a placed instance and a restored instance reach the same state.

4.  **Identity.** `InstanceId`, when present, MUST be unique within the loaded world and is the key under which §14 captures and restores this instance. Two Placements with the same `InstanceId` are an authoring error.

### 18.3 Scenes

A **Scene** is the composable, loadable unit of content.

``` typescript
struct Scene {
  /** Unique scene identifier. */
  Name: string;

  /** Parent scenes this one composes on top of, additively (§18.5). */
  Extends?: string[];

  /** Controller instances placed into the world. */
  Placements: Placement[];

  /** Standing zones active while the scene is loaded (§17.4). */
  Regions?: Region[];

  /** Named poses for dynamic spawning at runtime (§18.4). */
  SpawnPoints?: SpawnPoint[];
}
```

#### Load semantics (normative)

Loading a Scene MUST follow this order so that dependencies are satisfied as each step runs:

1.  **Regions first.** Instantiate every `Region` (§17.4) and begin evaluating occupancy. Establishing zones before placements means an instance spawned inside a zone receives its granted tags on its first spatial evaluation, not a frame late.

2.  **Placements next.** Instantiate each Placement in declaration order (§18.2). Declaration order is the tie-break for any order-dependent effect, so scene load is reproducible (§18.6).

3.  **Spawn points last.** Register each `SpawnPoint` (§18.4); they instantiate nothing at load.

Unloading a Scene reverses this: despawn placed instances (releasing their spatial registration and tags), then tear down regions. An instance’s persistable state MAY be captured (§14) before unload so a later reload resumes it.

### 18.4 Spawn Points

A **Spawn Point** is a named pose the running game spawns dynamic entities at — respawns, reinforcement waves, summoned minions, loot. Unlike a Placement it instantiates nothing at load; it is a labelled location gameplay selects at runtime.

``` typescript
struct SpawnPoint {
  /** Spawn point identifier, referenced by spawning logic. */
  Name: string;

  Position: Vector3;
  Rotation?: Quaternion;

  /** Classification tags for selection — team, wave, encounter (§7). */
  Tags?: GameplayTag[];
}
```

Selection is a §17.2 concern: "the nearest friendly spawn to the player" or "a random spawn tagged \`Spawn.Wave.2\`" is an ordinary spatial/tag query over the registered spawn points. The dynamic entity a spawn produces is itself a Placement (§18.2) created at runtime rather than at load.

### 18.5 Composition and Streaming

**Composition.** A Scene MAY `Extends` one or more parent scenes; the result is the additive union of their placements, regions, and spawn points — a base level plus an encounter overlay, or a shared arena plus a mode-specific ruleset. Merge is additive and order-preserving (parents first, in listed order, then this scene). An `InstanceId` or region `Name` that collides across composed scenes is an authoring error; an implementation MUST report it rather than silently pick a winner.

**Streaming.** Large worlds load and unload scenes as chunks. What is *active* is governed by the spatial partition (§17.6) and the ambient budget (§10.6); what *persists* across a load/unload cycle is governed by §14 — an instance keyed by `InstanceId` resumes its captured state when its chunk reloads. Region and perception tags are derived state (§17.4, §17.5): they are re-evaluated on load, never streamed.

### 18.6 Determinism and Persistence

Scene load MUST be deterministic: placements instantiate in declaration order (§18.3) and any randomised startup draws from the seeded stream of §9.5 / §13.8.1, so a given scene loads identically across machines and across a save/reload. This is what lets a replay (§14) or a predicted spawn (§13.8) reach the same world state the authoritative load produced.

Persistence composes directly: a loaded scene’s runtime state is the set of per-instance §14 snapshots keyed by `InstanceId`. Capturing the scene captures each instance’s base values, active effects, and granted abilities; restoring re-instantiates the scene, then applies each snapshot. Derived state — current values, region-granted tags (§17.4), perception (§17.5) — is recomputed, never serialised (§14.2), so a scene reloaded from a save is indistinguishable from one freshly composed and advanced to the same point.
