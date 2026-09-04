# D2 — The learner's big picture — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the learner's-big-picture page (with diagram 1: task → agent ↔ codebase/tools, agent → inference server containing the model) after the first verdict, then diagram 2 mapping Evals' evidence loop onto the same picture, as committed SVG assets with zero runtime JavaScript.

**Architecture:** Content lives in MyST pages; diagrams are authored as `docs/diagrams/*.d2` sources and rendered to committed SVGs by a `just diagrams` recipe running the d2 CLI in sketch mode. Sphinx and CI consume only committed SVGs — no toolchain enters the strict build, no JS reaches pages. A bake-off gate decides d2 vs a hand-authored SVG fallback before anything else is committed.

**Tech Stack:** d2 CLI (sketch mode; installed via `brew install d2`), Sphinx `-W` with MyST (`figure` directives), `just`, `uv`.

**Spec:** `docs/superpowers/specs/2026-09-04-d2-learner-big-picture-design.md` (committed `bf5e3e6`). The plan argues from the spec; executors read both.

## Global Constraints

- Worktree root for all commands: `/Users/pauleveritt/projects/pauleveritt/satyrn-evals/.worktrees/docs-diataxis-onboarding`.
- Zero runtime JavaScript on docs pages; zero new glossary terms.
- Readability rule: every text-bearing element sits on an **opaque card** (cream/white fill, ink text) — SVGs must be legible in both Furo modes.
- Fixed vocabulary — the four card labels and their wording are final (spec table): **coding agent** — decides what to ask, uses tools, observes results, and loops; **inference server** — loads the model and provides the request interface; **model** — turns the supplied context into the next tokens; **codebase + tools** — the environment the agent can inspect and change.
- Every diagram's source and rendered SVG are both committed (a hand-authored fallback commits its SVG only); d2-rendered SVGs are byte-for-byte reproducible with the recorded d2 CLI version.
- Satyrn stays out of diagram 1. No animation. No serving-ops detail.
- Plan and spec each ≤ 400 lines (checked by `just lint-docs`).
- Every figure has `:alt:` text. Commands run via `uv run` where the project venv is needed; `git` commands run in the worktree.

## File structure

| Path | Responsibility |
| --- | --- |
| `docs/diagrams/agent-big-picture.d2` + `.svg` | diagram 1: source + committed render |
| `docs/diagrams/evals-evidence-loop.d2` + `.svg` | diagram 2 |
| `docs/what-actually-happens.md` | the learner page (beats in Task 3; diagram-2 section in Task 6) |
| `docs/index.md` | Start here toctree gains the page after `tutorials/index` |
| `docs/tutorials/see-one-verdict.md` | closing links gain the page (line ~56-57) |
| `justfile` | `diagrams` recipe + recorded d2 version |
| `docs/sdd.md` | one diagram-review discipline bullet |
| `ROADMAP.md` | D2 row status transitions; Prior work entry at close-out |
| `~/.pi/agent/git/github.com/obra/superpowers/skills/requesting-code-review/code-reviewer.md` | "Visual assets" checks (Task 7; global file, recorded in the plan's commit) |

---

### Task 1: Install d2 and verify the render loop

**Files:** none yet (tool install).

**Interfaces:** Produces the `d2` binary used by every later task, and knowledge of its current version and theme list.

- [ ] **Step 1: Install**

Run: `brew install d2`
Expected: completes without error.

- [ ] **Step 2: Record the version**

Run: `d2 version`
Expected: a version string. Record it here in the plan's Task 2 commit message and in the `justfile` comment.

- [ ] **Step 3: Verify the render loop with a scratch diagram**

Write `/tmp/d2scratch.d2`:

```d2
vars: {
  d2-config: {
    sketch: true
  }
}
direction: down

"a" -> "b"
```

Run: `d2 --sketch /tmp/d2scratch.d2 /tmp/d2scratch.svg && ls -la /tmp/d2scratch.svg`
Expected: exit 0; an SVG file exists and opens as a hand-drawn-styled two-node diagram (`open /tmp/d2scratch.svg` to eyeball).

- [ ] **Step 4: Check the theme list**

Run: `d2 themes`
Expected: a numbered list of theme names; note the default and a light theme id for the card look (the recipe will pin one).

- [ ] **Step 5: Commit nothing** — the tool is external. Move to Task 2.

---

### Task 2: Bake off diagram 1 — author, render, judge, commit

**Files:**
- Create: `docs/diagrams/agent-big-picture.d2`, `docs/diagrams/agent-big-picture.svg`
- Modify: `justfile` (add `diagrams` recipe)

**Interfaces:** Produces the committed diagram-1 source + render, the `diagrams` recipe, and the recorded bake-off outcome. Later tasks embed the SVG; Task 6 follows the same authoring pattern.

- [ ] **Step 1: Author the starting source**

Create `docs/diagrams/agent-big-picture.d2`:

```d2
vars: {
  d2-config: { sketch: true }
}
direction: down

"Developer's task" -> "coding agent": ""

"coding agent" <-> "codebase + tools"

"coding agent" -> "inference server": "request / response"

"inference server": {
  "model"
}
```

The semantic content is fixed (five nodes, containment of model inside the inference server, the two edges) even if layout styling moves: the four card labels below must appear verbatim as node labels, and the model must render **inside** the server's card, not beside it.

- [ ] **Step 2: Render and inspect**

Run: `mkdir -p docs/diagrams && d2 --sketch --theme <default-light-theme> docs/diagrams/agent-big-picture.d2 docs/diagrams/agent-big-picture.svg && open docs/diagrams/agent-big-picture.svg`

Judge against the **lo-fi bar** (all must hold): ink text is readable on an opaque card in the diagram's own background (no text floating on transparency in a way dark Furo mode would kill — if unsure, toggle the site theme later in Task 3's build check); strokes look hand-drawn/wireframe, not production-polished; the containment (model inside server) is legible; the four labels read at a glance; the layout roughly matches the spec's ASCII.

