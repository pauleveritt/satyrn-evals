"""One-time vendoring: compose the six agentclinic repair bases from swiftstar.

Reconstruction rule (V8 spec §2): base = reference app tree (app.py, models.py,
templates/, tests/test_app.py) MINUS each .delete-named reference file, PLUS the
state's content overrides/additions. Per-state README*.md and .delete markers are
reconstruction meta, never vendored into base/.
"""
import shutil
from pathlib import Path

SRC = Path.home() / "projects/pauleveritt/swiftstar/fixtures/agenttest"
DEST = Path("src/satyrn_evals/tasks")

STATES = ["depth-2", "depth-3", "framing-2", "framing-2-edit",
          "misleading-locus", "plausible-wrong-fix"]
REF_FILES = ["app.py", "models.py", "templates/home.html",
             "templates/base.html", "templates/complaints.html",
             "tests/test_app.py"]


def main() -> None:
    for state in STATES:
        base = DEST / f"agentclinic-repair-{state}" / "base"
        shutil.rmtree(base, ignore_errors=True)
        base.mkdir(parents=True)
        for rel in REF_FILES:
            (base / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SRC / "reference" / rel, base / rel)
        state_dir = SRC / "repair" / state
        for path in state_dir.rglob("*"):
            if path.is_file() and path.name != ".delete" and not path.name.endswith("README.md"):
                rel = path.relative_to(state_dir)
                (base / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, base / rel)
        marker = state_dir / ".delete"
        if marker.exists():
            for line in marker.read_text().splitlines():
                (base / line.strip()).unlink(missing_ok=True)
        print(f"composed {state}")


if __name__ == "__main__":
    main()
