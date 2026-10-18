#!/usr/bin/env python3
"""Compatibility wrapper for ``uv run satyrn-evals-preflight-commands``."""

from satyrn_evals.preflight_commands import main

if __name__ == "__main__":
    raise SystemExit(main())
