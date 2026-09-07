> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V11a-trim — contract rungs, a generated engine contract, and rung provenance

**Status: confirmed 2026-09-05.** The design of record is the revised
proposal
[`2026-09-05-v11-trim-and-spike-proposal.md`](../research/2026-09-05-v11-trim-and-spike-proposal.md),
which states in its own header that it exists so V11a and V11b "can be ruled
on in one sitting rather than two". The maintainer confirmed its §9 items 1–3
on 2026-09-05. This spec is the delta that confirmation authorizes; it does
not reopen the proposal's arguments.

**Deliberately thin.** §2.5 of the proposal: V9 and V10 together ran to
roughly 3,300 lines of plan and still shipped blockers a one-hour review
caught. Prose is cut; the review is not.

## 1. What ships

1. An optional `contracts: {rung: text}` map in the task manifest — an
   **open** map, validated generically, shipping **R1 and R3 only**.
2. `--rung KEY` on `attempt` and `run`, selecting the text exported as
   `SATYRN_TASK_CONTRACT`.
3. `rung` and `contract_digest` on `AttemptRecord` and `Summary`.
4. A generated engine contract rendered from manifest plus rung, written
   once at a deterministic digest-keyed path under the output root.
5. R1 authored for all six `agentclinic-repair-*` tasks, **re-derived from
   this repository's own base rows**, never from recall.

## 2. Non-goals

- **R0 and R2.** Deferred to the V12 entry gate (proposal §2.1). The open
  map means they are later authoring additions, not new machinery.
- **Vendoring `specs/` into `base/`.** Reversed (§2.2). `base/` stays
  byte-identical, so the six contamination pairs and the 24/24 gate need no
  re-derivation.
- **The widened hidden-id check.** Deferred (§2.3): at R1 it is
  contradictory, because R1 carries bare hidden function names by design.
- **Envelope, arm definitions, the Pi adapter.** V11b.
- **Any model run.** The V5d smokes are the proposal's step 2, after both
  tracks land; the mini-probe and spike are behind a separate gate.
- **Rewriting historical records.** Pre-V11a records still load.

## 3. The manifest field

```json
"contracts": {
  "R1": "…",
  "R3": "…"
}
```

- Optional. Absent means the task has no rungs; `--rung` against it is a
  usage error naming the task.
- Keys are non-empty strings; the map is **open** — no enum of rung names in
  production code. R0 and R2 are added by authoring a key, not by a code
  change.
- Values are non-empty strings.
- `contract` remains the default and is what an attempt without `--rung`
  exports. It stays equal to R3 for the six AgentClinic tasks.
- **`_assert_contract_names_no_overlay` runs over `contract` and every rung
  value** (`manifest.py:207` runs over `contract` alone today). This is the
  one check the trim makes *wider*, not narrower, and it is not optional.

**The R1 authoring constraint that falls out of it.** The existing check
forbids the overlay's declared names — `overlay`, `test_acceptance.py`,
`overlay/test_acceptance.py`. So an R1 digest must carry **bare function
names** (`test_post_complaint_redirects_to_complaints_board`), never the
`test_acceptance.py::test_x` node-id form `expected_test_ids` uses, or the
manifest is refused at load. V8 §4 already authorized naming them.

## 4. `--rung`

- `attempt TASK --rung R1 -- CMD…` and `run TASK --rung R1 --n N -- CMD…`.
- Unknown rung, or `--rung` on a task with no `contracts`: `UsageError`,
  exit as the CLI's existing usage path does, naming the available keys.
- Absent `--rung`: `contract` is exported, `rung` is recorded `null`, and
  `contract_digest` is the digest of `contract`.
- The **adapter never sees `--rung`**. The rung reaches the executable as
  `SATYRN_TASK_CONTRACT`, exported by evals before invocation
  (`attempt.py:108-110`). This is what makes V11a and V11b independent.

## 5. Rung provenance on the record

`Summary` carries task, command and timeout (`summary.py:42-44`);
`AttemptRecord` carries no contract identity. Two runs at R1 and R3 with the
same command differ only by the prompt echoed in the transcript's first
`message_start` — recomputable but not indexed, the same shape as V9's T4.

