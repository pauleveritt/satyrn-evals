"""Operating characteristics of Phase 4's per-task stopping rule, computed exactly.

The spec's "Sample and decision rule" cites the numbers this prints: a
one-sided Fisher test at n = 12 per arm with one futility look at 6, compared
with a fixed n = 12 and with an early-win look that the design rejected, plus
the held-out loss tripwire at n = 6. No model, network, or subprocess.

Status 2026-09-15: these scenarios assume release one's four-then-three
ceiling tasks and a stipulated 0.10 vs 0.60 effect, which release one's
admission did not support (`2026-09-15-release-one-outcome.md`). Evidence,
not a current design input.

    uv run python scripts/seq_design.py
"""

from math import comb


def fisher_greater(b: int, e: int, n_b: int, n_e: int) -> float:
    """One-sided p that the second arm is better: P(E >= e | total passes)."""
    t = b + e
    total = n_b + n_e
    top = min(t, n_e)
    return sum(comb(n_e, k) * comb(n_b, t - k) for k in range(e, top + 1)) / comb(
        total, t
    )


def binom(n: int, k: int, p: float) -> float:
    return comb(n, k) * p**k * (1 - p) ** (n - k)


def fixed(pb: float, pe: float, n: int = 12, alpha: float = 0.05) -> float:
    """Power of a fixed-n one-sided Fisher test for Engine better."""
    return sum(
        binom(n, b, pb) * binom(n, e, pe)
        for b in range(n + 1)
        for e in range(n + 1)
        if fisher_greater(b, e, n, n) <= alpha
    )


def two_stage(
    pb: float,
    pe: float,
    *,
    n1: int = 6,
    n: int = 12,
    a1: float = -1.0,
    a2: float = 0.05,
    futility: int = 1,
) -> tuple[float, float, float]:
    """P(win), P(stop at the look), expected cells across both arms."""
    win = stopped = 0.0
    rest = n - n1
    for b1 in range(n1 + 1):
        for e1 in range(n1 + 1):
            pr = binom(n1, b1, pb) * binom(n1, e1, pe)
            if fisher_greater(b1, e1, n1, n1) <= a1:
                win += pr
                stopped += pr
                continue
            if e1 <= futility:
                stopped += pr
                continue
            for b2 in range(rest + 1):
                for e2 in range(rest + 1):
                    if fisher_greater(b1 + b2, e1 + e2, n, n) <= a2:
                        win += pr * binom(rest, b2, pb) * binom(rest, e2, pe)
    return win, stopped, 2 * n1 * stopped + 2 * n * (1 - stopped)


SCENARIOS = [(0.1, 0.1), (0.25, 0.25), (0.1, 0.6), (0.0, 0.5), (0.25, 0.75), (0.1, 0.4)]


def main() -> None:
    print("futility look only (the rule): stop at 6 per arm if Engine <= 1 of 6")
    for pb, pe in SCENARIOS:
        w, s, cells = two_stage(pb, pe)
        print(
            f"  Baseline {pb:.2f} Engine {pe:.2f}: P(win) {w:.3f}, P(stop at 6) {s:.2f}, "
            f"expected cells {cells:.1f}, fixed n=12 power {fixed(pb, pe):.3f}"
        )
    print("early-win look as well (rejected): win at 6 if p <= 0.01, else 0.04 at 12")
    for pb, pe in SCENARIOS:
        w, s, cells = two_stage(pb, pe, a1=0.01, a2=0.04)
        print(
            f"  Baseline {pb:.2f} Engine {pe:.2f}: P(win) {w:.3f}, P(stop at 6) {s:.2f}, expected cells {cells:.1f}"
        )
    print("held-out loss tripwire, n = 6 per arm, alpha 0.05")
    for pb, pe in [(0.6, 0.1), (0.5, 0.5), (0.25, 0.25)]:
        print(f"  Baseline {pb:.2f} Engine {pe:.2f}: P(loss) {fixed(pe, pb, n=6):.3f}")


if __name__ == "__main__":
    main()
