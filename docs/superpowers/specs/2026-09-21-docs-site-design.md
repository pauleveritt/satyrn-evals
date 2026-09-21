# Docs site — design (Zensical)

**Status:** design for the maintainer's approval, 2026-09-21. No site code is
written until this is approved. Drafted at the maintainer's request. This repo
is `satyrn-evals` on `release-one` at `aad78ae`; the product repo
`satyrn-engine` is read-only, frozen at `78ab87d` and pinned by
`arms/engine-ornith15-9b.json`.

## 1. What this decides

Where the rebooted project's documentation site lives, what it contains, how it
is built and gated, and what it must not do. It is Stage 1 of two; Stage 2 is
the minimal skeleton (config, landing page, navigation, the numbers page and
two or three canonical pages wired by inclusion, `just docs` at zero warnings,
provenance rows, a default-tier test, `just gates` exit 0). Stage 2 starts only
after this is approved.

## 2. Audience and the questions the site answers

Three readers, in order of how the maintainer wants them served:

1. **A Python developer who might use the product.** They need the four
   questions answered in order: *what is this*, *does it work*, *how do I use
   it*, and *how was it measured*.
2. **A technical reader judging the claim.** They arrive for the numbers and
   want the pre-registration, the negative, and the instrument gaps beside
   them, not after them.
3. **A future contributor** (today, the maintainer) who needs the repo layout,
   the gates, and the provenance rule.

The site is a **record**, not marketing. The strongest asset is that the
negative and the void night are shown. A site that hid them would be worth
less than the repository it copies.

## 3. Zensical: what the live docs and a scratch build settled

Researched with `ctx7` (`/zensical/docs`) and then confirmed by building a
throwaway project in `$HOME/satyrn-docs-scratch/ztest/` (never in the repo).

- **Version pinned: `0.0.63`** (`uvx zensical --version`). Zensical is written
  in Rust but distributed as a Python wheel; it follows `0.0.x` alpha
  versioning and is moving toward a beta (`0.x`) and then `1.0`. Pin the exact
  version in the lock; expect churn on upgrade.
- **Config file:** `zensical.toml` at the repo root, `[project]` table.
  `site_name` is required; `docs_dir` is a **relative subdirectory** and
  cannot be the root; `site_dir` defaults to `site`. `nav` is declared as a
  TOML array on `[project]`, mixing bare paths and `{ "Title" = "path" }`.
- **Install and run under uv:** add `zensical==0.0.63` to a **dependency
  group** named `docs`, then `uv run --group docs zensical build` and
  `uv run --group docs zensical serve`. The `docs` group is not a runtime
  dependency and does not change `pyproject.toml`'s `dependencies`.
- **Markdown extensions:** enabled under `[project.markdown_extensions]`, the
  Python-Markdown names (`pymdownx.snippets`, `attr_list`, `abbr`, ...). GFM
  pipe tables, headings, fenced code and front matter (`title:`) render with
  no extra extension; verified by building the real `docs/numbers.md` (8
  tables rendered).
- **Including a file from outside `docs_dir` works, by reference.** This is
  the finding the whole design rests on. `pymdownx.snippets` resolves
  `--8<-- "PATH"` **relative to the project root, not `docs_dir`**, and
  refuses to escape the project root. So with `docs_dir = "site"`, a site page
  can write `--8<-- "docs/numbers.md"` and pull the canonical file in at build
  time. There is **no copy and no drift**. The `@use` directive is not needed
  (it renders literally unless a separate directives wheel is installed).
- **Navigation:** `nav` in `zensical.toml`; pages not listed are still built.
  A page's nav title comes from front matter `title:`, which also overrides
  the browser title; the canonical file's own `# H1` still renders in the body.
- **Strict/fail-on-warning:** `zensical build --strict` exits **1** when
  validation issues are found (broken links, bad anchors). `[project.validation]`
  selects the checks. On `0.0.63` the abort prints a Python traceback after
  the clean "N issue found" message; the exit code is still correct.
- **Hazard found, and it is serious:** a `--8<--` target that does **not**
  exist is dropped **silently** — no warning, and `--strict` still exits 0.
  A typo in an include would publish a page with a hole in it. The build alone
  cannot be trusted; a default-tier test must assert every include target
  exists (section 9).

## 4. Where the site lives and how it is built

- **Source: `site/`** at the repo root. `docs/` keeps its existing rules
  (`tools/lint_docs.py` permits only `superpowers`, `superpowers/specs`,
  `superpowers/plans`, `results`, `reviews`), so the site does not go under
  `docs/`. `site/` is a new, flat room of pages; canonical files are pulled
  in by `--8<--`, never copied.
- **Output: `_build/`** at the repo root (`site_dir = "_build"`), added to
  `.gitignore`. `_build` is already in the `SKIP_PARTS` of both
  `tools/lint_docs.py` and `tools/provenance.py`.
- **Config: `zensical.toml`** at the repo root. It is a tracked root `.toml`
  file, so provenance already requires a row for it.
- **Recipes** (Justfile), matching the repo's existing style:

  ```
  docs:
      uv run --group docs zensical build --strict

  docs-serve:
      uv run --group docs zensical serve
  ```