- `rung: str | None` — the selected key, `null` when the default `contract`
  was used.
- `contract_digest: str | None` — SHA-256 of the exact selected text, UTF-8.
  **Always present on a new record**, including the default contract.
- Legacy records load with both `null` and re-summarize preserving the
  explicit unknowns. This is a new record generation, not a rewrite of
  history: `version` stays 1 and the fields are optional-on-read,
  required-on-write.
- `Summary` refuses mixed `rung` or mixed `contract_digest` across cells,
  exactly as it refuses mixed tasks, commands and timeouts
  (`summary.py:141-149`).

## 6. The generated engine contract

Today's `engine-contract.yaml` is hand-authored and shipped for two tasks
only; the six AgentClinic tasks have none. The V8 smoke used a hand-authored
file that **differed from the manifest by a token** and narrowed
`writable_paths` to `[app.py]`
(`2026-09-04-v5-v8-deep-review-and-agentclinic-ladder.md:287`). Generating it
makes the text the model sees the text on record.

New `engine_contract.py` renders, from manifest plus selected rung:

```yaml
id: <task>@<rung>            # stable for task + rung + digest
task: <the selected contract text>
writable_paths:
  - …
```

- **Both `id` and `task` are required** — Engine requires `id` as well as
  `task` (proposal correction 14).
- `writable_paths` derives from `source_paths`: a **file** entry stays
  exact; a **directory** entry becomes an fnmatch pattern matching its
  descendants. A generated pattern must admit every intended source file and
  reject a neighboring path — both directions, per BRIEF rule 8.
- Rendered bytes are written **once** at a deterministic path under the
  output root, keyed by the SHA-256 of the rendered bytes, and that stable
  absolute path is appended to the command.

**Why not the attempt directory.** A fresh per-attempt path changes the
recorded command, and `compute_summary` refuses mixed commands
(`summary.py:141-149`), so a batch would not summarize (proposal correction
8). The digest-keyed path is stable across the cells of a run and pins the
exact bytes.

## 7. Evidence floor (BRIEF rule 2, rule 6, rule 8)

Every item is a refusal paired with a success, each naming its fixture.

**Default tier.**

| # | Refuses | Accepts |
|---|---|---|
| 1 | `contracts` with an empty-string value | a two-key `{R1, R3}` map |
| 2 | a rung value naming `test_acceptance.py` | the same text with bare function names |
| 3 | `--rung R9` on a task with rungs | `--rung R1` |
| 4 | `--rung R1` on a task with no `contracts` | no `--rung` on that task |
| 5 | a new record written without `contract_digest` | a legacy record loading with `rung=null, contract_digest=null` |
| 6 | a summary over cells with mixed rungs | a summary over cells at one rung |
| 7 | a summary over cells with mixed digests at the same rung | equal digests |
| 8 | a generated pattern matching a neighboring path outside `source_paths` | the same pattern matching every declared source file |
| 9 | — | generated bytes pinned byte-for-byte for one task at each of R1 and R3 |
| 10 | — | a two-attempt batch summarizes **and re-summarizes** with equal commands |

**Integration tier.** `satyrn-engine check` accepts all six generated
contracts at both rungs. Marked `integration`; does not run in CI.

## 8. Stated limits

- **The R0→R3 monotonicity authoring gate collapses to a two-point
  `R1 ≤ R3` check** while only two rungs ship, and no run in this phase
  measures it. **The rung labels are unverified authoring claims until
  V12.** The trim advances an early comparison; it does not remove the R0/R2
  work, which is a V12 entry gate.
- **R1 may already sit at ceiling for a 12B.** The fixture author's own
  review says `assert 307 == 303` "delivers the answer"; Block B recorded
  19/20 on `plausible-wrong-fix`; the V8 smoke passed first try at R3, and
  R1 removes only the file name and the fix sentence. If the mini-probe
  ceilings at R1, R0 returns before the spike (proposal §4.1 rule 4).
- **`id` stability is a claim about this generator, not about Engine.**
  Engine's acceptance of the generated shape is proven only by the
  integration-tier `satyrn-engine check` row, against the pinned commit
  `75d4863`.
