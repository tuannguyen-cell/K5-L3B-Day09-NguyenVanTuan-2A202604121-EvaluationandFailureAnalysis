"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge) or not human:
        raise ValueError("labels must be nonempty and paired")
    out = dict(tp=0, fp=0, fn=0, tn=0)
    for h, j in zip(human, judge):
        if h not in {"PASS", POS} or j not in {"PASS", POS}:
            raise ValueError("labels must be PASS or FAIL")
        out[("t" if h == j else "f") + ("p" if j == POS else "n")] += 1
    return out


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    c = confusion(human, judge)
    return (c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else 0.0,
            c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else 0.0)


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    c = confusion(human, judge)
    n = len(human)
    po = (c["tp"] + c["tn"]) / n
    pe = ((c["tp"] + c["fn"]) * (c["tp"] + c["fp"])
          + (c["tn"] + c["fp"]) * (c["tn"] + c["fn"])) / n**2
    if pe == 1:
        raise ValueError("kappa is undefined")
    return (po - pe) / (1 - pe)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    import math
    if any(not math.isfinite(x) or not 0 <= x <= 1 for x in (observed_rate, sensitivity, specificity)):
        raise ValueError("rates must be finite probabilities")
    denominator = sensitivity + specificity - 1
    if denominator <= 0:
        raise ValueError("judge has no positive discriminatory signal")
    return min(1.0, max(0.0, (observed_rate + specificity - 1) / denominator))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.ndim != 1 or b.ndim != 1 or len(a) != len(b) or not len(a):
        raise ValueError("bootstrap needs nonempty paired vectors")
    if not np.isfinite(a).all() or not np.isfinite(b).all() or not 0 < confidence < 1 or n_resamples < 1:
        raise ValueError("invalid bootstrap input")
    delta = float(np.mean(a - b))
    if np.all(a == b):
        return 0.0, 0.0, 0.0
    if len(a) == 1:
        return delta, delta, delta
    result = bootstrap((a, b), lambda x, y, axis: np.mean(x - y, axis=axis), paired=True,
                       method="percentile", n_resamples=n_resamples, confidence_level=confidence,
                       rng=np.random.default_rng(rng))
    return delta, float(result.confidence_interval.low), float(result.confidence_interval.high)


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    from math import comb
    _validate_trials(n, c, k)
    return 1 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    from math import comb
    _validate_trials(n, c, k)
    return comb(c, k) / comb(n, k)


def _validate_trials(n: int, c: int, k: int) -> None:
    if any(type(x) is not int for x in (n, c, k)) or not (n >= 1 and 0 <= c <= n and 1 <= k <= n):
        raise ValueError("require integers n >= 1, 0 <= c <= n, 1 <= k <= n")
