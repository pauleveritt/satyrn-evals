# Whole-attempt deadline implementation plan

This plan implements the reviewed
[whole-attempt deadline design](whole-attempt-deadline-design.md). It does not
authorize an executor or model run.

## 1. Establish durable, default-tier semantics

1. Extend the attempt record with optional `attempt_timeout` configuration
   provenance, plus an immutable `deadline` block when it expires: matching
   whole-attempt seconds, first-expired phase, observed elapsed seconds, and
   retained-workspace status. Add `DEADLINE_EXCEEDED` as the pre-grade refusal
   code.
2. Permit a retained artifact path with an absent digest only for the
   deadline-finalization missingness case; retain existing digest requirements
   otherwise. State that distinction in the wire-format documentation.
3. Add default-tier tests for valid and invalid deadline blocks, ordinary
   records remaining unchanged, `DEADLINE_EXCEEDED` before a grade, and a
   `GRADE_FAILED` record retaining deadline provenance for later regrade.

## 2. Add one deadline authority

1. Add a small monotonic deadline object to the attempt layer. It creates one
   deadline after no-write validation, returns remaining seconds for a named
   phase, and raises a typed expiry carrying phase and elapsed time.
2. Unit-test expiry, command-versus-whole precedence, simultaneous expiry,
   and no new productive phase after expiry using a fake clock. Do not use a
   real sleep or subprocess in this tier.
3. Add `--attempt-timeout SECONDS` to `attempt` and `run`, with no implicit
   whole-attempt default. Keep `--timeout` as the independent command limit.
   Test missing/invalid/explicit values and update the CLI reference.

## 3. Make workspace lifetime finalize last

1. Refactor the workspace boundary into a lease whose command result and
   artifacts can be processed before its cleanup. Preserve current safe Git
   materialization and process-group isolation.
2. Replace the current multiple teardown waits with one shared monotonic
   `DEFAULT_TEARDOWN_GRACE` cutoff for termination, reaping, and group checks.
   On expiry, allow only finalization: teardown, artifact reads, record/receipt
   writes, and safe retention.
3. Default-tier fake-workspace tests cover setup, command, preservation, and
   cleanup expiries; each has a within-budget sibling. Verify that all paths
   preserve the attempt directory and artifacts available at the boundary.

## 4. Bound grading without changing verdict authority

1. Pass the remaining deadline to grading's environment materialization, Git,
   oracle, and freeze-attestation subprocesses. An expiry starts no later
   subprocess.
2. Write the pre-grade `GRADE_FAILED` record before grading. If a deadline is
   observed during grading, retain it with deadline provenance and leave it
   regradeable.
3. If a receipt is durable before expiry but its `OK` record is not, finalize
   the matching `OK` record from that receipt. A durable `unavailable` receipt
   remains a completed unavailable verdict, never a refusal fabricated from a
   timeout or exit code.
4. Test both default-tier fake grader paths and regrade: regrading changes only
   eligible verdict/receipt data and preserves original deadline provenance.

## 5. Summaries, integration, and review

1. Surface deadline provenance and explicit missingness in summaries without
   changing the planned denominator or turning it into a success rate.
2. Add marked integration witnesses for real command-group teardown, an oracle
   subprocess given a short remaining budget, receipt-before-record
   finalization, and cleanup retention. Regrade retained evidence offline.
3. Run the default suite with its subprocess tripwire, the affected integration
   tests, Ruff, type checking, documentation lint, strict Sphinx, and
   `git diff --check`. Distinguish any baseline type-check failures.
4. **Final Astra acceptance review:** after Sol's iterative reviews and all
   focused checks, review the implementation and retained evidence before any
   live run. A live request still must freeze the task/rung, prompt,
   executor, model/engine/tool revisions, schedule, both limits, stopping rule,
   budget, and evidence-review plan. The first live action is one bounded
   attempt; two per matched configuration is triage only.
