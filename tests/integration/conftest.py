"""Integration-tier fixtures.

``cell_scratch``: every row that runs a command as ``satyrn-cell`` asks for
it. It skips with the reason when ``sudo -n -u satyrn-cell true`` fails or
the cells root is absent, so contributors without the second user still get
a green integration tier. The directory lives under the cells root (the
cell cannot read pytest's temp directory) and is removed afterwards.
"""

import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from satyrn_evals.cell import (
    CELLS_ROOT,
    cell_unavailable_reason,
    grant_maintainer,
    share_with_cell,
)


@pytest.fixture
def cell_scratch() -> Iterator[Path]:
    if (reason := cell_unavailable_reason()) is not None:
        pytest.skip(f"the cell user is not set up: {reason}")
    root = Path(tempfile.mkdtemp(prefix="satyrn-test-", dir=CELLS_ROOT))
    assert grant_maintainer(root) is None
    share_with_cell(root)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)
