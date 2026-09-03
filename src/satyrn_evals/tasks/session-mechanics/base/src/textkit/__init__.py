"""Tiny text helpers the session extends."""


def normalize(text: str) -> str:
    """Collapse internal whitespace and strip the ends."""
    return " ".join(text.split())


def wrap(text: str, width: int) -> str:
    """Break text into width-limited lines on word boundaries."""
    out: list[str] = []
    for word in text.split():
        if out and len(out[-1]) + 1 + len(word) > width:
            out.append(word)
        else:
            out.append(f"{out[-1]} {word}".strip() if out else word)
    return "\n".join(out)
