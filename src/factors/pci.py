# src/factors/pci.py
# Utilities to compute a simple PCI (pairwise complementarity index) and standardized variants.
# The PCI implemented here is intentionally interpretable: it measures the relative magnitude
# of two-factor interaction effects compared to additive effects.

from __future__ import annotations

from typing import Tuple, Optional
import numpy as np
import pandas as pd


def interaction_matrix_from_cell_means(cell_means: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the two-way interaction residuals matrix:
      I_{ij} = cell_mean_{ij} - row_mean_i - col_mean_j + overall_mean

    Returns a DataFrame with same index/columns as cell_means.
    """
    overall = float(np.nanmean(cell_means.values))
    row_means = cell_means.mean(axis=1)
    col_means = cell_means.mean(axis=0)
    I = cell_means.copy()
    for i in cell_means.index:
        for j in cell_means.columns:
            mij = cell_means.loc[i, j]
            if np.isnan(mij):
                I.loc[i, j] = np.nan
            else:
                I.loc[i, j] = mij - row_means.loc[i] - col_means.loc[j] + overall
    return I


def pci_simple(
    cell_means: pd.DataFrame,
    normalize: bool = True,
    eps: float = 1e-9,
) -> float:
    """
    Compute a simple PCI:
      PCI = sum_abs_interactions / sum_abs_cell_means

    If normalize=True, returns a value in [0, +inf) but typically <= 1 when interactions are
    smaller than main cell magnitudes.

    Parameters
    ----------
    cell_means :
        DataFrame of cell means.
    normalize :
        If True, divide by sum absolute cell means to get a relative index.
    eps :
        Small constant to avoid division by zero.

    Returns
    -------
    float
        PCI score (higher => more complementarity / interaction).
    """
    I = interaction_matrix_from_cell_means(cell_means)
    sum_abs_I = float(np.nansum(np.abs(I.values)))
    if not normalize:
        return sum_abs_I
    denom = float(np.nansum(np.abs(cell_means.values)))
    if denom <= eps:
        return 0.0
    return sum_abs_I / denom


def pci_by_variance_share(cell_means: pd.DataFrame) -> Tuple[float, float, float]:
    """
    Decompose total variance of cell means into additive and interaction components using ANOVA-like sums:
      total_var = var(cell_means)
      additive_fit = row_mean + col_mean - overall_mean
    Returns (interaction_variance, additive_variance, total_variance) where each is non-negative.

    This is a descriptive decomposition useful for reporting sample complexity and PCI interpretation.
    """
    # Vectorize valid entries
    mask = ~np.isnan(cell_means.values)
    values = cell_means.values.copy()
    values[~mask] = 0.0
    overall = float(np.nanmean(cell_means.values))
    row_means = cell_means.mean(axis=1).reindex(cell_means.index).values[:, None]
    col_means = cell_means.mean(axis=0).reindex(cell_means.columns).values[None, :]

    additive = row_means + col_means - overall
    residuals = values - additive
    # Only account entries that were present originally
    total_var = float(np.nanvar(cell_means.values))
    additive_var = float(np.nanvar(np.where(mask, additive, np.nan)))
    interaction_var = float(np.nanvar(np.where(mask, residuals, np.nan)))
    # Ensure non-negative and return
    total_var = max(total_var, 0.0)
    additive_var = max(additive_var, 0.0)
    interaction_var = max(interaction_var, 0.0)
    return interaction_var, additive_var, total_var
