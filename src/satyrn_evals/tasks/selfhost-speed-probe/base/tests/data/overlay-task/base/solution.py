def normalize(text: str) -> str:
    """Collapse internal whitespace and strip the ends."""
    return " ".join(text.split())
