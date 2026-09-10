"""HP7's marker-ordering fix, witnessed against a real process.

The mocked-`subprocess.run` unit tests in `test_pi_implementer.py` cannot
catch the bug Sol reproduced: they write the marker and the child's bytes
through the *same* Python file object, in process, so both go through the
same userspace buffer and land in write order regardless of any flush. A
real child process gets the file's raw OS descriptor via `dup2` and writes
straight to it -- so an unflushed marker sitting in Python's own buffer can
lose the race to the child's own write. Only a real subprocess exercises
that race; this file drives one.
"""

from pathlib import Path

import pytest

from satyrn_evals.adapters import pi_implementer
from satyrn_evals.route import PACKET_ENV, RESULT_ENV

pytestmark = pytest.mark.integration

PROJECTION = {"objective": "Say hello.", "facts": ["x"]}


def test_the_marker_precedes_real_child_output_in_the_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`/bin/echo` stands in for `pi`: a real, fast, dependency-free child
    that writes deterministic bytes to the same stdout descriptor `pi`
    would. The regression this guards: the marker written just before
    `subprocess.run` must reach the file before the child's own bytes do."""
    packet_path = tmp_path / ".satyrn-packet.json"
    result_path = tmp_path / ".satyrn-result.json"
    import json

    packet_path.write_text(json.dumps(PROJECTION))
    monkeypatch.setenv(PACKET_ENV, str(packet_path))
    monkeypatch.setenv(RESULT_ENV, str(result_path))
    monkeypatch.setattr(
        pi_implementer,
        "build_pi_argv",
        lambda model, tools, prompt, pi_bin: ["/bin/echo", "real-child-output"],
    )

    pi_implementer.main(["--model", "irrelevant", "--pi-bin", "/bin/echo"])

    transcript = (tmp_path / pi_implementer.TRANSCRIPT_NAME).read_bytes()
    marker_index = transcript.index(b'"adapter_marker"')
    child_index = transcript.index(b"real-child-output")
    assert marker_index < child_index, (
        f"marker at {marker_index} did not precede child output at "
        f"{child_index}: {transcript!r}"
    )


def test_the_marker_precedes_real_child_output_across_two_phases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The shape that actually matters for phase segmentation: two real
    calls in the same workspace, each marker ahead of its own turn's bytes,
    in the right relative order."""
    packet_path = tmp_path / ".satyrn-packet.json"
    result_path = tmp_path / ".satyrn-result.json"
    import json

    packet_path.write_text(json.dumps(PROJECTION))
    monkeypatch.setenv(PACKET_ENV, str(packet_path))
    monkeypatch.setenv(RESULT_ENV, str(result_path))
    monkeypatch.setattr(
        pi_implementer,
        "build_pi_argv",
        lambda model, tools, prompt, pi_bin: ["/bin/echo", "turn-output"],
    )

    pi_implementer.main(["--model", "irrelevant", "--pi-bin", "/bin/echo"])
    pi_implementer.main(["--model", "irrelevant", "--pi-bin", "/bin/echo"])

    transcript = (tmp_path / pi_implementer.TRANSCRIPT_NAME).read_text()
    first_marker = transcript.index('"index": 0')
    first_output = transcript.index("turn-output")
    second_marker = transcript.index('"index": 1')
    second_output = transcript.index("turn-output", first_output + 1)
    assert first_marker < first_output < second_marker < second_output
