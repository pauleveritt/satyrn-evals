"""Synthetic fixture executor for the first-milestone route.

It uses the ordinary attempt environment seam but identifies itself in its
transcript as a fixture, never as a model or engine.
"""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("contract")
    args = parser.parse_args()

    patch = Path(args.patch)
    Path(os.environ["SATYRN_ATTEMPT_PATCH"]).write_bytes(patch.read_bytes())
    transcript_path = Path(os.environ["SATYRN_ATTEMPT_TRANSCRIPT"])
    # Retain both delivery artifacts before any further work.  A terminating
    # signal can arrive while applying the patch or running the public suite;
    # this provisional transcript makes that interrupted attempt reviewable.
    transcript_path.write_text(
        json.dumps(
            {
                "type": "message",
                "message": {"model": args.model},
                "status": "started",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "apply", str(patch)], check=True, capture_output=True)
    public_hook = transcript_path.with_name("public-hook.json")
    public_env = dict(os.environ)
    public_env["SATYRN_ORACLE_RESULT"] = str(public_hook)
    public_env["PYTEST_PLUGINS"] = "satyrn_evals.oracle_hook"
    public_env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    public = subprocess.run(
        ["uv", "run", "python", "-m", "pytest", "tests/"],
        capture_output=True,
        text=True,
        env=public_env,
    )
    transcript_path.write_text(
        json.dumps(
            {
                "type": "message",
                "message": {"model": args.model},
                "public_suite_exit": public.returncode,
                "public_hook": json.loads(public_hook.read_text(encoding="utf-8")),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    if pause := os.environ.get("SATYRN_FIXTURE_PAUSE"):
        time.sleep(float(pause))
    raise SystemExit(public.returncode)


if __name__ == "__main__":
    main()
