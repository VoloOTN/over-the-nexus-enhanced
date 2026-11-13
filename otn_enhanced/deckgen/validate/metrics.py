"""Statistics, implemented locally so the tool needs no scipy.

Everything here is rank- or resampling-based, which suits the question: deck
"strength" is ordinal, the samples are small (305 decks, fewer per tier), and
nothing is remotely normal.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


def ranks(xs: list[float]) -> list[float]:
    """Average ranks, ties shared."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (dx * dy) if dx and dy else 0.0


def spearman(xs: list[float], ys: list[float]) -> float:
    """Rank correlation."""
    return pearson(ranks(xs), ranks(ys))


def kendall_tau_b(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    conc = disc = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = xs[i] - xs[j], ys[i] - ys[j]
            if a == 0 and b == 0:
                continue
            if a == 0:
                tx += 1
            elif b == 0:
                ty += 1
            elif (a > 0) == (b > 0):
                conc += 1
            else:
                disc += 1
    denom = math.sqrt((conc + disc + tx) * (conc + disc + ty))
    return (conc - disc) / denom if denom else 0.0


def auc(pos: list[float], neg: list[float]) -> float:
    """Mann-Whitney AUC: P(a random *pos* scores above a random *neg*)."""
    if not pos or not neg:
        return float("nan")
    wins = 0.0
    for a in pos:
        for b in neg:
            wins += 1.0 if a > b else 0.5 if a == b else 0.0
    return wins / (len(pos) * len(neg))


def wilcoxon_signed_rank_p(a: list[float], b: list[float], iters: int = 20000,
                           rng: random.Random | None = None) -> float:
    """Two-sided p for "a and b are paired samples from the same distribution".

    Uses a sign-flip permutation rather than the asymptotic normal approximation,
    which is unreliable with the many zero differences deck overlap produces.
    """
    rng = rng or random.Random(0)
    diffs = [x - y for x, y in zip(a, b) if x != y]
    if not diffs:
        return 1.0
    observed = abs(sum(diffs))
    hits = 0
    for _ in range(iters):
        total = sum(d if rng.random() < 0.5 else -d for d in diffs)
        if abs(total) >= observed:
            hits += 1
    return (hits + 1) / (iters + 1)


def permutation_p(xs: list[float], ys: list[float], iters: int = 10000,
                  rng: random.Random | None = None) -> float:
    """Two-sided p for "spearman(xs, ys) is no better than chance"."""
    rng = rng or random.Random(0)
    observed = abs(spearman(xs, ys))
    shuffled = list(ys)
    hits = 0
    for _ in range(iters):
        rng.shuffle(shuffled)
        if abs(spearman(xs, shuffled)) >= observed:
            hits += 1
    return (hits + 1) / (iters + 1)


@dataclass
class CI:
    low: float
    high: float

    def __str__(self) -> str:
        return f"[{self.low:+.3f}, {self.high:+.3f}]"

    def excludes_zero(self) -> bool:
        return self.low > 0 or self.high < 0


def bootstrap_spearman_ci(
    xs: list[float], ys: list[float], iters: int = 10000, alpha: float = 0.05,
    rng: random.Random | None = None,
) -> CI:
    rng = rng or random.Random(0)
    n = len(xs)
    stats: list[float] = []
    for _ in range(iters):
        pick = [rng.randrange(n) for _ in range(n)]
        stats.append(spearman([xs[i] for i in pick], [ys[i] for i in pick]))
    stats.sort()
    lo = stats[int(alpha / 2 * iters)]
    hi = stats[min(iters - 1, int((1 - alpha / 2) * iters))]
    return CI(lo, hi)


def median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2.0
