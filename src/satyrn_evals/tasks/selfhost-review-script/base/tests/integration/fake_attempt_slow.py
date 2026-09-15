"""Fake attempt command that announces itself and then blocks.

Used only by the V11d F3 signal-interruption reproduction: it writes its
artifacts through the same env seam as ``fake_attempt.py``, drops a
uniquely named sentinel so the parent test knows a cell is *in flight*,
and then sleeps until killed. That makes "send the signal mid-cell"
deterministic instead of timing-dependent.

Flags:
  --patch FILE      copy FILE's content to the patch path
  --started DIR     create DIR/<n>.started, numbered by how many exist
  --sleep SECONDS   block this long (default 60); the test kills it first
  --fast-after N    do not sleep once N sentinels already exist
"""

import argparse
import os
import sys
import time
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--patch")
    p.add_argument("--started")
    p.add_argument("--sleep", type=float, default=60.0)
    p.add_argument("--fast-after", type=int, default=0)
    p.add_argument("contract", nargs="?")
    args = p.parse_args()

    if (patch_path := os.environ.get("SATYRN_ATTEMPT_PATCH")) and args.patch:
        Path(patch_path).write_bytes(Path(args.patch).read_bytes())
    if transcript_path := os.environ.get("SATYRN_ATTEMPT_TRANSCRIPT"):
        Path(transcript_path).write_text("fake slow attempt ran\n")

    index = 0
    if args.started:
        started = Path(args.started)
        started.mkdir(parents=True, exist_ok=True)
        index = len(list(started.glob("*.started")))
        (started / f"{index}.started").write_text("", encoding="utf-8")

    if index >= args.fast_after:
        time.sleep(args.sleep)
    sys.exit(0)


if __name__ == "__main__":
    main()