- [ ] **Step 3: Iterate until the bar is met**

If any criterion fails, adjust the `.d2` (per-card `style.fill`, `style.font-color`, edge labels, node ordering/`direction`, theme id) and re-render. Consult current d2 styling syntax via `d2 --help` and the find-docs skill (`d2` docs) rather than recalling it. Do **not** add ops detail, colors that die without the page theme, or a peer model card.

- [ ] **Step 4: Decide and record — the gate**

- PASS: the recipe below is added, and both files commit.
- FAIL (cannot reach the bar after genuine iteration): delete `agent-big-picture.d2`, hand-write `docs/diagrams/agent-big-picture.svg` with the same five nodes/containment/labels as a lo-fi card SVG, and commit the SVG only. Record the FAIL and its reason in the commit message and in Task 8's close-out.

- [ ] **Step 5: Add the `diagrams` recipe**

Append to `justfile`:

```makefile
# Render committed diagrams from their .d2 sources (d2 CLI, sketch mode).
# Requires: brew install d2. Version pinned by the byte-for-byte check below.
diagrams:
    d2 --sketch --theme <theme-id> docs/diagrams/agent-big-picture.d2 docs/diagrams/agent-big-picture.svg
    d2 --sketch --theme <theme-id> docs/diagrams/evals-evidence-loop.d2 docs/diagrams/evals-evidence-loop.svg
```

Where `<theme-id>` is the id chosen in Step 2. The version is recorded in a comment on the first line and in the commit message.

- [ ] **Step 6: Verify reproducibility**

Run: `just diagrams && git diff --exit-code -- docs/diagrams/`
Expected: re-rendering changes nothing (byte-for-byte with the recorded version).

- [ ] **Step 7: Commit**

```bash
git add justfile docs/diagrams/ ROADMAP.md
# ROADMAP.md: flip the D2 row Status from 'proposed' to 'active' first.
git commit -m "docs: diagram 1 (agent ↔ tools, agent → server → model) — d2 <version>, bake-off PASS|FAIL: <reason>"
```

---

### Task 3: Author the learner page

**Files:**
- Create: `docs/what-actually-happens.md`

**Interfaces:** Consumes `docs/diagrams/agent-big-picture.svg`. Produces the page Task 4 wires into navigation; Task 6 appends its diagram-2 section.

- [ ] **Step 1: Write the page**

Title: `# What actually happens when an agent works`. Opening line orients the reader in ordinary words and ties to what they just did in the tutorial. Then the six beats from the spec's "Page and placement", in order, as prose sections:

