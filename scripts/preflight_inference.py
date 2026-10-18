#!/usr/bin/env python3
"""Compatibility wrapper for ``uv run satyrn-evals-preflight-inference``."""

from satyrn_evals.preflight_inference import main

if __name__ == "__main__":
    raise SystemExit(main())
