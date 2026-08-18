"""Capture orchestration: turn a fixing commit into a valid task.

Task 6 defines `slugify_subject`; the full lifecycle lands with capture().
"""

import re

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify_subject(subject: str) -> str | None:
    """Task-name slug from a commit subject; None when underivable."""
    slug = _SLUG_RE.sub("-", subject.strip().lower()).strip("-")
    return slug or None
