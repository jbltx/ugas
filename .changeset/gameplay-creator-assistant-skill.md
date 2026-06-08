---
'ugas': patch
---

[Added] `gameplay-creator-assistant` skill — genre-first, whole-game scaffolding for projects that consume UGAS. It fetches the canonical spec, JSON schemas, and genre template packs from the published docs site (version-pinned), loads a chosen pack's template entities as the base, and scaffolds the four pillars plus a Gameplay Controller into the user's own project; runs guided (interactive Q&A) or one-shot (a genre + brief in, a full schema-valid game definition out), delegating per-entity authoring to `ugas-schema-author` (#29). Also documents how users and AI agents consume a pack — the manual copy-and-extend path and the skill-driven path — in both `genres/README.md` and the published `genres/index.adoc` (#28).