1. **You give a task** — the "Developer's task" card; the reader just did this in the tutorial.
2. **The agent** — quote verbatim with citation: "An Agent is a system that uses an AI Model, typically an LLM, as its core reasoning engine. It understands natural language, reasons and plans to solve problems, and interacts with its environment by gathering information and taking actions." — Hugging Face Agents Course, *What are agents?* (`units/en/unit1/what-are-agents.mdx`; link https://huggingface.co/learn/agents-course/unit1/what-are-agents).
3. **Why tools exist** — the model emits text; something must interpret and act. Quote verbatim with citation: "The Agent interprets the LLM's text-based tool invocation, executes the specified tool on the LLM's behalf, and retrieves the results." — same course, *What are tools?* (`units/en/unit1/tools.mdx`).
4. **The serving layer** — the inference server loads the model and provides the request interface; the model generates the next tokens. Ground in the NIM/vLLM distinction without ops detail: "loads models, runs inference, and exposes an OpenAI-compatible API" shape, citing NVIDIA NIM's Architecture at a Glance (https://docs.nvidia.com/nim/large-language-models/latest/introduction.html) and vLLM's architecture overview (https://docs.vllm.ai/en/stable/design/arch_overview) as the source of the split.
5. **On a laptop with 16–32 GB** — the server and the model can run locally, and RAM bounds which model fits; on a remote server they run remotely and the network takes the RAM's place; the picture is the same either way.
6. **You already ran this loop** — the tutorial's verdict was produced by an attempt command that is exactly this whole loop treated as one program; link to the guides. Say explicitly: Evals never looks inside the loop — this sentence is the hook Task 6 builds on.

- [ ] **Step 2: Embed diagram 1**

Place the figure after beat 4 (the reader now has the full vocabulary the cards name). Use a MyST figure with alt text:

```markdown
```{figure} ../diagrams/agent-big-picture.svg
:alt: Developer's task flows down to a coding agent. The coding agent exchanges arrows with a codebase and tools card. A request and response arrow runs from the coding agent down to an inference server card that contains a model card inside it.
```
```

- [ ] **Step 3: Verify the strict build with the figure**

Run: `uv run --group docs sphinx-build -W -b html docs docs/_build/html`
Expected: build succeeds — the SVG is found, the alt text is accepted. Open the built page in dark and light Furo modes and confirm the diagram text is legible in both.

- [ ] **Step 4: Lint and whitespace**

Run: `just lint-docs && git diff --check`
Expected: both clean.

- [ ] **Step 5: Commit**

```bash
git add docs/what-actually-happens.md docs/diagrams/agent-big-picture.svg
git commit -m "docs: learner page — what actually happens when an agent works"
```

---

### Task 4: Wire the page into navigation

**Files:**
- Modify: `docs/index.md` (Start here toctree, ~line 83-86), `docs/tutorials/see-one-verdict.md` (closing links, ~line 56-57)

**Interfaces:** Makes the page reachable in the reveal order; Task 3's page is the payload.

- [ ] **Step 1: Add to the Start here toctree**

In `docs/index.md`, under the Start here caption, change:

```text
why
tutorials/index
```

to:

```text
why
tutorials/index
what-actually-happens
```

- [ ] **Step 2: Extend the tutorial's closing links**

In `docs/tutorials/see-one-verdict.md`, where the page currently links straight to the attempt guide and trust boundaries, add between them a link to the new page — e.g. "To see what actually happened under you — the agent, its tools, and the model behind it — read [what actually happens when an agent works](../what-actually-happens.md)." Keep the existing links.

- [ ] **Step 3: Verify**

Run: `uv run --group docs sphinx-build -W -b html docs docs/_build/html`
Expected: succeeds; the new page appears in Start here in the built HTML, between the tutorial and the guides.

- [ ] **Step 4: Commit**

```bash
git add docs/index.md docs/tutorials/see-one-verdict.md
git commit -m "docs: wire learner page into Start here and tutorial links"
```

---

### Task 5: Review-workflow discipline in the repo

**Files:**
- Modify: `docs/sdd.md`

- [ ] **Step 1: Add the discipline bullet**

In `docs/sdd.md`, under "The disciplines review holds you to:", append one bullet:

```markdown
- **Diagrams** — contrast holds on the diagram's own card background (never
  on the page theme), card labels match the page's vocabulary, no orphaned
  asset files, and every figure is verified in the strict build with alt
  text present.
```

- [ ] **Step 2: Verify**

Run: `just lint-docs && uv run --group docs sphinx-build -W -b html docs docs/_build/html`
Expected: both clean.

- [ ] **Step 3: Commit**

```bash
git add docs/sdd.md
git commit -m "docs: sdd discipline — diagrams reviewed against card contrast, vocabulary, assets"
```

---

### Task 6: Diagram 2 and its page section

**Files:**
- Create: `docs/diagrams/evals-evidence-loop.d2` + `.svg`
- Modify: `docs/what-actually-happens.md` (append the diagram-2 section after beat 6)

**Interfaces:** Consumes diagram 1's authoring pattern and the page's beat-6 hook. Closes the cycle.

- [ ] **Step 1: Author diagram 2's source**

The picture reuses diagram 1's coding-agent card and adds Evals' nouns. Semantic content (fixed): a chain task → **the attempt command** (drawn as the diagram-1 agent card, labeled as the opaque boundary) → saved patch + transcript → offline grade → receipt. The claim the picture makes: Evals never peers inside the agent loop — it preserves and grades what the loop delivers. Author `docs/diagrams/evals-evidence-loop.d2` in the same sketch/card style, containing the coding-agent card from diagram 1 as one opaque node.

- [ ] **Step 2: Render and judge**

Run: `just diagrams && open docs/diagrams/evals-evidence-loop.svg`
Expected: the same lo-fi bar holds; the reused agent card is visually the same object as diagram 1's (same fill, shape, label wording "coding agent").

- [ ] **Step 3: Append the page section**

In `docs/what-actually-happens.md`, after beat 6, add a section titled e.g. `## What Evals records` that: names the five elements of diagram 2 in page vocabulary; states the seam in one sentence (the attempt command is diagram 1's whole loop treated as an opaque executable); embeds the figure with alt text; and links to the guides (`guides/evaluate-an-attempt.md`) as the next step.

- [ ] **Step 4: Verify**

Run: `just lint-docs && uv run --group docs sphinx-build -W -b html docs docs/_build/html && git diff --exit-code -- docs/diagrams/`
Expected: lint clean, build succeeds, re-render reproduces committed SVGs.

- [ ] **Step 5: Commit**

```bash
git add docs/diagrams/ docs/what-actually-happens.md
git commit -m "docs: diagram 2 — Evals records the loop's output, not its inside"
```

---

### Task 7: Review template (global file, outside the repo)

**Files:**
- Modify: `~/.pi/agent/git/github.com/obra/superpowers/skills/requesting-code-review/code-reviewer.md` (this path is outside the repository; the change is recorded here and in the commit message so the repo does not silently depend on it)

- [ ] **Step 1: Add the visual-assets check group**

Read the file first (its current structure: Description, then review areas, then Example Output with Strengths/Issues/Recommendations/Assessment). Add a short "Visual assets" review instruction near the other review-area instructions, requiring the reviewer to check: diagram text is legible on the diagram's own background in both light and dark site themes; card labels match the page's vocabulary; every figure has alt text; no orphaned asset files. Keep it to a few lines.

- [ ] **Step 2: Confirm with the maintainer**

The file is shared tooling; before committing anything in this repo that references it, state the change in the session so the maintainer knows the template now asks reviewers about visual assets. (No repo commit can carry this file.)

- [ ] **Step 3: Commit (repo side records the step)**

```bash
git add docs/superpowers/plans/2026-09-04-d2-learner-big-picture.md
git commit -m "docs: plan D2 — review-template visual-assets step (code-reviewer.md, global)"
```

---

### Task 8: Close-out — roadmap, bake-off record, full verification

**Files:**
- Modify: `ROADMAP.md`, this plan

**Interfaces:** Ends the cycle; every earlier task's deliverable is verified here as a whole.

- [ ] **Step 1: Flip the D2 row to complete**

The D2 row's Status went `proposed` → `active` when Task 2 committed diagram 1. Now set it to `complete` with a one-line summary of the delivered IA, and add a Prior work bullet (pattern: V5d, D1 entries) recording the bake-off outcome (PASS d2 `<version>`, or FAIL-hand-authored with the reason).

- [ ] **Step 2: Record the bake-off outcome in the plan**

Add a short "Bake-off outcome" note at the top of Task 2 or in the close-out with the verdict and reason (one or two lines).

- [ ] **Step 3: Full verification battery**

Run, in order:

```bash
just lint-docs
uv run --group docs sphinx-build -W -b html docs docs/_build/html
git diff --check main...HEAD
uv run pytest -q
just diagrams && git diff --exit-code -- docs/diagrams/
```

Expected: lint clean; strict build succeeds; diff check clean; tests pass; diagrams reproduce byte-for-byte. Navigate the built Start here section and confirm: front page → tutorial → learner page (both figures legible in light and dark Furo modes) → guides.

- [ ] **Step 4: Commit**

```bash
git add ROADMAP.md docs/superpowers/plans/2026-09-04-d2-learner-big-picture.md
git commit -m "docs: close D2 — learner big picture with two diagrams (d2 <version>, bake-off <OUTCOME>)"
```
