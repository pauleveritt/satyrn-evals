# Public site — design

**Status:** design for the maintainer's approval, 2026-09-23. No site content is
written until this is approved. Supersedes
`docs/superpowers/specs/2026-09-21-docs-site-design.md`, which specified a
*record* site ("the site is a record, not marketing", a flat ten-page tree).
This design is the pivot to a **public-facing** site. The old spec's build
mechanics (section 7 below) are carried over unchanged; only the audience,
stance, page tree, and content change.

## 1. What this decides

The public site's audience and stance, its naming and identity, its page tree
and navigation, the content of each page, the diagram plan, and what is left as
a placeholder. It does **not** decide deployment (GitHub Pages wiring stays
out of scope until the maintainer asks).

## 2. The pivot

The site stops being the record and becomes the project's public face. The
record does not disappear — it stays in this repository and is linked, not
restated. The negative is still shown; it is simply framed for someone deciding
whether to pay attention, not for someone auditing an instrument.

- **Hosted at** `pauleveritt.github.io/satyrn-evals/` for the next month, moving
  toward a **0.1 release**.
- **Audience, in order:** (1) a Python developer who might use the product;
  (2) a technical reader judging the claim; (3) a future contributor.

## 3. Identity and naming

| term | canonical form |
|---|---|
| mission | **Laptop AI** |
| project | **SatyrnAI** |
| GitHub org | **`satyrn-ai`** |
| site title / H1 | **Satyrn Evals and Satyrn Engine** |
| `site_name` (`zensical.toml`) | Satyrn Evals and Satyrn Engine |

The current repo and URL live under `pauleveritt` (`pauleveritt/satyrn-evals`,
`pauleveritt/satyrn-engine`); after 0.1 the two repos fold into one under
`satyrn-ai`. This is stated on the home page (bottom), not hidden.

## 4. Page tree and navigation

```
Home                                index.md                new — the story
How it works                        how-it-works.md         new — progressive diagram arc
First results                       numbers.md              include docs/numbers.md
Release one — the stated negative   release-one-negative.md include
Measurement                         measurement.md          new
Evals
  About Satyrn Evals                evals-about.md          new
  Architecture                      evals-architecture.md   new
  Using Evals                       use-evals.md            new
  Authoring                         authoring.md            placeholder
Engine
  About Satyrn Engine               engine.md               re-pointed (synced README)
  Architecture                      engine-architecture.md  new
  Using Engine                      engine-usage.md         re-pointed (synced usage)
Satyrn Models                       models.md               placeholder
Lessons                             lessons.md              include docs/lessons.md
Pathologies                         pathologies.md          include docs/pathologies.md
Remediations                        remediations.md         include docs/remediations.md
Contributing                        contributing.md         new
Glossary                            glossary.md             new — the Evals glossary
```

Ordering notes: results (`First results`, `Release one`, `Measurement`) sit
together at the top so the negative is one click from the numbers page, per the
old spec's one hard rule. `Contributing` sits directly above `Glossary`, as the
maintainer specified. `Lessons`/`Pathologies`/`Remediations` are top-level
(cross-cutting, not Evals-specific).

## 5. Home page

Flow, in order:

1. **The story.** The four-quadrillion-tokens trap — "your agent encourages
   your brilliance and starts building … you find it isn't actually solving a
   problem, because you didn't start with evidence." The turn: Satyrn Evals is
   a deep, deliberately over-deep way to find pathologies and experiment with
   remedies. Small models need help; Evals gives confidence you are on track
   and can deliver into an Engine.
2. **The shape.** Evals is the star; Engine is the petri dish where remedies
   are tested. Later Engine becomes a routine-Python tool for Laptop AI. For
   now: a group of people learning to measure and investigate for Laptop AI.
3. **Honest scope.** Engine is not ready to be an everyday addition to your
   agent. In 0.1 it is a good implementer for medium-sized tasks in routine
   Laptop AI Python work.
4. **Join.** Mastodon as the intake (handle **TBD**).
5. **Bottom FYI admonition.** Two repos today under `pauleveritt`; after 0.1
   they fold into one under `satyrn-ai`; the site currently lives at
   `pauleveritt.github.io/satyrn-evals/`.
6. **Close.** Heading "Part of the SatyrnAI project" with a link (**URL TBD**).

