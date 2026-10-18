#!/usr/bin/env python3
"""Compatibility wrapper for ``uv run satyrn-evals-preflight-settings``."""

from satyrn_evals.preflight_settings import main

if __name__ == "__main__":
    raise SystemExit(main())
