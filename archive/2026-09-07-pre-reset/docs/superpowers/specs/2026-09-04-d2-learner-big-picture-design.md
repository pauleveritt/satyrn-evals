> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# D2 design: The learner's big picture

## Decision

Add one learner page — "What actually happens when an agent works" — to the
**Start here** section, carrying the project's first diagram: a deliberately
small hybrid of the coding agent and the serving layer it drives. Two
diagrams ship in this cycle, in order: the learner big-picture first; the
mapping onto Evals' evidence loop second, developed only after the first is
complete. The page teaches domain orientation in ordinary words before the
reader meets Satyrn's evidence architecture.

The front-door reveal becomes: run this suite (front page, tutorial) → what
actually happened when the command ran (this page) → do real work (guides) →
why it is shaped this way (topics, architecture).

**Naming note.** The phase (D2) collides with a diagram CLI (d2). In prose
and docs the tool is always "the d2 CLI"; the phase is D2.

## Context

D1 (amended 2026-09-04) put the concrete suite and its runnable command on
the front page (`docs/index.md:17`) and the tutorial lands a first verdict.
No page yet gives a learner the domain picture the attempt guides quietly
assume: what a coding agent, an inference server, and a model are, and why
an agent needs tools at all. The D1 design's "explanation after a concrete
result" rule governed Satyrn's *own* architecture, not the reader's prior
domain knowledge; domain orientation belongs before the first run. The page
therefore sits between the tutorial and the guides in **Start here**
(`docs/index.md:83-86`), and the tutorial's closing links
(`docs/tutorials/see-one-verdict.md:56-57`) gain it between themselves and
the evaluate-an-attempt guide.

## Sources (retrieved and verified 2026-09-04)

- Hugging Face Agents Course, `units/en/unit1/what-are-agents.mdx`
  (github.com/huggingface/agents-course): "An Agent is a system that uses an
  AI Model, typically an LLM, as its core reasoning engine. It understands
  natural language, reasons and plans to solve problems, and interacts with
  its environment by gathering information and taking actions."
- Hugging Face Agents Course, `units/en/unit1/tools.mdx`: "The Agent
  interprets the LLM's text-based tool invocation, executes the specified
  tool on the LLM's behalf, and retrieves the results." — the mechanism that
  makes agents and tools necessary. The course's "LLMs can only generate
  text" sentence was **not retrieved verbatim**; the spec cites the
  mechanism above instead of quoting from memory.
- NVIDIA NIM, `docs.nvidia.com/nim/large-language-models/latest/introduction.html`,
  "Architecture at a Glance": the container's Inference Engine "powered by
  vLLM, executes model inference and provides OpenAI-compatible API
  endpoints."
- vLLM, `docs.vllm.ai/en/stable/design/arch_overview`: separate API Server
  Process, Engine Core Process, and GPU Worker Processes — corroborating the
  server/generator split the diagram draws.

Neither source is copied outright: Hugging Face explains agency but folds
the serving layer away; NVIDIA shows serving but as an operations diagram
(proxy, readiness, container internals) too heavy for a first encounter. The
result is a deliberately smaller hybrid, recorded in the next section.

## The hybrid visual model

An **original Satyrn synthesis**, produced for this phase and informed by the
cited references: Hugging Face supplies the agent model (a system using a
model as its reasoning engine, acting on its environment through tools);
NIM and vLLM supply the serving model (a server that loads the model and
provides the request interface, distinct from the model that generates). The
precise diagram composition — containment, the four cards, the unlabeled
task arrow — is maintainer-provided (this session, 2026-09-04). No prior
repository document defines the synthesis (checked: no hit for "hybrid
visual" or "inference server" in `docs/`, `ROADMAP.md`, `BACKLOG.md` on
2026-09-04).

