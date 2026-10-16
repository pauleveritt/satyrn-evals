"""The prerequisite checks live in `satyrn_evals.prereqs`; this keeps the
repo script named by `docs/user-guide.md` and `docs/user-journey.md` runnable,
and `satyrn-evals doctor` reaches the same logic."""

from satyrn_evals.prereqs import main

if __name__ == "__main__":
    raise SystemExit(main())
