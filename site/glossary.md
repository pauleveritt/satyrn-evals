---
title: Glossary
---

# Glossary

The Evals harness's vocabulary, alphabetical. The engine's terms live in its
own [glossary](engine-glossary.md). Most entries name the file or ledger entry
(`evidence/2026-09-15-release-one-decision-ledger.md`, "the ledger") that
holds the meaning.

**admitted**

A cell with refusals 0 and reaches 0 (`confinement.Finding.admitted`). Only
admitted cells enter a deciding denominator; a hidden basename reached inside
the cell's own worktree is reported and does not un-admit (C3 D5).

**allowlist** (class)

A passing state exists but a file outside `source_paths` voids the patch
(census design §7). Never read from a replayed patch in new work (ledger
2026-10-04, ruling 1).

**ambiguity** (class)

The prompt admits a reading the hidden suite rejects (census design §7). A
task defect: the task is fixed or leaves the set, and nothing is claimed
against it.

**arm**

One measured configuration: the attempt command, the model, and the tool
surface. Baseline and Engine are the two arms. An Engine arm file also pins a
satyrn-engine commit and seven file digests, and launch refuses a checkout
whose HEAD differs from the pin.

**attempt command**

The executable the harness runs in a cell to do the work: Pi with no product
extensions plus the eval's confinement extension for Baseline, the Engine's
`/implement` for the Engine arm (unisolated-harness design §3, C1).

**backstop**

The wall-clock limit on a cell's command, 4,800 s in the C3 records. A cell
the backstop ends is a named wall-clock cut; it stands and is not re-run
(ledger 2026-10-03, "C3 nights A and B ran").

**budget**

The token and turn limits that stop a cell, and the wall-clock backstop. A
cell that runs out of budget is graded, not discarded. The run budget
(48,000 output tokens / 72 turns) and the declared line (32,000 / 48) are
different numbers; see **line**.

**budget** (class)

A pass state is reached late and the 32k line falls before it (census design
§7).

**budget-shaped**

A task with at least 3 admitted cells of which at least half are not a pass
at the line (C4 pre-registration §5). Every other deciding task is
**floor**.

**C0–C4** (Phase C)

The steps that re-derive isolated evidence on the confinement harness: C0
marks it unconfirmed, C1 re-qualifies, C2 re-reads the census process
classes, C3 re-runs the census, C4 re-derives the finishing counterfactual
(`ROADMAP.md`, "Next"). All five were done by 2026-10-03.

**capability** (class)

The cell has the facts, spends its budget and never reaches a pass state
(census design §7).

**cell**

One attempt: a task run once, in its own attempt worktree under the
confinement extension, under one arm (ledger 2026-10-02, "C0").

**ceiling set**

The tasks a comparison may claim on. Ruled at the R0 sitting on 2026-10-04:
run-record-gate and preflight-quiet.

**census**

The classified set of Baseline cells, eight class columns by turn, read
before any Engine remedy is built, to see where an arm actually fails. The
current one is C3: 36 cells under confinement, all admitted
(`evidence/2026-10-03-c3-census/`).

**class column**

One of eight per-cell flags (information, ambiguity, capability, budget,
finishing, runaway, hunting, allowlist), signed by the maintainer. The
primary class is the one whose removal would have changed the verdict at
32k, cited by turn; "pass" means no primary (census design §7).

**controller**

The attended agent session that dispatches and reviews agents, launches
records at the maintainer's word, and writes the ledger. Pushes are the
maintainer's.

**D-numbered decision**

A numbered open decision in a plan (D1, D2, ...) with lettered options and a
recommendation. The maintainer rules it, and the ledger records the ruling
with the evidence it rests on.

**deciding**

A record or cell whose result can support a claim: purposes admission,
route-proof and campaign (`run_record.DECIDING_PURPOSES`), with the rule
pre-registered.

**development**

A record purpose with no task outcome in its decision rule. Development cells
are read beside, never pooled, and never support a claim (ledger 2026-10-04,
"Engine pin moved").

