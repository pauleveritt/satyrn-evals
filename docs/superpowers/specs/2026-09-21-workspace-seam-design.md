# Workspace and seam — design (engine fetch, docs sync)

**Status:** design for the maintainer's approval, 2026-09-21, drafted at his
request. This is sub-project 1 of a phase that also covers the collaborator
experience and the promotion of the reboot to `main`; those two get their own
specs later. This repo is `satyrn-evals` on `release-one` at `17b0227`. The
product repo `satyrn-engine` is read-only here, frozen at `78ab87d` and pinned
by `arms/engine-ornith15-9b.json`.

## 1. What this decides

Where the engine checkout lives for a collaborator, how it is obtained, and how
a single documentation site presents both repositories without a submodule and
without the engine entering the evals project root. It makes **no harness
behavior change**: `launch`, `attempt`, the isolation profiles, and the arm
pins are untouched.

## 2. Goal and success criterion

A collaborator with a clone of `satyrn-evals` can get the exact engine the
comparison used with one command, and build a single site that presents both
repositories offline from a committed, drift-tested copy.

Done when, on a plain clone:

- `just fetch-engine` obtains `satyrn-engine` at the arm's pinned commit and
  prints `SATYRN_ENGINE_REPO`;
- `just docs` builds the single site with zero warnings, with no engine
  checkout present;
- `just gates` exits 0 with no engine checkout present;
- the site's engine pages are the engine's own bytes at the pin, and a
  default-tier test fails if they ever differ.

The published numbers and the harness are unchanged; the only pin this
sub-project reads is the arm's existing `engine_commit`.

## 3. What the live tooling settled

Confirmed by building a throwaway Zensical `0.0.63` project in
`$HOME/satyrn-docs-scratch/` (never in the repo):

- `pymdownx.snippets` resolves `--8<-- "PATH"` from the **project root** and
  refuses to escape it, so a sibling checkout cannot be included in place.
- `exclude_docs` did **not** keep a synced file out of the page tree: a
  `site/_engine/usage.md` was still built as `_engine/usage/index.html`. A
  synced copy must therefore live **outside `docs_dir`**.
- A root directory outside `docs_dir` is not a page and is included fine
  (the same rule that lets `site/numbers.md` include `docs/numbers.md`).
- `lint_docs` globs only `*.md`, `docs/**/*.md`, and `site/**/*.md`, so a root
  `_engine/` is not whitespace-checked — which is correct for verbatim bytes.

## 4. The workspace: fetch the arm's pin

The engine stays a **sibling checkout**. `just fetch-engine` wraps a new
`satyrn-evals fetch-engine` subcommand that:

1. reads `pins.engine_commit` from `arms/engine-ornith15-9b.json` (reusing
   `satyrn_evals.arms`);
2. clones `https://github.com/pauleveritt/satyrn-engine.git` into
   `$SATYRN_ENGINE_REPO` when set, else `../satyrn-engine` relative to the
   evals root, and checks out the pinned commit detached;
3. is idempotent: an existing checkout already at the pin is left alone; one
   at another commit is refused with the two shas named;
4. prints the path and the `export SATYRN_ENGINE_REPO=…` line.

A sibling, not `.engine/` inside the evals tree, because an in-tree clone would
be collected by pytest, ruff, and pyrefly unless four configs grew excludes.
The fetch is shallow: `git init`, `git remote add`, `git fetch --depth 1 origin
<sha>`, `git checkout FETCH_HEAD`, so it pulls one commit, not the history.
The remote is `$SATYRN_ENGINE_URL` when set, else the URL above.

## 5. The sync: a committed, digest-tested copy

`just sync-engine` wraps a `satyrn-evals sync-engine` subcommand that reads
`$SATYRN_ENGINE_REPO` (default `../satyrn-engine`), refuses unless its `HEAD`
equals the arm's pin, copies three files into a committed root directory, and
writes a manifest:

```
_engine/README.md
_engine/usage.md
_engine/glossary.md
_engine/manifest.json
```

`manifest.json`:

```json
{
  "engine_commit": "78ab87dbab3381dd585986c43fd49e6e4974f6b6",
  "source_repository": "https://github.com/pauleveritt/satyrn-engine.git",
  "files": {
    "README.md": {"source": "README.md", "sha256": "..."},
    "usage.md": {"source": "docs/usage.md", "sha256": "..."},
    "glossary.md": {"source": "docs/glossary.md", "sha256": "..."}
  }
}
```

