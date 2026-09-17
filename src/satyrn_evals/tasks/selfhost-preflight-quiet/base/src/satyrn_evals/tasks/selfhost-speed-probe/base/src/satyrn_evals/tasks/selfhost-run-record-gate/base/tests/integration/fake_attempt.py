"""Fake attempt command: honors the env seam for integration tests.

Writes the patch to SATYRN_ATTEMPT_PATCH and the transcript to
SATYRN_ATTEMPT_TRANSCRIPT, then exits. A test double, not a real engine —
it exercises the seam end-to-end without any model or network.

Flags:
  --patch FILE        copy FILE's content to the patch path
  --transcript TEXT   transcript content (default: "fake attempt ran")
  --exit N            process exit code (default: 0)
  --no-patch          write nothing to the patch path
  --bad-patch         write non-diff text to the patch path
  --no-transcript     write nothing to the transcript path
  --empty-transcript  write an empty transcript
"""

import argparse
import os
import sys
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--patch")
    p.add_argument("--transcript", default="fake attempt ran")
    p.add_argument("--exit", type=int, default=0)
    p.add_argument("--no-patch", action="store_true")
    p.add_argument("--bad-patch", action="store_true")
    p.add_argument("--no-transcript", action="store_true")
    p.add_argument("--empty-transcript", action="store_true")
    p.add_argument("contract", nargs="?")
    args = p.parse_args()

    if args.contract is not None and not Path(args.contract).is_file():
        p.error("contract is not a file")

    patch_path = os.environ.get("SATYRN_ATTEMPT_PATCH")
    if patch_path and not args.no_patch:
        if args.bad_patch:
            Path(patch_path).write_text("this is not a unified diff\n")
        elif args.patch:
            Path(patch_path).write_bytes(Path(args.patch).read_bytes())

    transcript_path = os.environ.get("SATYRN_ATTEMPT_TRANSCRIPT")
    if transcript_path and not args.no_transcript:
        text = "" if args.empty_transcript else args.transcript
        Path(transcript_path).write_text(text)

    sys.exit(args.exit)


if __name__ == "__main__":
    main()
