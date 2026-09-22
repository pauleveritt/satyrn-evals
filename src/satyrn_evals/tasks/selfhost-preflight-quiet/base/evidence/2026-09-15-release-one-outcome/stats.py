#!/usr/bin/env python3
"""Decision-rule arithmetic for release one (one-sided Fisher, n = 12 per arm).

Prints: the minimum Engine passes that reject at alpha = 0.05 for each
Baseline count; power at n = 12 for a grid of (baseline p, engine p);
probability of clearing the futility look (Engine >= 2 of 6) for a given
engine p; and the probability that >= 2 of 3 tasks reject under a given
per-task rejection probability.
"""
from math import comb


def fisher_one_sided(a, b, n1, n2):
    """P(X >= a | margins) with X ~ hypergeom: a passes in arm 1 of n1, b in arm 2 of n2."""
    k = a + b
    N = n1 + n2
    tot = comb(N, k)
    p = 0.0
    for x in range(a, min(k, n1) + 1):
        y = k - x
        if 0 <= y <= n2:
            p += comb(n1, x) * comb(n2, y) / tot
    return p


def min_engine_for_reject(b, n=12, alpha=0.05):
    for a in range(b, n + 1):
        if fisher_one_sided(a, b, n, n) <= alpha:
            return a
    return None


def binom(k, n, p):
    return comb(n, k) * p**k * (1 - p) ** (n - k)


def power(pb, pe, n=12, alpha=0.05):
    tot = 0.0
    for b in range(n + 1):
        for a in range(n + 1):
            if fisher_one_sided(a, b, n, n) <= alpha:
                tot += binom(b, n, pb) * binom(a, n, pe)
    return tot


def main():
    print("min Engine passes (of 12) to reject at alpha 0.05, by Baseline passes:")
    for b in range(0, 4):
        a = min_engine_for_reject(b)
        print(f"  Baseline {b}/12 -> Engine >= {a}/12  (p = {fisher_one_sided(a, b, 12, 12):.4f})")
    print()
    print("power at n = 12 (no futility look), rows = engine p, cols = baseline p")
    pbs = [0.0, 0.05, 0.10, 0.15, 0.25]
    print("  pe\\pb " + " ".join(f"{pb:>6.2f}" for pb in pbs))
    for pe in [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80]:
        print(f"  {pe:>5.2f} " + " ".join(f"{power(pb, pe):>6.2f}" for pb in pbs))
    print()
    print("P(Engine >= 2 of 6 at the futility look) by engine p:")
    for pe in [0.10, 0.20, 0.30, 0.40, 0.50, 0.60]:
        p = 1 - binom(0, 6, pe) - binom(1, 6, pe)
        print(f"  pe {pe:.2f}: {p:.2f}")
    print()
    print("P(at least 2 of 3 tasks reject) by per-task rejection probability r:")
    for r in [0.05, 0.2, 0.3, 0.4, 0.5, 0.6, 0.79]:
        p = 3 * r**2 * (1 - r) + r**3
        print(f"  r {r:.2f}: {p:.3f}")


if __name__ == "__main__":
    main()
