"""One review, one model, one file. Refuses to write a second review of the
same range; delete the first if you truly need another, and that shows in git.
"""

import subprocess
import sys
from pathlib import Path

PROMPT = """Review the commit range {range_label} of this repository against the
release-one design (docs/superpowers/specs/2026-09-13-release-one-design.md),
BRIEF.md's invariants and comparison policy, and AGENTS.md. Verify claims by
reading the tree, not the commit messages. Return exactly one verdict line —
`Accept` or `Send back` — followed by an itemized list of what must change,
each item naming file:line. No second-order commentary.

{diff}
"""


def _slug(value: str) -> str:
    return value.replace("/", "-")


def review_path(root: Path, commit_range: str, model: str) -> Path:
    return root / "docs" / "reviews" / f"{_slug(commit_range)}-{_slug(model)}.md"


def refuse_if_exists(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"a review already exists at {path}; delete it deliberately to review again")


def provider_and_model(spec: str) -> tuple[str, str]:
    if "/" not in spec:
        raise ValueError(f"model must be given as provider/model, got {spec!r}")
    provider, model = spec.split("/", 1)
    return provider, model


def build_prompt(diff: str, range_label: str) -> str:
    return PROMPT.format(range_label=range_label, diff=diff)


def normalize_document(text: str) -> str:
    if not text:
        return text
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: review.py COMMIT_RANGE PROVIDER/MODEL", file=sys.stderr)
        return 2
    commit_range, spec = argv
    root = Path.cwd()
    try:
        path = review_path(root, commit_range, spec)
        refuse_if_exists(path)
        provider, model = provider_and_model(spec)
        diff = subprocess.run(["git", "diff", commit_range], check=True, capture_output=True, text=True).stdout
        prompt = build_prompt(diff, commit_range)
        result = subprocess.run(
            ["pi", "-p", "--no-session", "--no-extensions", "--no-skills", "-nc",
             "--provider", provider, "--model", model, "--exclude-tools", "write,edit", prompt],
            check=True, capture_output=True, text=True)
    except (FileExistsError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        stderr = e.stderr
        if isinstance(stderr, bytes):
            stderr = stderr.decode()
        print(stderr or str(e), file=sys.stderr)
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalize_document(f"<!-- {commit_range} reviewed by {spec} -->\n\n{result.stdout}"))
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
