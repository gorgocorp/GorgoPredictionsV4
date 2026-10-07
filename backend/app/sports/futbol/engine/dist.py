"""Distribuciones de conteo: Poisson y binomial negativa (parametrizada por media y varianza)."""

import math


def pmf_list(mean: float, var: float, k_max: int) -> list[float]:
    """P(X = 0..k_max) con X ~ binomial negativa (o Poisson si var <= media)."""
    if mean <= 0:
        return [1.0] + [0.0] * k_max
    out = []
    if var <= mean * 1.0001:
        pmf = math.exp(-mean)
        out.append(pmf)
        for i in range(1, k_max + 1):
            pmf *= mean / i
            out.append(pmf)
        return out
    r = mean * mean / (var - mean)
    p = r / (r + mean)
    pmf = math.exp(r * math.log(p))
    out.append(pmf)
    for i in range(1, k_max + 1):
        pmf *= (i - 1 + r) / i * (1.0 - p)
        out.append(pmf)
    return out


def prob_at_least(mean: float, var: float, k: int) -> float:
    """P(X >= k)."""
    if k <= 0:
        return 1.0
    if mean <= 0:
        return 0.0
    cdf = sum(pmf_list(mean, var, k - 1))
    return min(1.0, max(0.0, 1.0 - cdf))


def prob_over(mean: float, var: float, line: float) -> float:
    """P(X > line) para líneas de medio punto (2.5 -> 3 o más)."""
    return prob_at_least(mean, var, math.floor(line) + 1)


def poisson_pmf(mean: float, k_max: int) -> list[float]:
    return pmf_list(mean, mean, k_max)