The page relies on subordinate pages for detail; it links to `First results`
early and to `How it works`.

## 6. How it works — the progressive diagram arc

One top-level page carrying the whole reveal, from a prompt to an eval verdict,
in three sections. Each section hides the previous section's "out there"
complexity and collapses it to one block. All diagrams are Mermaid fenced
blocks (section 8); no SVG assets.

**Section 1 — How agents work** (simple → complex):

1. prompt → agent → inference server → model.
2. + tools, a loop, and planning.
3. running locally: Pi → oMLX → Ornith 1.5 9B (Pi's tools: read, bash, edit,
   write).

**Section 2 — How the Engine works:**

1. Pi as the coding agent (the server and model collapse to one block).
2. + guards (four: loop breaker, writable-path scope, symbol preservation,
   command bounds — TypeScript checks observing Pi tool calls).
3. + `/implement` at a high level (derive, then deliver).
4. The Engine's pieces: a Python core that runs a **fresh Pi subprocess**
   (headless, guards loaded) in its own isolated worktree.
5. Worktree isolation and the logical pieces inside (adapter, engine core,
   protocol, contract, candidate, receipt).

**Section 3 — How Evals works (logical):** the glossary decomposition — the
harness's jargon pieces (task, cell, arm, harness, launcher, record, census,
guard, …) and how they fit, at the highest level first.

**Boundary with `Architecture`:** "How it works" is conceptual, layered, and
diagrammatic. The Evals **Architecture** page carries the *physical* run — the
launcher loop, the frozen record, two-uid isolation, the grading subprocess —
which is where the maintainer's "starts as a launcher → isolated workspace →
headless Pi subprocess → collect telemetry → analyze" sequence lives.

## 7. What to carry from the old record-site design

These were settled on the scratch build and are not re-decided:

- **Zensical `0.0.63`**, `docs` dependency group, `uv run --group docs zensical build/serve`.
- **`site/`** as `docs_dir`; `_build/` as `site_dir` (git-ignored); `zensical.toml` at root.
- **Include-by-reference**: `pymdownx.snippets` `--8<-- "PATH"` resolves against
  the project root, so canonical files are pulled in with no copy and no drift.
  The **silent missing-include hazard** stands: a typo'd target publishes a hole
  and `--strict` still exits 0, so a default-tier test must assert every include
  target exists.
- **`just docs`** = strict build; it joins `just gates`. Provenance rows for
  every `site/**` file (add `"site"` to `TRACKED_DIRS`).
- **Engine section stays synced** from `satyrn-engine` at the pinned commit
  (`78ab87d`); the About/Usage pages carry the "synced to engine `78ab87d`"
  banner and must not be hand-edited.
- **Deployment** remains out of scope until asked.

## 8. Diagrams: Mermaid

Enable in `zensical.toml`:

```toml
[project.markdown_extensions]
pymdownx.superfences.custom_fences = [
  { name = "mermaid", class = "mermaid", format = "pymdownx.superfences.fence_code_format" },
]
```

Flowchart, sequence, class, and state diagrams are available; the arc above
uses flowcharts and sequence diagrams. Diagrams are version-controlled text in
the page Markdown.

## 9. Placeholders and open items

**Placeholders (write a stub now, fill later):**

- **`Authoring`** — "analyze telemetry → form a hypothesis → start a task → (maybe)
  author a suite." The maintainer expects to un-defer suite-authoring before
  release; the page ships as a stub until then.
- **`Satyrn Models`** — a placeholder naming the Models project and its
  relationship; content to be authored after a maintainer interview.

**TBD (do not guess):**

- Mastodon handle for `join`.
- Laptop AI mission wording and the SatyrnAI site URL for the closing section.

**Recommendations the maintainer has not yet confirmed** (adopted here, listed
so they can be vetoed): an authored **Evals glossary** at the top-level
`Glossary` (the engine glossary stays under Engine); `Release one` and
`Measurement` as top-level pages; `site_name` set to "Satyrn Evals and Satyrn
Engine".

## 10. Out of scope

Deployment, analytics, search tuning, theming beyond the default palette,
versioned docs, any Engine page requiring an unfreeze of `satyrn-engine`. The
site never runs a model and never touches `records/`, `arms/`, `evidence/`
outputs, `src/satyrn_evals/tasks/`, or `/Users/Shared/satyrn-cells`.
