"""Regresión de Poisson con penalización ridge sobre un diseño ralo.

Cada observación activa pocas columnas (intercepto, localía, equipo, rival, liga…), así que el
diseño se guarda como dos matrices (n, K): índices de columna y valores. Las ecuaciones normales
se acumulan con `np.bincount`, sin construir la matriz completa (miles de columnas).

Minimiza  Σ w·(μ − y·log μ) + ½ Σ ridge_j·β_j²   con  log μ = Σ_k β[cols_k]·vals_k
por Newton-Raphson. `y` puede ser no entero (p. ej. una mezcla de goles y xG): es la versión
cuasi-Poisson, con la misma media y los mismos estimadores.
"""

import numpy as np


def fit_poisson_ridge(
    cols: np.ndarray,
    vals: np.ndarray,
    y: np.ndarray,
    w: np.ndarray,
    penalty: np.ndarray,
    beta0: np.ndarray | None = None,
    max_iter: int = 30,
    tol: float = 1e-7,
) -> np.ndarray:
    n_params = len(penalty)
    beta = np.zeros(n_params) if beta0 is None else beta0.astype(float).copy()
    # Penalización mínima para que columnas sin datos no hagan singular el sistema.
    pen = np.maximum(penalty, 1e-6)
    flat_pairs = (cols[:, :, None] * n_params + cols[:, None, :]).ravel()
    pair_vals = vals[:, :, None] * vals[:, None, :]
    for _ in range(max_iter):
        eta = (beta[cols] * vals).sum(axis=1)
        mu = np.exp(np.clip(eta, -20, 20))
        resid = w * (mu - y)
        grad = np.bincount(cols.ravel(), weights=(vals * resid[:, None]).ravel(), minlength=n_params) + pen * beta
        hess = np.bincount(
            flat_pairs, weights=((w * mu)[:, None, None] * pair_vals).ravel(), minlength=n_params * n_params
        ).reshape(n_params, n_params)
        hess[np.diag_indices(n_params)] += pen
        step = np.linalg.solve(hess, grad)
        # Amortigua pasos grandes en las primeras iteraciones (inicio lejos del óptimo).
        biggest = np.abs(step).max()
        if biggest > 1.0:
            step /= biggest
        beta -= step
        if biggest < tol:
            break
    return beta


def predict_log_mean(beta: np.ndarray, cols: np.ndarray, vals: np.ndarray) -> np.ndarray:
    return (beta[cols] * vals).sum(axis=1)
