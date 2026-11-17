"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb

import numpy as np
from scipy import stats as scipy_stats

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    tp = fp = fn = tn = 0
    for h, j in zip(human, judge):
        h_pos = str(h).strip().upper() == POS
        j_pos = str(j).strip().upper() == POS
        if h_pos and j_pos:
            tp += 1
        elif not h_pos and j_pos:
            fp += 1
        elif h_pos and not j_pos:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    precision = cm["tp"] / (cm["tp"] + cm["fp"]) if (cm["tp"] + cm["fp"]) else 0.0
    recall = cm["tp"] / (cm["tp"] + cm["fn"]) if (cm["tp"] + cm["fn"]) else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    cm = confusion(human, judge)
    n = cm["tp"] + cm["fp"] + cm["fn"] + cm["tn"]
    if n == 0:
        raise ValueError("undefined kappa: empty labels")
    p_o = (cm["tp"] + cm["tn"]) / n
    p_h_pos = (cm["tp"] + cm["fn"]) / n
    p_j_pos = (cm["tp"] + cm["fp"]) / n
    p_e = p_h_pos * p_j_pos + (1 - p_h_pos) * (1 - p_j_pos)
    if p_e == 1:
        raise ValueError("undefined kappa: p_e == 1 (constant labels)")
    return (p_o - p_e) / (1 - p_e)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    den = sensitivity + specificity - 1
    if den == 0:
        return 0.0
    raw = (observed_rate + specificity - 1) / den
    return float(max(0.0, min(1.0, raw)))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    aa = [float(x) for x in a]
    bb = [float(x) for x in b]
    if aa == bb:
        return (0.0, 0.0, 0.0)
    xa = np.asarray(aa, dtype=float)
    xb = np.asarray(bb, dtype=float)
    d = float(xa.mean() - xb.mean())
    res = scipy_stats.bootstrap(
        (xa, xb),
        statistic=lambda x, y: np.mean(x) - np.mean(y),
        n_resamples=n_resamples,
        paired=True,
        method="percentile",
        confidence_level=confidence,
        random_state=np.random.default_rng(rng),
    )
    lo = float(res.confidence_interval.low)
    hi = float(res.confidence_interval.high)
    return (d, lo, hi)


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    if k < 1 or n < 1 or c < 0 or c > n or k > n:
        raise ValueError(f"invalid pass_at_k args n={n} c={c} k={k}")
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    if k < 1 or n < 1 or c < 0 or c > n or k > n:
        raise ValueError(f"invalid pass_hat_k args n={n} c={c} k={k}")
    if c < k:
        return 0.0
    return comb(c, k) / comb(n, k)