**EB0–EB3** (Phase EB)

The engine-budget phase: EB0 development cells on floor tasks, EB1 an offline
read of them, EB2 remedies each with an offline estimate, EB3 a
pre-registered floor read (engine-budget design §3, branch
`worktree-engine-budget`).

**Engine terms**

Guards, the finish nudge, the scope guard, the red-stop gate, edit parity and
the Engine's confinement root are Engine vocabulary, defined in the
[engine glossary](engine-glossary.md).

**fidelity note**

A `fidelity:` reason on a classifier row whose replay skipped a bash writer,
so the replayed tree may differ from the cell's. C4's rule withheld such rows
as unmeasured (C3 census page, "Replay artifact on `allowlist`").

**finishing** (class)

A pass state is reached within 32k and the cell keeps working past the line
(census design §7).

**flagged**

A cell with a refusal or a reach. It is reported, is not a pass, and stays
outside the denominator (unisolated-harness design §3, C3).

**floor**

A deciding task that is not budget-shaped; it is in scope for harm (C4
pre-registration §5).

**frozen**

Fixed before any cell runs: a run record is committed first, and a sitting
runs from a named commit recorded in the ledger as "C3 frozen `<sha>`".

**go, verify, not-the-lever**

C4's three verdicts. Go needs at least 2 qualifying tasks, floor harm under 2
and no floor task insufficient; verify needs at least one qualifying task;
not-the-lever means no budget-shaped task has net 1 or more (C4
pre-registration §5). C4 read verify.

**grade-line**

`satyrn-evals grade-line` (`src/satyrn_evals/line_grade.py`), the at-line
reader: it grades each finished cell's `line.diff` at the crossing on both
arms and uses the harness verdict for a cell that never crossed. It reports
an `unavailable` cell apart from the pass denominator.

**hunting** (class)

A root search or a bounded command precedes the failure (census design §7).
Mechanical under C2's rule, no override.

**information** (class)

The prompt omits a fact the hidden suite requires, and no cell finds it
(census design §7). A task defect, never claimed against.

**instrument-only piece**

A piece of work that changes how things are measured and runs no
measurement. Two consecutive instrument-only pieces stop the loop
(`AGENTS.md`).

**insufficient**

A task with more than 1 unmeasured admitted cell, or fewer than 3 admitted
cells (C4 pre-registration §5).

**isolation** (retired)

The two-uid `satyrn-cell` and `bwrap` profiles. Retired at `35c298d` for
confinement; the user and its sudoers rule were removed on 2026-10-03.

**launcher**

The `satyrn-evals launch` command that runs a frozen record's cells, arms
interleaved, stopping on infrastructure failure and resuming a stopped night.
On a capped exit (4) the sitting stops and the next sitting resumes the
record.

**line**

The declared read point, 32,000 output tokens / 48 turns, inside a 48,000 / 72
run budget (`line_token_budget`, `line_turn_budget`). A record must declare
it for its cells to be read at the line.

**line harvest**

The patch the launcher writes as `line.diff` when a cell crosses the declared
line, without disturbing the cell.

**net, rescue, harm**

Rescue: actual not-pass, counterfactual pass. Harm: actual pass,
counterfactual not-pass. Net per task is rescues minus harms, on admitted
cells (C4 pre-registration §4).

**night**

One unattended run of a set of frozen records through the launcher, named A,
B, and so on; the launcher writes one ledger per night.

**oMLX**

The local model server the arms call; preflight checks its settings.

**Ornith**

The model, Ornith 1.5 9B, served by oMLX as `Ornith-1.5-9B-MLX-8bit`.

**outside**

Computed and reported, never deciding; speed-probe sits outside C4's
decision for its prompt ambiguity.

**pass at the line**

The cell's own tree at the line: its `line.diff` when it crossed the declared
line, the harness verdict when it ended inside it; one reader and one grader
for both arms (ledger 2026-10-04, ruling 1). The reader is `grade-line`.

