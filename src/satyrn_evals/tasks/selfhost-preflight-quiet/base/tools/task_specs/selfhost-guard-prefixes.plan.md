<!-- The Phase 0 fix wave that widened the guard's pi lead (4a54743) was dispatched from a review, not from a plan task. This file writes that item in the plan-task shape so tools/cut_task.py can derive its R1-plan rung; the prose is the headroom probe's R1 text for the same task (worktree-selfhost-headroom-probe 635c12b, src/satyrn_evals/tasks/selfhost-guard-prefixes/manifest.json). -->

### Fix wave: guard wrapper prefixes before pi

**Files:**
- Modify: `tools/hooks/guard.py`

**Interfaces:**
- Produces: `decide(tool_name: str, tool_input: dict) -> str | None` (signature unchanged; only the pi-lead regex changes)

`_PI_LEAD = ^[\s(]*pi\b` lets `uv run pi -p hi`, `env K=1 pi -p hi`, `time pi -p hi`, `timeout 60 pi -p hi`, `sudo pi -p hi`, `nohup pi -p hi`, `$(pi -p hi)` and `` `pi -p hi` `` through. `uv run` is this repository's habitual prefix. Widen the lead to accept an optional run of known wrapper tokens before `pi`: `uv run`, `env` (with optional `K=V` assignments), `time`, `timeout <arg>`, `sudo`, `nohup`, and an opening `$(` or backtick. Keep `ls pi -p`, `grep -rn pi docs`, `echo pi`, `pip install -p x`, `pipx -p` allowed. Do not touch the write-protection rules.