- **`just gates` gains `just docs`.** The strict build is offline, takes well
  under a second on this tree, and is the only check that proves the includes
  resolve and the links are valid. `uv run --group docs` installs the group on
  demand; the CI job (`uv sync --frozen`) needs `--all-groups` or the recipe's
  `--group docs` to see it.

## 5. Page tree

Ten pages now; two held for later. "Include" means the page is a stub with
front matter whose body is `--8<--` of the canonical file, so a number cannot
differ between the repo and the site.

| # | Page | Source | Status |
|---|---|---|---|
| 1 | `index.md` — what Satyrn is; first link is the numbers page | new page | now |
| 2 | `numbers.md` — the release-two result | include `docs/numbers.md` | now |
| 3 | `release-one-negative.md` — the stated negative | include `docs/superpowers/specs/2026-09-15-release-one-outcome.md` | now |
| 4 | `measurement.md` — how the claim was measured; the census, the route proofs, the void night, the instrument gaps | new page, quoting `evidence/2026-09-19-r0-inputs/README.md` and `docs/superpowers/specs/2026-09-17-release-two-engine-design.md` §7a | now |
| 5 | `use-evals.md` — run the harness, grade offline | new page, derived from `README.md` and `STATE.md` | now |
| 6 | `use-engine.md` — `/implement` and the contract | new page, derived from the engine `README.md` and `docs/usage.md`; banner "synced to engine `78ab87d`" | now (later: re-sync when unfrozen) |
| 7 | `lessons.md` — the catalogue | include `docs/lessons.md` | now |
| 8 | `pathologies.md` — the catalogue | include `docs/pathologies.md` | now |
| 9 | `roadmap.md` — phases and status | include `ROADMAP.md` | now |
| 10 | `contributing.md` — layout, gates, provenance, invariants | new page, derived from `AGENTS.md` and `BRIEF.md` | now |
| 11 | `state.md` — the moving project state | include `STATE.md` | later (volatile; link to GitHub meanwhile) |
| 12 | `remediations.md` — the catalogue | include `docs/remediations.md` | later |

The landing page's first link is page 2. The negative (3) and the void night
(in 4) are one click from the top, not buried.

## 6. One site or two

**Recommendation: one site, in `satyrn-evals`, covering both repositories.**

- The record that earns the site lives here: the numbers, the negative, the
  census, the decision ledger. The engine repo holds no result of its own.
- `satyrn-engine` is **frozen at `78ab87d` and pinned by an eval arm**. Putting
  the site there would either freeze the site too or force an unfreeze and
  invalidate the pin. Neither is acceptable before the maintainer unfreezes it.
- The engine's user-facing text (`README.md`, `docs/usage.md`) is stable at the
  frozen commit, so `use-engine.md` can be derived now and re-synced later.
- When the engine is unfrozen and gets its own releases, revisit: either move
  `use-engine.md` into an engine site and link the two, or keep one site and
  include the engine's canonical files by `--8<--` (same repo boundary problem
  does not arise if the site is built from a checkout that has both).

## 7. What to carry from the old Sphinx site

The tag `pre-release-one-2026-09-13` held a Sphinx/MyST site with a Furo theme:
**116 `.md`/`.rst`/`.py` files under `docs/`**, of which 55 were
`docs/current/` pre-run records, 25 were superpowers plans/specs, and the rest
were hand-written pages (`index`, `why`, `usage`, `architecture`, `sdd`,
`glossary`, `what-actually-happens`, `topics/`, `guides/`, `tutorials/`,
`reference/`, `development/`, plus four `.d2`/`.svg` diagrams). It was
configured by `docs/conf.py` with `myst_parser`, `furo`, and a `{toctree}` in
`docs/index.md`.

**Worth carrying — the shape, re-authored, not the files:**

- A "why this exists" page (the old `why.md` names the real problem: a
  plausible change is not a solved task).
- A "what actually happens" walkthrough (task → attempt → preserved patch and
  transcript → offline grade → receipt).
- A trust-boundaries page. `BRIEF.md` invariant 2 still cites the tagged
  `docs/topics/trust-boundaries.md` as the current mitigation and limit, so
  its content is live even though its file is not in this tree.
- A CLI/reference surface for the harness.

**Not worth carrying:** everything under `docs/current/` (55 obsolete pre-run
records), `docs/development/cycles/`, the old `roadmap`/phase docs, and
`architecture.md`/`sdd.md`, which describe the pre-reboot design. Most of the
old site is evidence, not guidance.

**One line must not be carried:** the old `docs/index.md` says Evals "is not a
benchmark or a claims layer" and makes no "A/B publication claims". Release two
is exactly a pre-registered A/B claim (`docs/numbers.md`). Carrying the old
scope sentence would publish a falsehood.

## 8. Single source of truth

The repo's Markdown pages are the record and are cited by commit. The site
presents them, it does not fork them:

- Canonical pages are **included by reference** (`--8<-- "docs/..."`), which
  the scratch build proved works across the `docs_dir` boundary.
