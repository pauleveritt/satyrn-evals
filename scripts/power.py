#!/usr/bin/env python
"""Exact power for a one-sided Fisher exact test on two independent binomials.

Instrument, not production code: it lives outside ``src/satyrn_evals`` and is
covered by ``tests/test_power.py``.

**Why exact, and not an approximation.** At the sample sizes this project can
afford, a normal approximation is wrong in the direction that flatters the
design -- it reports more power than the test actually has, and a design
justified by an inflated number is a design that cannot find what it claims to
look for. This enumerates instead: every ``(x_baseline, x_engine)`` outcome is
weighted by its probability under the stated alternative, and the weights of
the tables Fisher would reject are summed. No simulation, no closed form, no
seed.

**What the number assumes**, and what a caller must therefore state beside it:

1. attempts are **independent** within and across arms;
2. each arm has a **fixed underlying success probability** for the duration --
   no drift in machine state, model, or condition;
3. the analysis is the **one-sided Fisher exact test** at the stated ``alpha``,
   on **one** primary contrast, decided before the data;
4. the alternative ``(p_baseline, p_engine)`` is a *stipulated* effect worth
   detecting, not an estimate carried over from an earlier batch. Powering
   against a previously observed effect overstates power, because the observed
   effect of an underpowered batch is biased upward -- the winner's curse.

Numbers produced here are properties of a design, never of a result. Reporting
"observed power" after seeing an outcome is not a use this file supports.
"""

from __future__ import annotations

import argparse
from itertools import product
from math import comb

type Probability = float

DEFAULT_ALPHA: Probability = 0.05


def fisher_one_sided(successes_a: int, successes_b: int, n: int) -> Probability:
    """``P(X_b >= successes_b)`` given both margins, the hypergeometric tail."""
    total = successes_a + successes_b
    high = min(n, total)
    denominator = comb(2 * n, total)
    return (
        sum(comb(n, k) * comb(n, total - k) for k in range(successes_b, high + 1))
        / denominator
    )


def power(
    n: int, p_a: Probability, p_b: Probability, alpha: Probability = DEFAULT_ALPHA
) -> Probability:
    """Probability the one-sided test rejects, with ``n`` attempts per arm.

    ``p_a`` is the reference arm's success probability and ``p_b`` the arm the
    alternative favours; the test asks whether arm B exceeds arm A.
    """
    if n < 1:
        raise ValueError("each arm needs at least one attempt")
    if not all(0.0 <= p <= 1.0 for p in (p_a, p_b, alpha)):
        raise ValueError("probabilities must lie in [0, 1]")
    rejects: dict[tuple[int, int], bool] = {}
    total = 0.0
    for x_a, x_b in product(range(n + 1), repeat=2):
        if (decision := rejects.get((x_a, x_b))) is None:
            decision = rejects[(x_a, x_b)] = fisher_one_sided(x_a, x_b, n) <= alpha
        if decision:
            total += (
                comb(n, x_a) * p_a**x_a * (1 - p_a) ** (n - x_a)
                * comb(n, x_b) * p_b**x_b * (1 - p_b) ** (n - x_b)
            )
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, required=True, help="attempts per arm")
    parser.add_argument("--p-reference", type=float, required=True)
    parser.add_argument("--p-alternative", type=float, required=True)
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    args = parser.parse_args(argv)
    value = power(args.n, args.p_reference, args.p_alternative, args.alpha)
    print(
        f"power={value:.3f}  n={args.n} per arm  "
        f"{args.p_reference:.2f}->{args.p_alternative:.2f}  "
        f"one-sided Fisher exact, alpha={args.alpha}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
