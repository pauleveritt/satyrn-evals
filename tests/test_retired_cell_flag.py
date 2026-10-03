"""No live code passes ``--cell``, the flag ``preflight_settings.py`` lost with
the two-uid harness (2026-09-27); only files headed as historical may still
name it (2026-10-02-c1-requalify-design.md §4). No model, network, or subprocess.
"""

import re
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORICAL_MARK = "# HISTORICAL: frozen evidence for the isolated census nights"
RETIRED = re.compile(r"--cell(?![\w-])")


def retired_flag_callers(paths: Iterable[Path]) -> list[str]:
    """Files that name ``--cell`` and are not headed as historical."""
    return sorted(
        path.name
        for path in paths
        if RETIRED.search(text := path.read_text()) and HISTORICAL_MARK not in text
    )


def _live() -> list[Path]:
    return sorted([*(ROOT / "src" / "satyrn_evals").glob("*.py"), *(ROOT / "scripts").glob("*")])


def test_no_live_file_names_the_retired_cell_flag() -> None:
    assert retired_flag_callers(p for p in _live() if p.is_file()) == []


def test_a_historical_file_and_a_cell_dir_flag_are_not_callers(tmp_path: Path) -> None:
    (tmp_path / "old.sh").write_text(f"#!/bin/sh\n{HISTORICAL_MARK}\nx.py --cell\n")
    (tmp_path / "timing.py").write_text('p.add_argument("--cell-dir")\n')
    assert retired_flag_callers(sorted(tmp_path.iterdir())) == []


def test_an_unheaded_caller_is_named(tmp_path: Path) -> None:
    (tmp_path / "live.sh").write_text("#!/bin/sh\nx.py --cell\n")
    assert retired_flag_callers([tmp_path / "live.sh"]) == ["live.sh"]
