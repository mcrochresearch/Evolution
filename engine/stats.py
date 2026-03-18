"""Shared statistical utilities for the Evolution engine.

Consolidates wilson_lower, wilson_score, sample_sd, effect_size, and now()
which were previously duplicated across state.py, analyze.py, and skillforge.py.
"""

import math
from datetime import datetime, timezone


def now() -> str:
    """Return the current UTC time as an ISO 8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


def wilson_lower(successes: int, total: int, z: float = 1.96) -> float:
    """Wilson score lower bound -- conservative success rate estimate.

    Useful for ranking items by quality when sample sizes vary.
    With the default *z* = 1.96 the bound corresponds to a 95 %
    confidence level.
    """
    if total == 0:
        return 0.0
    phat = successes / total
    denom = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denom
    spread = z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total) / denom
    return max(0, round(center - spread, 4))


def wilson_score(successes: int, total: int, z: float = 1.96) -> tuple:
    """Wilson score confidence interval for a binomial proportion.

    More statistically rigorous than a simple successes/total ratio,
    especially for small sample sizes.

    Returns:
        (lower, upper) bounds as a tuple of floats.
    """
    if total == 0:
        return (0.0, 1.0)
    phat = successes / total
    denominator = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denominator
    spread = z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total) / denominator
    return (max(0, round(center - spread, 4)), min(1, round(center + spread, 4)))


def sample_sd(values: list) -> float:
    """Compute sample standard deviation (Bessel-corrected).

    Uses *n - 1* in the denominator so the result is an unbiased
    estimator of the population standard deviation.  Returns 0.0 when
    fewer than two values are provided.
    """
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((x - mean) ** 2 for x in values) / (n - 1))


def effect_size(group1: list, group2: list) -> float:
    """Cohen's d effect size between two groups using Bessel-corrected pooled SD.

    Returns the magnitude of difference in standard deviation units:
        - < 0.2:   negligible
        - 0.2-0.5: small
        - 0.5-0.8: medium
        - > 0.8:   large
    """
    if not group1 or not group2:
        return 0.0
    n1, n2 = len(group1), len(group2)
    mean1, mean2 = sum(group1) / n1, sum(group2) / n2
    # Bessel-corrected sample variance (divide by n-1)
    var1 = sum((x - mean1) ** 2 for x in group1) / max(n1 - 1, 1)
    var2 = sum((x - mean2) ** 2 for x in group2) / max(n2 - 1, 1)
    # Pooled SD weighted by degrees of freedom
    pooled_sd = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / max(n1 + n2 - 2, 1))
    if pooled_sd == 0:
        return 0.0
    return round((mean1 - mean2) / pooled_sd, 3)
