"""The frozen census instruments equal their blobs at 0c3ad1f.

C3 and C4 outputs are reproduced by running these files unmodified; an edit
changes signed rows. Digests computed with ``git show 0c3ad1f:<path> | shasum -a 256``.
The file also pins the EB2 inputs, ``eb1.py`` and ``read_cells.py``, at their
committed blobs (``git show 8079874:<path> | shasum -a 256``).
The delivery reader ``decide.py`` is pinned at its blob at c75a5ab, re-frozen after the
review's fixes (``git show c75a5ab:<path> | shasum -a 256``), before launch (D5).
"""

import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

FROZEN = {
    "evidence/2026-09-16-census/classify.py": "2951b12b7f9500738827aa857daea3d43d57fc01725837cef376f352d09ad4db",
    "evidence/2026-09-15-finishing-counterfactual/counterfactual.py": "8a213fc3ce0724e1c3dea14edfd39a1198610f7b8cdb3c99c84e634e2738dce5",
    "src/satyrn_evals/census_classify.py": "637d0ef7fbf12e84a03d5b6f97551e46a9193de4976cd352fdb5554556244fea",
    "evidence/2026-10-03-eb1-read/eb1.py": "6f2dd72b5d0a9ef2a113d197a97b1ae0ffbdc4dd36ec81c4acb8dd11167cbe9a",
    "evidence/2026-10-05-eb-cell-read/read_cells.py": "6fdb28541b6d2067b842971ea221bf431510a47a8eda9db189a7712f4685633b",
    "evidence/2026-10-05-rrg-delivery/decide.py": "44573d17ab2ac87f643a20cecfecebdac6d878fe3646aa5f6182626b582c9aad",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_digest_function_known_value():
    assert digest(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


@pytest.mark.parametrize("path", sorted(FROZEN))
def test_frozen_instrument_unchanged(path: str):
    assert digest((ROOT / path).read_bytes()) == FROZEN[path], f"{path} drifted from 0c3ad1f"