- No copy step is needed, so no drift test is needed. If a future Zensical
  version drops project-root snippet resolution, the fallback is a small build
  step that copies canonical files into `site/_canonical/` and a default-tier
  test that digests match their sources; the design does not use it today.
- New pages (1, 4, 5, 6, 10) are written for the site and link to the canonical
  files for their claims; they quote numbers only by including or linking, never
  by restating them.

## 9. Testing

- **`tests/test_docs_site.py` (default tier, no subprocess):** asserts
  `zensical.toml` exists and sets `docs_dir = "site"`; parses every
  `site/**/*.md` for `--8<-- "PATH"` and asserts each target exists in the
  repo (this is the check that catches Zensical's silent missing include);
  asserts `index.md` links the numbers page first; asserts the included
  canonical files listed in section 5 exist. No model, network, or subprocess,
  so the `tests/conftest.py` tripwire permits it.
- **`just docs` (strict build)** is the only check that validates links and
  anchors, and it is a subprocess, so it belongs in `just gates`, not in the
  pytest default tier.
- Because no copies are made, there is no drift test; if copies are ever
  introduced, add one.

## 10. Hygiene for publication — found, not fixed

These are in the canonical files the site would include or link. The maintainer
decides whether to redact, and where (in the canonical file, which changes the
record, or in a site-only note). I did not change any of them.

1. **Absolute local paths.** `STATE.md:180` (`/Users/Shared/satyrn-cells/`,
   `~/satyrn-runs`); `docs/pathologies.md:129` (`/Users/pauleveritt/satyrn-smokes/...`);
   many specs/plans carry `/Users/pauleveritt/...`. Included raw, they publish.
2. **The cell user and local isolation state.** `satyrn-cell`, its home
   `/Users/satyrn-cell`, the sudoers rule, and `/Users/Shared/satyrn-cells`
   appear in `STATE.md`, `docs/superpowers/specs/2026-09-15-release-one-outcome.md`,
   and the release-one design.
3. **Git-ignored ledgers.** `.superpowers/sdd/...` is referenced by
   `docs/superpowers/specs/2026-09-17-release-two-census-night-2-design.md:93`
   and `docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md:13`,
   among others. `.superpowers/` is in `.gitignore`, so those references are
   dead links on a published site.
4. **The README title.** `README.md:1` still reads "Satyrn Evals — release one"
   while the body describes release two.
5. **The numbers page is still a draft.** `docs/numbers.md:1` says "(draft for
   the maintainer's edit)".
6. **Local run and grade roots.** `~/satyrn-runs`, `~/satyrn-comparison-grades`,
   `$HOME/satyrn-route-proof-2-analysis/` in `docs/numbers.md` and
   `evidence/2026-09-19-r0-inputs/README.md`.
7. **Engine-local paths.** The engine's `docs/usage.md` names `.git/satyrn/...`,
   `/path/to/satyrn-engine`, and machine-specific model ids; `use-engine.md`
   must paraphrase these, not paste them.

## 11. Open questions for the maintainer

Each with my recommendation.

1. **One site or two?** Recommend one site here covering both (section 6).
2. **Site source home.** Recommend `site/`, leaving `docs/`'s caps untouched.
   Alternative: add `site` as a sixth permitted `docs/` directory and put the
   site at `docs/site/`, which changes a rule the maintainer wrote. Recommend
   `site/`.
3. **Do the whitespace rules reach `site/`?** **No.** `tools/lint_docs.py`
   globs only `root/*.md` and `docs/**/*.md`, so a trailing space or a blank
   last line in a site page passes today. Recommend extending `_whitespace` to
   also glob `site/**/*.md` (a small instrument change with a test); otherwise
   published pages are held to a lower standard than the record.
4. **Does the strict build join `just gates`?** Recommend yes, via `just docs`
   (section 4). It is offline and sub-second. It does add the `docs` group and
   a Rust wheel to CI, and CI needs the group synced.
5. **Does `site/` get provenance rows?** `tools/provenance.py` tracks `docs/`
   but not `site/`, so a new site file needs no row and `check` will not fail
   for a missing one. The maintainer's stated rule is that every file has a
   row. Recommend adding `"site"` to `TRACKED_DIRS` (with its test) so the rule
   is mechanical, and recording every site file.
6. **`use-engine.md`: derive or link?** Recommend a short derived page with a
   "synced to engine `78ab87d`" banner and a link to the engine repo, rather
   than pasting the frozen `docs/usage.md`. It is the only page that can go
   stale against a frozen source.
7. **`state.md` now or later?** Recommend later, or link `STATE.md` on GitHub.
   It changes most nights and would churn the site's record.
8. **Deployment.** Out of scope for this brief. Recommend GitHub Pages via a
   workflow once the site builds, and no deployment until the maintainer asks.

## 12. Out of scope

Deployment, analytics, search tuning, theming beyond the default palette,
versioned docs, and any Engine page that requires unfreezing `satyrn-engine`.
The site never runs a model, never touches `records/`, `arms/`, `evidence/`
outputs, `src/satyrn_evals/tasks/`, or `/Users/Shared/satyrn-cells`.
