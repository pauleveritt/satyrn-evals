#!/usr/bin/env python3
"""Real command fixture for the V4 detached-worktree integration tests."""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observation")
    parser.add_argument("--lock", action="store_true")
    parser.add_argument("--lock-and-remove", action="store_true")
    parser.add_argument("--delay-marker")
    parser.add_argument("--git-sentinel")
    parser.add_argument("--filtered", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.lock:
        completed = subprocess.run(
            ["git", "worktree", "lock", "."], capture_output=True, check=False
        )
        return completed.returncode
    if args.lock_and_remove:
        worktree = Path.cwd()
        completed = subprocess.run(
            ["git", "worktree", "lock", "."], capture_output=True, check=False
        )
        if completed.returncode != 0:
            return completed.returncode
        os.chdir(worktree.anchor)
        shutil.rmtree(worktree)
        return 0
    if args.delay_marker:
        code = (
            "import signal,time; from pathlib import Path; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            f"time.sleep(0.6); Path({args.delay_marker!r}).write_text('late')"
        )
        subprocess.Popen([sys.executable, "-c", code])
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        time.sleep(2)
        return 0
    if args.git_sentinel:
        sentinel = Path(args.git_sentinel)
        git_dir = Path(
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
        hooks = git_dir / "hooks"
        hooks.mkdir(exist_ok=True)
        for name in ("reference-transaction", "post-checkout"):
            hook = hooks / name
            hook.write_text(f"#!/bin/sh\necho fired >> {sentinel!s}\n")
            hook.chmod(0o755)
        fsmonitor = git_dir / "fsmonitor"
        fsmonitor.write_text(f"#!/bin/sh\necho fired >> {sentinel!s}\n")
        fsmonitor.chmod(0o755)
        subprocess.run(["git", "status", "--porcelain"], check=True, capture_output=True)
        subprocess.run(
            ["git", "update-ref", "refs/satyrn/probe", "HEAD"],
            check=True,
            capture_output=True,
        )
        return 0
    assert args.observation
    cwd = Path.cwd()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    symbolic = subprocess.run(
        ["git", "symbolic-ref", "--quiet", "HEAD"], capture_output=True, check=False
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
    ).stdout
    Path(args.observation).write_text(
        json.dumps(
            {
                "cwd": str(cwd),
                "head": head,
                "detached": symbolic.returncode == 1,
                "status": status,
                "git_dir": os.environ.get("GIT_DIR"),
                "git_work_tree": os.environ.get("GIT_WORK_TREE"),
                "git_namespace": os.environ.get("GIT_NAMESPACE"),
                "terminal_prompt": os.environ.get("GIT_TERMINAL_PROMPT"),
                "plain": (cwd / "plain.txt").read_text(),
                "link_target": os.readlink(cwd / "link"),
                "executable": os.access(cwd / "run", os.X_OK),
                "filtered": (cwd / "filtered.txt").read_text()
                if args.filtered
                else None,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