The three source paths are fixed; the flattening (`docs/usage.md` to
`usage.md`) is deliberate, so the site's includes are short and stable.
`_engine/` is committed and is the record of what the site shows; the sync is
the only thing that writes it, and it writes the `PROVENANCE.md` rows for its
outputs (section 8) so a sync is complete on its own.

## 6. Tests

Default tier (`tests/test_engine_sync.py`, no subprocess):

- the manifest's `engine_commit` equals the committed arm's `engine_commit`;
- every manifest file exists at `_engine/<name>` and its sha256 matches;
- every `--8<-- "_engine/…"` target in `site/**/*.md` is named in the
  manifest, and every manifest file is included by some page;
- each engine page's banner commit equals the manifest's commit;
- pure helpers over a fixture tree: `build_manifest` hashes what it is given,
  and `check_manifest` names a file whose bytes changed, a file that is
  missing, and a manifest whose commit is not the arm's.

Integration tier (`tests/integration/test_engine_sync.py`, marked): when a
checkout at the pin is present (`SATYRN_ENGINE_REPO` or `../satyrn-engine`),
re-sync into a temporary directory and compare digests to `_engine/`; skipped
with the reason when no checkout is present.

The existing `tests/test_docs_site.py` already asserts every include target
exists against the repo root, so `_engine/…` targets are covered there too.

## 7. The site's engine section

Three pages, each front matter, a one-line banner, and one include:

| page | include | nav title |
|---|---|---|
| `site/engine.md` | `_engine/README.md` | The engine |
| `site/engine-usage.md` | `_engine/usage.md` | Using the engine |
| `site/engine-glossary.md` | `_engine/glossary.md` | Glossary |

The banner is `Synced from satyrn-engine <commit>; do not edit here.` The
commit in each banner is checked against the manifest, so the banner cannot
drift. The pages link back to the engine repository and to the numbers page.
The record pages are unchanged.

## 8. Provenance and gates

`_engine/` files come from another repository, and `provenance.py` today can
only say `pre-release-one-2026-09-13 @ <sha>` or `created in release-one`.
The seam adds a general source form:

```
uv run python tools/provenance.py record --source "satyrn-engine @ 78ab87d…" _engine/README.md …
```

`record --source` replaces any existing rows for the given paths and appends
one per path, so re-running the sync is idempotent and never doubles a row.
`provenance.py`'s `TRACKED_DIRS` gains `_engine`, so `check` enforces the rows.
`sync-engine` calls the same function, so the rows appear without a second
command. Tests: a source row is written verbatim; recording twice leaves one
row per path; `check` names an `_engine/` file without a row.

`just gates` is unchanged in shape: `just docs` builds the committed copy
offline, and the new default-tier test runs under `just pytest`. Nothing in
gates fetches or needs the engine. CI needs no change.

## 9. Evidence and harness

This sub-project makes no claim and names no Engine target, ceiling task, or
budget, so the "Evidence has a harness" rule has nothing to re-open. It adds
tools and a documentation copy; it changes no launcher, adapter, isolation, or
arm behavior. The single pin it reads is `arms/engine-ornith15-9b.json`'s
`engine_commit`, which is the same value the harness already enforces through
`cell_engine.arm_export_problems`; the site and the comparison therefore cannot
disagree about which engine they describe.

## 10. Explicitly out of scope

- The collaborator quickstart and the rest of the onboarding work
  (sub-project 2).
- Any change to `launch`, `attempt`, the isolation profiles, or the arms.
- Unfreezing `satyrn-engine` or moving it into this repository.
- Promoting `release-one` to `main`, and the deep review (sub-project 3).
- Deployment of the site.

## 11. Open items and risks

1. **Vendoring is the least-bad alternative.** The engine's text is copied, not
   included, because the boundary cannot be crossed. The digest test and the
   arm-derived pin are what keep the copy honest; if the maintainer later
   prefers no copy, the fallback is link-only, which loses the verbatim text.
2. **The shallow fetch of a specific sha** relies on the server allowing
   `git fetch --depth 1 origin <sha>`; GitHub does. If it ever fails, the
   fallback is a full clone then checkout, with the same refusal rules.
3. **`_engine/` is inside the repo but outside the record's rules.** It is not
   whitespace-checked and not in `docs/`; its integrity is the manifest test,
   not `lint_docs`. This is intentional for verbatim bytes.
4. **Re-pin procedure.** When the engine advances, `just sync-engine` refuses
   until the arm is re-pinned and re-exported; the spec does not automate the
   re-pin, which stays an attended decision.
5. **Site build without the engine.** Because the copy is committed, `just
   docs` never needs the engine; `just fetch-engine` is only for running evals
   or refreshing the copy.
