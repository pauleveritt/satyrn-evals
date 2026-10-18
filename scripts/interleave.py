#!/usr/bin/env python3
"""Compatibility wrapper for ``uv run satyrn-evals-interleave``."""

from satyrn_evals.interleave import main

if __name__ == "__main__":
    raise SystemExit(main())
