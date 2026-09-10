"""An implementer **executable** satisfying HP2's seam.

It reads a packet from ``SATYRN_HANDOFF_PACKET``, writes the files its phase
declares, and writes an ``ImplementerResult`` document to
``SATYRN_IMPLEMENTER_RESULT``. Nothing crosses on stdout, for the same reason
no verdict does anywhere else in this repository.

Its phase is chosen by a counter file in the harness directory rather than by
reading the packet's prose, matching the in-process fake: a packet carries no
step id on purpose.

**Split 2026-09-10**, mirroring `adapters/pi_implementer.py`'s own fix for
HP3 composition: ``edit_dir`` (``Path.cwd()``, where phase files are
written) and ``harness_dir`` (``SATYRN_IMPLEMENTER_RESULT``'s parent,
where the counter lives) are two names now, not one derived from the
other. HP2's real `command_implementer` seam sets both to the same
directory, so this is behavior-preserving for every existing test; the new
engine-composed integration test is what actually needs them to differ --
without this split, this fake would write phase files into the harness
scratch directory instead of the isolated worktree `deliver` provides as
this process's own `cwd`, and every phase would come back `NO_CHANGES`.
"""

import json
import os
import sys
from fnmatch import fnmatch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from satyrn_evals.route import ROUTE_SCENARIO  # noqa: E402


def main() -> int:
    packet_path = Path(os.environ["SATYRN_HANDOFF_PACKET"])
    result_path = Path(os.environ["SATYRN_IMPLEMENTER_RESULT"])
    packet = json.loads(packet_path.read_text())
    harness_dir = result_path.parent
    edit_dir = Path.cwd()

    counter = harness_dir / ".phase-counter"
    index = int(counter.read_text()) if counter.is_file() else 0
    counter.write_text(str(index + 1))

    phases = list(ROUTE_SCENARIO.values())
    files = phases[index] if index < len(phases) else {}

    written: list[str] = []
    for name, text in files.items():
        # The executable honours the packet's declared scope, exactly as the
        # in-process fake does; a permissive one would hide a route defect.
        # The patterns are fnmatch, which is why this uses `fnmatch` and not a
        # hand-rolled prefix test. The prefix version it replaced agreed with
        # the patterns only while the phased task rendered exact filenames;
        # HP4's declaration made `templates` render `templates/*` and the
        # difference stopped being invisible.
        if not any(fnmatch(name, pattern) for pattern in packet["writable_paths"]):
            raise SystemExit(f"{name} outside declared scope")
        path = edit_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        written.append(name)

    result_path.write_text(
        json.dumps(
            {
                "changed_files": written,
                "reported_outcome": "delivered" if written else "refused",
                "message": None,
                "version": 1,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
