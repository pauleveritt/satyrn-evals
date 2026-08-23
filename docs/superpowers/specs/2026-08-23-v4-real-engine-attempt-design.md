# V4 — Real engine attempt: design spec

**Phase:** V4 (`ROADMAP.md`). **Date:** 2026-08-23. **Status:** approved for
implementation by Issue #5 and the maintainer discussion.

## Correction — 2026-08-23 post-implementation review

The first implementation review found six places where the accepted design
was underspecified or its planned evidence did not prove the claim:

1. A safe temporary root is outside the task/output/cwd **and** outside every
   enclosing Git repository's top-level, registered worktree, Git directory,
   and common directory that can be discovered from those paths. Allocation
   and post-allocation identity checks use the expanded set.
2. The synthetic commit includes every persisted regular file, including a
   file matched by the persisted `.gitignore`; eval-owned `git add` therefore
   uses `--force`. An empty persisted tree is a valid Git tree, not a setup
   refusal.
3. Process cleanup is closed before teardown begins and reopens only after the
   direct child is reaped and the POSIX group is confirmed gone. Descriptor
   and temporary-parent acquisition has explicit ownership. A catchable
   primary exception keeps its identity; every cleanup failure remains visible
   as a note or a typed `CLEANUP_FAILED` with its retained path.
4. Workspace and attempt records enforce their complete runtime shape. The
   loader accepts omission only of `workspace_base_sha` and `retained_path` in
   a legacy V3 record; it does not coerce malformed strings, numbers,
   sequences, or extra fields.
5. `COMMAND_UNAVAILABLE` is a workspace outcome converted to usage/no record.
   A separate `WorkspaceRun` or injectable `CommandRunner` was not needed:
   `WorkspaceResult` carries the boundary and failure tests patch private
   production functions only for destructive or non-portable branches.
6. The real Engine evidence invokes the installed `uv` and the source
   checkout's `satyrn-engine` console script. Only Pi is replaced by a
   deterministic fixture; the test does not replace the project/entrypoint
   seam.

The synchronous trusted-command boundary is unchanged: normal direct-child
completion records its exit code; process-group teardown is required for a
timeout or exceptional wait path. Hostile or daemonizing command containment
remains outside V4.

## Why this phase

V3 proved the executable attempt seam with a fake command, but its workspace
is only a copied directory. `satyrn-engine attempt` deliberately has no
`--repo`; it requires its current directory to be a clean Git worktree with a
readable `HEAD`. V4 therefore has two inseparable outcomes:

1. reconstruct a private Git repository from a task's persisted `base/` and
   run the command once in a detached linked worktree; and
2. use that same executable seam with one real E5 `satyrn-engine attempt`,
   preserving its patch and transcript before cleanup and grading the patch
   offline.

