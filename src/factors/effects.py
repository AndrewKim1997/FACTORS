# src/factors/effects.py
# Utilities to estimate main effects and two-factor interaction effects from tabular data.
# The implementations are simple, dependency-light, and intended for reproducible experiment code.

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Iterable, Tuple, Dict, Optional


def estimate_main_effects(
    df: pd.DataFrame,
    factor_cols: Iterable[str],
    outcome_col: str,
    groupby_weights_col: Optional[str] = None,
) -> Dict[str, pd.Series]:
    """
    Estimate marginal means (main effects) for each categorical factor.

    Parameters
    ----------
    df :
        DataFrame containing data.
    factor_cols :
        Iterable of column names for categorical factors to analyze.
    outcome_col :
        Name of the numeric outcome column.
    groupby_weights_col :
        Optional column name in df with sample weights to compute weighted means.
        If None, unweighted means are computed.

    Returns
    -------
    dict
        Mapping factor_name -> pandas.Series indexed by factor level containing marginal means.
    """
    effects: Dict[str, pd.Series] = {}
    for f in factor_cols:
        if groupby_weights_col is None:
            grp = df.groupby(f)[outcome_col].mean()
        else:
            # weighted mean: sum(w * y) / sum(w)
            s = df.groupby(f).apply(
                lambda g: (g[outcome_col] * g[groupby_weights_col]).sum()
                / (g[groupby_weights_col].sum() if g[groupby_weights_col].sum() != 0 else np.nan)
            )
            grp = s
        effects[f] = grp.sort_index()
    return effects


def estimate_two_factor_cell_means(
    df: pd.DataFrame, factor_a: str, factor_b: str, outcome_col: str
) -> pd.DataFrame:
    """
    Compute cell means for a 2-factor table.

    Parameters
    ----------
    df :
        DataFrame containing data
    factor_a :
        Column name for factor A (row factor)
    factor_b :
        Column name for factor B (column factor)
    outcome_col :
        Outcome variable to average

    Returns
    -------
    pandas.DataFrame
        DataFrame indexed by levels of factor_a and with columns equal to levels of factor_b.
        Missing cells are filled with NaN.
    """
    cell_means = df.groupby([factor_a, factor_b])[outcome_col].mean().unstack(level=factor_b)
    return cell_means


def two_factor_interaction_matrix(
    cell_means: pd.DataFrame,
    effect_center: str = "overall",
) -> pd.DataFrame:
    """
    Given a two-factor cell mean table, compute the interaction matrix
    defined as: interaction_{ij} = cell_mean_{ij} - row_mean_i - col_mean_j + overall_mean.

    This is the classical two-way interaction residuals from additive model.

    Parameters
    ----------
    cell_means :
        DataFrame with rows corresponding to factor A levels and columns to factor B levels.
    effect_center :
        How to center the effects. Only 'overall' is currently supported (subtracts overall mean).

    Returns
    -------
    pandas.DataFrame
        Interaction matrix with same index/columns as input.
    """
    if effect_center != "overall":
        raise ValueError("effect_center currently supports only 'overall'")

    overall_mean = cell_means.values[~np.isnan(cell_means.values)].mean()
    row_means = cell_means.mean(axis=1)
    col_means = cell_means.mean(axis=0)

    # Broadcast to compute interaction residuals
    interaction = cell_means.copy()
    for i in cell_means.index:
        for j in cell_means.columns:
            mij = cell_means.loc[i, j]
            if np.isnan(mij):
                interaction.loc[i, j] = np.nan
            else:
                interaction.loc[i, j] = mij - row_means.loc[i] - col_means.loc[j] + overall_mean
    return interaction