**patch**

The cumulative diff from the workspace's base commit, harvested after the
attempt — untracked files included, so a model `git commit` hides nothing.

**Pi**

The agent CLI both arms run. The Engine runs its own inner Pi inside
`/implement`.

**pre-registration**

The decision rule, denominators and verdict table, approved and committed
before any cell it reads exists. A judgment made after the read is what it
forbids (ledger 2026-10-03, C4 D9).

**R0 sitting**

The attended sitting, at most 60 minutes, in which the maintainer alone fixes
the claim row, ceiling set, budget, win rule and power (census design §8).
Ruled 2026-10-04.

**reach**

A file-tool path or bash argument that resolves to the corpus root, a task
directory, a hidden basename or a fixture, found by the post-hoc reach audit
(unisolated-harness design §3, C3). A hidden basename inside the cell's own
worktree is an in-worktree reach: reported, never counted for admission.

**re-cut**

Rebuilding a task's base from its source. C1's re-cut `7fc679f` removed the
nested selfhost task trees from three bases and changed their task tree
digests.

**refused**

A cell with a `confinement_refused` entry: the extension blocked a file-tool
path outside the worktree or a bash command naming a protected root. Not
admitted.

**replay**

The classifier's reconstruction of a cell's tree at a turn. Diagnostic only
(class columns, pass turn), never a deciding "pass at the line" (ledger
2026-10-04, ruling 1).

**root search**

A bash search whose path argument lies outside the cell's worktree, such as
`/` or the temp root (`cell_evidence.root_search`, which sees through
`timeout`, `env` and similar prefixes since `c9ce8e5`).

**run 1, run 2**

The classifier's two counterfactual readings: run 1 applies the 2026-09-15
§3–§5 rules with amendments 7.1–7.4; run 2 grades the trigger-turn tree by
replay. Run 2 decided C4, with the fidelity amendment; run 1 is printed beside.

**run record**

The frozen JSON that names the task, arms, model, budgets, schedule, and the
decision rule, committed before any cell runs. Its purpose is admission,
route-proof, campaign or development.

**runaway** (class)

A length-stop turn precedes the failure (census design §7).

**self-stop**

A cell that ended by itself, before tripping the budget or a cut
(`self_stop_tokens`, `self_stop_turn` in `cells.json`).

**sitting**

Two senses. A launcher sitting is one start of a record's slots, listed in
the result's `sittings`. A decision sitting is an attended session in which
the maintainer decides, such as the R0 sitting.

**slot**

One of a record's n cells per arm. A finished slot never runs again; a slot
lost to infrastructure is replaced (`launch.py`).

**task**

One self-contained piece of work: a base commit, a contract, a hidden oracle
test suite, and a public feedback surface. Captured by `satyrn-evals capture`.

**transcript**

The model's stream, preserved byte-for-byte, from which tool calls and usage
are read.

**trigger turn**

`own_green_turn`: the turn of the first green test run after the first
source edit, counted only inside the line (finishing-counterfactual spec §3).
The counterfactual stops the cell there.

**UNCONFIRMED, SUPERSEDED, KEPT**

Ledger marks. UNCONFIRMED (`<sha>`): evidence from a harness later found
defective, kept as evidence but built on by nothing until re-derived.
SUPERSEDED: replaced by a re-derivation. KEPT: the mark stands after a
re-derivation that did not cover it (ledger 2026-10-02, "C0"; C4 D9).

**unmeasured**

A cell the read cannot score, listed with its reason and never dropped. In
confinement, a cell with no finding; in C4, a `fidelity:` or `raised:` row,
counted as no change; at the line, a crossed cell with a harvest error or no
line patch, counted as Baseline-favouring (ledger 2026-10-04, ruling 1;
`grade-line` reports it apart, and the pre-registration picks one).

**verdict**

The outcome of offline grading by the oracle test hook — pass or fail, never
an exit code or stdout.