The isolation mechanism is the subject of
[Issue #5](https://github.com/pauleveritt/satyrn-evals/issues/5). The current
satyrn-engine E3/E5 specifications and the corrected V2 capture lifecycle are
evidence; their code is not copied. V4 re-earns the behavior for a repository
that evals constructs and owns completely.

## Done-when

- `satyrn-evals attempt TASK -- COMMAND...` reconstructs a private repository
  from `TASK/base`, creates one detached worktree at the exact synthetic base
  commit, runs the command once there, and removes the worktree and repository
  after preserving attempt artifacts.
- The materialized worktree represents the task base: regular-file bytes,
  executable bits, and symbolic-link targets are verified before the command
  starts. Empty directories are not part of Git's tree model.
- Repository-local Git routing variables are removed from the child
  environment. Git prompts are disabled. Engine-owned Git commands disable
  hooks, fsmonitor, replacement refs, and graft overlays while retaining
  ordinary Git configuration and filters.
- The worktree registration guard becomes uncertain before `git worktree add`
  can mutate Git state. Cleanup deletes the temporary parent only after Git
  confirms that the linked worktree is no longer registered.
- A timeout tears down and reaps the command's POSIX process group before Git
  cleanup. A cleanup failure is the final authoritative refusal and names the
  retained recovery path. Windows remains outside the V4 proof.
- The bundled task carries an engine-owned contract as an opaque task artifact.
  Evals validates only its safe task-relative location, appends its absolute
  path to `COMMAND...`, and never parses its contents.
- A real E5 `satyrn-engine attempt` changes the bundled task through the same
  seam, writes the existing patch and transcript artifacts, and the persisted
  patch grades `pass` offline. A real Engine failure still writes an attempt
  record with its command exit and whatever artifacts were produced.
- The fake-command success and refusal siblings remain green. Default tests
  spawn nothing; real Git, process groups, and Engine execution stay in the
  integration tier. Python statement and branch coverage remain 100%; Ruff,
  Pyrefly, strict Sphinx, and `git diff --check` pass.

## Ownership boundary

```text
task package
  base/                    evals-owned captured tree
  manifest.json            evals-owned grading metadata
  engine-contract.yaml     engine-owned opaque input

satyrn-evals
  reconstruct private repository
  create/remove detached worktree
  clean child environment
  enforce outer timeout and process teardown
  preserve patch/transcript
  grade the preserved patch and write attempt.json/receipt.json

satyrn-engine attempt
  parse the engine contract
  enumerate the detached worktree
  run Pi with E4 mutation
  write patch/transcript to the V3 artifact seam
```

Evals does not import engine internals, validate the engine contract schema,
or infer a verdict from Engine stdout or exit status. Engine does not create a
second worktree in this path. The worktree is eval-owned because V4 calls E5
`attempt` directly; E3 `deliver` is not part of this path.

## Phase slices

V4 is implemented as four reviewable slices, each complete enough to test:

1. **Design and plan** — this specification and its file-level plan.
2. **Workspace isolation** — synthetic repository, exact base commit,
   detached-worktree lifecycle, clean environment, timeout, and cleanup
   precedence. The fake command remains the executable proof.
3. **Real Engine seam** — opaque contract path, bundled contract fixture, and
   a real E5 integration run using the source checkout rather than a published
   package.
4. **Evidence and documentation** — full failure matrix, coverage, public
   architecture/usage/glossary/roadmap, and the SDD verification record.

No slice adds batching, task selection, baseline probes, or summaries; those
remain V5.

## Task contract seam

The manifest gains one optional field:

```json
{
  "engine_contract": "engine-contract.yaml"
}
```

When present, it must be a non-empty relative POSIX path naming an existing
regular file below the task directory. Absolute paths, `..`, backslashes,
symlinks in any component, and non-regular files are rejected. Evals reads no
bytes from the file; the Engine owns its format and validation.

For such a task, the invoked argv is:

```text
COMMAND... /absolute/task/path/engine-contract.yaml
```

The appended path is option-safe because `satyrn-engine attempt` accepts a
literal `--` before its positional contract. The recommended V4 command is:

```text
uv run --project /path/to/satyrn-engine satyrn-engine attempt \
  --model=MODEL --
```

Evals appends the contract after that prefix. V3 manifests without
`engine_contract` remain usable with their existing fake/custom command and
receive no appended argument. They are not Engine-capable until a maintainer
adds an opaque Engine contract. V4 does not teach V2 capture to author Engine
YAML; that would duplicate Engine policy in evals.

The bundled `format_number` task gains an Engine contract whose writable path
matches its existing `source_paths`. This one fixture proves the vertical
slice; automatically creating Engine contracts for captured tasks is not part
of V4.

## Synthetic repository

`base/` intentionally contains no Git administration data. V4 reconstructs a
repository for each attempt:

```text
allocate verified temporary parent
  -> copy TASK/base into seed/ (preserve symlinks and modes)
  -> git init seed/
  -> git add --force --all
  -> create one deterministic base commit
  -> git worktree add --detach worktree/ BASE
  -> confirm registration, detached HEAD, clean status, and base snapshot
  -> run COMMAND once in worktree/
  -> preserve artifacts outside the temporary parent
  -> terminate/reap if required
  -> git worktree remove --force
  -> confirm registration absent
  -> remove the whole temporary parent
  -> grade the preserved patch
```

The synthetic commit is identity, not provenance. The attempt record may name
it for diagnosis, but the task manifest's optional V2 `provenance` remains the
source-history identity. The synthetic commit uses fixed author/committer
identity and message, disables signing, and strips inherited author/committer
date overrides so ambient user configuration cannot make creation fail.

The temporary parent is allocated from explicit system temporary roots, not a
blind inherited `TMPDIR`, and is verified outside the task directory, attempt
output, and any existing Git worktree that can be discovered from those
paths. The repository and both its worktrees are eval-owned and disposable.
If cleanup cannot prove that the linked worktree registration is absent, the
parent is retained for recovery rather than recursively deleted.

## Git boundary

Every eval-owned Git invocation uses the current corrected safety boundary:

- `--no-replace-objects` and `GIT_NO_REPLACE_OBJECTS=1`;
- `GIT_GRAFT_FILE` fixed to the null device;
- `core.hooksPath` fixed to the null device;
- `core.fsmonitor=false`;
- `GIT_TERMINAL_PROMPT=0`;
- `core.symlinks=true` for materialization and
  `core.sparseCheckout=false` for linked-worktree creation;
- repository-local routing variables from `git rev-parse --local-env-vars`,
  plus `GIT_NAMESPACE`, removed from owned Git and command environments.

The Issue #5 wording mentions an empty hooks directory. Current E3 and the
corrected V2 implementation use the platform null device and also disable
fsmonitor/reference-transaction paths; V4 follows the newer, tested boundary.
Normal clean/smudge filters remain enabled. After checkout, the verified base
snapshot is authoritative: a filter that cannot reproduce the persisted task
base causes a named workspace refusal before the command runs.

## State machine and cleanup precedence

```text
ABSENT
  | begin add (before Git call)
  v
MAY_EXIST -- Git confirms present --> PRESENT -- remove + confirms absent --> ABSENT
    |                                  |
    +-- lookup failure ----------------+
                 retain parent; CLEANUP_FAILED
```

`MAY_EXIST` and `PRESENT` both close the recursive-delete gate. An interrupt
can arrive after Git registers the worktree but before the subprocess or
registration lookup returns; setting the guard before the mutating call is
therefore required.

One `finally` path owns command teardown, linked-worktree removal, and parent
removal. Its precedence is:

1. a catchable unexpected primary exception keeps its identity; every
   secondary cleanup failure is attached as a note;
2. otherwise any unconfirmed process or worktree cleanup becomes a refused
   `CLEANUP_FAILED` record and supersedes success, ordinary refusal, timeout,
   or command failure while preserving their diagnostic detail;
3. only confirmed process teardown and confirmed absent registration open the
   parent-deletion gate.

The record's `command_exit` becomes nullable because setup or timeout can end
without a normal child exit. Existing V3 records remain readable. Detailed
attempt codes become a dedicated `AttemptCode` `StrEnum`; exit status remains
coarse (`0`, `2`, or `3`) and is never the verdict.

## Command lifecycle

The command is trusted and synchronous, but V4 owns its bounded lifecycle:

- `stdin` is disconnected;
- stdout/stderr are captured for process hygiene but remain non-authoritative;
- on POSIX the command starts a new session/process group;
- normal completion records the direct child's exit code;
- timeout sends `SIGTERM`, waits a short grace period, then `SIGKILL`, and
  reaps the direct child before Git cleanup;
- if group disappearance or direct-child reap cannot be confirmed, Git and
  filesystem cleanup are withheld and the recovery path is recorded.

Windows uses a direct-child fallback and is not evidence for this phase. WSL
is Linux only when its filesystem and Git behavior satisfy the POSIX
integration tests. This is not a security sandbox: the command has the user's
permissions and can intentionally access paths outside the worktree.

## Attempt results

Existing V3 preservation codes remain. V4 adds typed operational codes:

| code | condition |
|---|---|
| `WORKSPACE_FAILED` | private repository/base/worktree preparation failed before a usable command run |
| `COMMAND_TIMEOUT` | the command exceeded the configured deadline and teardown was confirmed |
| `CLEANUP_FAILED` | process, worktree, or parent cleanup could not be confirmed; retained path named |

An Engine exit by itself is diagnostic only. If it still produced a complete
patch and transcript, those artifacts are graded. If it produced no patch,
the existing first-failure rule records `NO_PATCH`, with `command_exit`
preserved. This keeps V3's artifact-driven outcome unchanged.

## Tests and evidence

### Default tier

- typed attempt-code/outcome/exit maps and record invariants;
- tree snapshot equality for bytes, executable modes, and symlink targets;
- environment cleaning without subprocess;
- task-relative opaque contract validation, including traversal/symlink
  refusal and a regular-file sibling;
- state transitions and cleanup-result precedence using abnormal-path mocks;
- command construction preserves every user token and appends the contract
  exactly once only for Engine-capable tasks.

### Integration tier

- real Git reconstruction and detached `HEAD` at the synthetic base;
- command observes a clean Git worktree, the expected base files, stripped
  routing variables, and no repository hooks/fsmonitor execution;
- normal filters still operate and the materialized snapshot remains exact;
- hostile `TMPDIR`, worktree-add success followed by reported failure,
  registration lookup interruption, locked cleanup, timeout descendant, and
  executable/symlink base fixtures;
- source task directory, caller checkout, and attempt output contain only
  declared persistent artifacts after success/refusal;
- fake known-good/known-broken/refusal siblings remain green;
- source-checkout E5 command with fake Pi writes real Engine patch/transcript,
  the patch names `solution.py`, grades the bundled known-good result `pass`,
  and leaves no linked worktree registration or descendant.

## Out of scope

- model-quality claims, baseline probes, suite admission, repeated attempts,
  summaries, A/B comparison, and resume — V5;
- automatic Engine-contract generation from V2 manifests or prose;
- Engine package publication or a shared Python dependency;
- containers, hostile-command containment, filesystem quotas, and rollback of
  writes made intentionally outside the disposable tree;
- Windows proof, native Windows symlink semantics, and WSL-specific support;
- changing Engine's YAML contract format to TOML. That is a separate Engine
  design issue and must not be smuggled into eval workspace isolation.
