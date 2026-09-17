"""The broken-channel exception helper: attributed in-process."""

import pytest

from satyrn_evals.adapter_process import _raise_closed_channel
from satyrn_evals.errors import SatyrnError


def test_raise_closed_channel_maps_broken_pipe() -> None:
    with pytest.raises(SatyrnError, match="adapter closed stdin"):
        _raise_closed_channel(BrokenPipeError("gone"))


def test_close_stdin_tolerates_a_missing_descriptor() -> None:
    from types import SimpleNamespace

    from satyrn_evals.adapter_process import AdapterProcess

    proc = object.__new__(AdapterProcess)
    proc._buf = b""
    proc._proc = SimpleNamespace(stdin=None, stdout=None)  # type: ignore[bad-assignment]  # deliberate None-guard subject
    proc.close_stdin()  # the None guard: no descriptor to close
