#!/usr/bin/env python3
"""Compatibility wrapper for ``uv run satyrn-evals-preflight-models``."""

from satyrn_evals.preflight_models import main

if __name__ == "__main__":
    raise SystemExit(main())