```text
  [ Developer's task ]
          │
          ▼
 ┌───────────────┐        ┌────────────────────┐
 │ coding agent  │◄──────►│  codebase + tools  │
 └───────┬───────┘        └────────────────────┘
         │  request / response
         ▼
 ┌──────────────────────────────┐
 │ inference server             │
 │  ┌───────────────────────┐   │
 │  │ model                 │   │
 │  └───────────────────────┘   │
 └──────────────────────────────┘
```

The load-bearing choice is **containment**: the model sits inside (or
directly beneath) the inference server, never beside it as a peer service.
The server serves; the model generates; the agent acts. Satyrn stays out of
this picture entirely — diagram 2 introduces it as the evidence loop around
a candidate change, not another box competing with the agent.

## Diagram 1 — the learner's picture

Ships first. Four cards, four labels, one unlabeled entry arrow:

| Element | Label (page vocabulary, near-verbatim from the maintainer's sketch) |
| --- | --- |
| coding agent | decides what to ask, uses tools, observes results, and loops |
| inference server | loads the model and provides the request interface |
| model | turns the supplied context into the next tokens |
| codebase + tools | the environment the agent can inspect and change |

"Developer's task" enters at the top; its arrow is unlabeled because it is
the reader's own situation, in the Agents Course's teaching order (objective
→ reason and plan → use tools → observe). The 16–32 GB constrained-laptop
discussion is a hand-drawn note anchored to the inference-server card: *on a
laptop, the server and the model run locally, and RAM bounds which model
fits; on a remote server, they run remotely, and the network takes the RAM's
place. The picture is the same either way.*

**Amendment (2026-09-04, superseded in implementation).** The sentence above —
the task arrow is unlabeled because it is the reader's own situation — was
superseded by the maintainer before landing: the shipped diagram 1 labels the
task→agent edge `prompt` and the agent↔tools edge `tool calls`, and places
"Developer's task" off to the left of a horizontal (`direction: right`)
composition so the picture uses page width. The unlabeled-arrow rationale is
kept here as the original decision, not edited away; the shipped labels and
layout are the decision of record. (Rendered at `d2 --scale 0.5`; flags
recorded in the Justfile `diagrams` recipe.)

## Diagram 2 — how Evals uses those pieces

Developed after diagram 1 is approved complete; the cycle closes with both.
The task (base state + oracle) → **the attempt command — diagram 1's whole
agent loop treated as one opaque executable** → patch and transcript
preserved → offline grade → receipt. Its payoff is the seam: Evals never
looks inside the loop, it grades what the loop delivers. Page section and
diagram are built together, and the page's vocabulary carries over — no new
boxes beyond the five already named plus Evals' own nouns.

## Page and placement

New page `docs/what-actually-happens.md`, in the Start here toctree after
`tutorials/index`, before the guides. Prose beats, in order:

1. You give a task (the developer's task card).
2. The agent: a system that uses a model as its reasoning engine and
   interacts with its environment (HF quote, cited).
3. Why tools exist: a model emits text; something must interpret and act on
   it (HF tools mechanism, cited).
4. The serving distinction: the server loads the model and provides the
   request interface; the model generates (NIM/vLLM, production detail
   dropped).
5. The laptop constraint (the note above, expanded to two sentences).
6. Hand-off: you already ran this loop once — the tutorial's verdict — now
   see what Evals records about it (link to guides; diagram 2's section
   lands here when built).

Genre note: this is explanation living in Start here deliberately — the
section labels name reader jobs, not Diátaxis types. No glossary terms are
added; "inference server", "model", "coding agent", and "tools" are the
reader's domain vocabulary, not Satyrn concepts.

## Pipeline: the d2 CLI with a bake-off gate

Diagrams are authored as `docs/diagrams/*.d2` sources, rendered to committed
SVGs by a `just diagrams` recipe invoking the d2 CLI (`--sketch`, fixed
theme, opaque card fills, fixed padding). **Both source and SVG are
committed**; Sphinx and CI consume only committed SVGs, so the strict build
gains no toolchain and zero runtime JavaScript reaches pages. The recipe
records the d2 CLI version, and regeneration from committed sources must
reproduce the committed SVGs byte-for-byte with that version.

**Bake-off gate.** Diagram 1 is authored first as
`docs/diagrams/agent-big-picture.d2`, rendered to
`docs/diagrams/agent-big-picture.svg`. If `--sketch` plus card styling cannot
reach the lo-fi bar — ink text on opaque cards, pencil-weight strokes,
wireframe plainness — the diagram falls back to a hand-authored SVG committed
at that rendered path (the `.d2` source is then not committed), and the
reason is recorded in the phase's close-out note. The fallback is recorded
either way; the pipeline decision is not reopened per-diagram.

No pi extension is built for this: the agent writes text files and runs one
CLI, which existing tools already do.

## Readability: cards carry their own background

The theme is Furo (`docs/conf.py:36`) with automatic light/dark modes. An
SVG loaded as an image cannot read the page theme, so hardcoded dark text
dies in dark mode and `currentColor`/CSS variables do not reach it. The
decision: every text-bearing element is drawn on an **opaque card** (cream
or white fill, ink text, pencil-weight border) so the diagram carries its
own background in both modes. This is also the Balsamiq lo-fi look the phase
calls for. Theme-coupled colors are a recorded first-try limit, revisitable
in a later phase.

## Review workflow

- `docs/sdd.md`'s "disciplines review holds you to" list gains one bullet:
  *diagrams* — contrast holds on the diagram's own card background, labels
  match the page's vocabulary, no orphaned assets, figures verified in the
  strict build.
- The superpowers review template
  (`~/.pi/agent/git/github.com/obra/superpowers/skills/requesting-code-review/code-reviewer.md`)
  gains a small "Visual assets" check group. This is an implementation-plan
  step sequenced **after** the repo-side work, so the spec defines what
  reviewers check before the template names it. The file is outside this
  repository; the plan records the edit rather than the repo owning it.

## Out of scope

- Animation (CSS/SMIL or otherwise) — not asked for this cycle.
- Any client-side rendering runtime (Mermaid JS, Lit/wired-elements,
  Excalidraw React) — violates the zero-runtime-JavaScript constraint.
- Theme-coupled SVG colors — recorded limit above.
- Operational serving detail (proxy, readiness probes, container internals,
  workers) — deliberately dropped from NIM/vLLM.
- Satyrn boxes in diagram 1.
- More learner pages or diagrams beyond the two.
- V6–V8 operational documentation; D1's exclusions continue unchanged.

## Acceptance

1. The page renders in the strict build and appears in Start here between
   the tutorial and the guides; order is verified in the built HTML.
2. Diagram 1 renders in the built HTML; the page contains no runtime
   JavaScript; the SVG is legible in both Furo modes because it carries its
   own opaque background.
3. The four card labels' wording matches the page prose; the glossary is
   unchanged.
4. Diagram 2 ships with its page section connecting the attempt command to
   diagram 1; the cycle closes only when both diagrams are verified.
5. Every diagram's source and rendered SVG are both committed (a
   hand-authored fallback commits its SVG only); each d2-rendered SVG is
   byte-for-byte reproducible by `just diagrams` with the recorded d2 CLI
   version; the bake-off outcome is recorded.
6. `just lint-docs` (including the whitespace guard), strict
   `sphinx-build -W`, and `git diff --check main...HEAD` all pass.
7. The `docs/sdd.md` discipline bullet exists; the review-template step is
   either landed (with the maintainer's knowledge, as it is a global file)
   or explicitly deferred in the close-out.

## Cross-roadmap gates

| Dependency | Owner | Status | D2 may proceed with | Waits for |
| --- | --- | --- | --- | --- |
| D1 amendment | Evals D1 | complete on this branch (`5e733ef`) | Builds on the amended IA and front page; no further dependency. | — |
| V6 session eval | Evals V6 | **complete** — shipped 2026-09-04 (reconciled on the merge onto main) | No interaction; D2 excluded V6 docs and continues to. | — (met) |
