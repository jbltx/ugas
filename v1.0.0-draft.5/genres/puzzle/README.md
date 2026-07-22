# UGAS Genre Pack: Puzzle

> Tile-matching puzzle: a score resource and a move economy, a swap/match/cascade loop, and a
> match-scoring pipeline that multiplies a base match by a combo factor and a chain factor.

This pack is the copy-and-extend companion to the **Puzzle (2048-style) case study** in the core
spec (Section 16.4). It ships the matching Attributes, Tags, Abilities, and Effects as
schema-conformant entities, plus a worked board example. Match-3 is the concrete seed; the scoring
factors, move economy, and cascade chain generalize across the wider puzzle family.

## What's in this pack

| File | Purpose |
|------|---------|
| `spec.adoc` | Additional Puzzle specification — extends, never replaces, the core spec |
| `entities/attribute_set.yaml` | `PuzzleBoardSet`: score, move/time economy, combo & chain multipliers, telemetry |
| `entities/tag_registry.yaml` | Puzzle tags: board states, level phases, tile types, powerups, ability types |
| `entities/effect_match_clear.yaml` | Instant; runs `ExecCalc_MatchScore` to bank the match product into `Score` |
| `entities/effect_combo_build.yaml` | `HasDuration` `+1` `ComboMultiplier`, refreshing its window each match (combo factor) |
| `entities/effect_cascade_chain.yaml` | Instant `+1` `ChainLength` per cascade depth (chain factor) |
| `entities/effect_powerup_bomb.yaml` | Instant board-clear bonus, `AttributeBased` on `BaseMatchValue` |
| `entities/effect_time_bonus.yaml` | Instant `+TimeRemaining` top-up for timed modes |
| `entities/effect_reset_chain.yaml` | Instant `Override` of `ChainLength` to `0` once the board settles |
| `entities/ability_swap_tiles.yaml` | `GA_SwapTiles`: the core move; costs `1` move, applies `GE_MatchClear` |
| `entities/ability_activate_powerup.yaml` | `GA_ActivatePowerup`: detonate a special tile (`GE_PowerupBomb`) |
| `entities/ability_use_hint.yaml` | `GA_UseHint`: free assist on a cooldown |
| `entities/input_actions.yaml` | `SelectTile`, `ActivatePowerup`, `UseHint` actions |
| `entities/input_action_set_board.yaml` | `BoardControls`: the input context active during a live level |
| `entities/input_mapping_board_touch.yaml` | Touch bindings (tap/swipe/double-tap) — the primary scheme |
| `entities/input_mapping_board_pc.yaml` | Mouse + keyboard bindings mirroring the touch scheme |
| `entities/gameplay_controller.yaml` | Worked example: a board mid-cascade with a ×3 combo showing the scoring math |

## How to use

1. Read `spec.adoc` for the genre-specific design (especially the match-scoring pipeline).
2. Copy the entity files in `entities/` into your project and adapt them.
3. They validate against the core `schemas/*.yaml`, so AI agents (e.g. the
   `ugas-schema-author` skill) can load and extend them directly.
4. Implement the `ExecCalc_MatchScore` engine seam (the per-match product); everything else is data.
5. Run `python scripts/validate_schema_examples.py` after changes.

## Published spec

<!-- Link to the built HTML once published, e.g. v<version>/genres/puzzle/index.html -->
