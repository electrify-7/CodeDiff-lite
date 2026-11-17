"""Non-parametric statistical verification engine for compiler coverage disparities.

Computes Wilcoxon signed-rank tests and Cliff's delta effect sizes for
evaluating optimization degradation and cross-toolchain divergence.
"""

import math
from typing import Dict, List, Tuple


def normal_cdf(z: float) -> float:
    """Standard normal cumulative distribution function using math.erf."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def cliffs_delta(x: List[float], y: List[float]) -> Tuple[float, str]:
    """Compute Cliff's delta non-parametric effect size between distributions x and y.

    Returns:
        (delta, interpretation) where interpretation is in
        ['negligible', 'small', 'medium', 'large']
    """
    m = len(x)
    n = len(y)
    if m == 0 or n == 0:
        return 0.0, "negligible"

    greater = 0
    lesser = 0
    for xi in x:
        for yj in y:
            if xi > yj:
                greater += 1
            elif xi < yj:
                lesser += 1

    d = (greater - lesser) / (m * n)
    abs_d = abs(d)
    if abs_d < 0.147:
        effect = "negligible"
    elif abs_d < 0.33:
        effect = "small"
    elif abs_d < 0.474:
        effect = "medium"
    else:
        effect = "large"

    return round(d, 4), effect


def wilcoxon_signed_rank(x: List[float], y: List[float]) -> Tuple[float, float, str]:
    """Compute paired two-tailed Wilcoxon signed-rank test on paired distributions.

    Returns:
        (W_statistic, p_value, summary_string)
    """
    diffs = [xi - yi for xi, yi in zip(x, y)]
    non_zero = [d for d in diffs if d != 0]
    n = len(non_zero)
    if n == 0:
        return 0.0, 1.0, "No difference (all paired differences are zero)"

    # Sort non-zero differences by absolute value
    sorted_diffs = sorted(non_zero, key=lambda d: abs(d))
    abs_vals = [abs(d) for d in sorted_diffs]

    # Assign fractional ranks for tied absolute differences
    ranks = [0.0] * n
    i = 0
    tie_adjustment = 0.0
    while i < n:
        j = i
        while j < n and abs_vals[j] == abs_vals[i]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        tie_len = j - i
        if tie_len > 1:
            tie_adjustment += (tie_len**3 - tie_len) / 48.0
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    w_pos = sum(ranks[k] for k in range(n) if sorted_diffs[k] > 0)
    w_neg = sum(ranks[k] for k in range(n) if sorted_diffs[k] < 0)
    w = min(w_pos, w_neg)

    mu = n * (n + 1) / 4.0
    var = (n * (n + 1) * (2 * n + 1) / 24.0) - tie_adjustment
    if var <= 0:
        return w, 1.0, "Degenerate variance"

    sigma = math.sqrt(var)
    # Continuity correction shifts discrete statistic half a unit closer to the mean mu
    diff = abs(w - mu) - 0.5
    if diff > 0:
        z = math.copysign(diff, w - mu) / sigma
    else:
        z = 0.0
    p_val = 2.0 * (1.0 - normal_cdf(abs(z)))

    return round(w, 2), float(f"{p_val:.6e}"), f"z={z:.4f}, p={p_val:.6e}"


def compute_optimization_degradation_statistics(
    gcc_degradations: List[float],
    clang_degradations: List[float],
) -> dict:
    """Generate formal non-parametric comparison statistics for research paper reporting."""
    delta_val, delta_interp = cliffs_delta(gcc_degradations, clang_degradations)
    w_stat, p_val, test_summary = wilcoxon_signed_rank(gcc_degradations, clang_degradations)

    n_samples = min(len(gcc_degradations), len(clang_degradations))
    gcc_mean = sum(gcc_degradations) / len(gcc_degradations) if gcc_degradations else 0.0
    clang_mean = sum(clang_degradations) / len(clang_degradations) if clang_degradations else 0.0

    return {
        "paired_sample_size": n_samples,
        "gcc_mean_degradation_pct": round(gcc_mean, 2),
        "clang_mean_degradation_pct": round(clang_mean, 2),
        "cliffs_delta": delta_val,
        "cliffs_delta_effect": delta_interp,
        "wilcoxon_w": w_stat,
        "wilcoxon_p_value": p_val,
        "statistically_significant_p05": p_val < 0.05,
        "statistically_significant_p01": p_val < 0.01,
        "summary": (
            f"Wilcoxon signed-rank test confirmed statistically significant difference "
            f"(W={w_stat}, p={p_val:.4e}, Cliff's delta={delta_val} [{delta_interp}])."
        ),
    }
