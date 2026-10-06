---
'ugas': patch
---

[Fixed] The `scene` schema's Regions now match §17.4. A region requires `Name`, `Shape`, `Origin` and `GrantedTags`, takes `Radius`, `HalfExtents`, `Orientation`, `P0`/`P1` and a `Filter` (§17.2 SpatialFilter), and requires the fields its shape needs: `Radius` for a Sphere, `HalfExtents` for a Box, `P0`, `P1` and `Radius` for a Capsule. Unknown region fields are rejected. **Breaking for authored scenes:** a region's `Position` is now `Origin`. The reference checkers also resolve `Filter.RequireTags` and `Filter.ExcludeTags`.
