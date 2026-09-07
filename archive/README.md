# Historical archive

This directory contains the pre-reset record moved on 2026-09-07 from source
commit `d9003255a538fb9635c4ac254dbc0e98b4cb33ca`
(`d900325`, “Correct the R1-to-R3 citation to a within-batch comparison”).
It is evidence, not current guidance. Read root `AGENTS.md`, `BRIEF.md`, and
`ROADMAP.md` for current instructions.

The move preserves original paths under
`archive/2026-09-07-pre-reset/`: root files remain at that mirrored root;
`docs/superpowers/...`, `docs/sdd.md`, and `docs/development/lessons.md` keep
their original relative locations below it. The only change to each archived
Markdown record is its banner.

Default `rg` excludes `archive/` through the repository `.ignore`. Retrieve a
single named record with `rg --no-ignore archive/2026-09-07-pre-reset/...`; do
not preload the archive.

For an original path and line citation, inspect the unchanged source revision:

```console
git show d900325:docs/superpowers/research/2026-09-07-v15-premise-correction.md
git blame d900325 -- docs/superpowers/research/2026-09-07-v15-premise-correction.md
```

The first command reproduces original line numbers. Use the archived copy for
targeted reading and the source revision when a citation must refer to the
pre-reset file path.
