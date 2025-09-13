# src/factors/score.py
# Functions to build a 2-factor approximation f̃(x), compute a risk-adjusted score J,
# and compute simple penalties (uncertainty and cost) used by the optimization pipeline.
#
# The module expects pandas DataFrame inputs for cell-level quantities. The
# canonical index/columns layout is the same as produced by effects.estimate_two_factor_cell_means:
# rows = levels of factor A, columns = levels of factor B.

from __future__ import annotations

from typing import Optional, Tuple
import numpy as np
import pandas as pd


def build_f_tilde_from_cell_means(cell_means: pd.DataFrame) -> pd.DataFrame:
    """
    Return the two-factor approximation f̃ as the provided cell means.
    This is a thin wrapper that documents the intended semantics: f̃(x_{ij}) = cell_mean_{ij}.

    Parameters
    ----------
    cell_means :
        DataFrame of shape (n_levels_A, n_levels_B) with cell-wise mean outcome estimates.

    Returns
    -------
    pandas.DataFrame
        Copy of input cell means representing f̃.
    """
    return cell_means.copy()


def compute_uncertainty_from_bootstrap(
    bootstrap_values: dict,
    levels_a: Optional[list] = None,
    levels_b: Optional[list] = None,
    aggfunc: str = "std",
) -> pd.DataFrame:
    """
    Compute per-cell uncertainty (standard error or other aggregator) from bootstrap draws.

    Parameters
    ----------
    bootstrap_values :
        Mapping (a_level, b_level) -> 1D array-like of bootstrap replicate estimates
        or a pandas.DataFrame with MultiIndex (a_level, b_level) and columns for replicates.
    levels_a :
        Optional ordered list of A levels to use for the index.
    levels_b :
        Optional ordered list of B levels to use for the columns.
    aggfunc :
        Aggregation function name: "std" for standard deviation, "se" for standard error,
        "iqr" for interquartile range, or a custom callable name supported by numpy.

    Returns
    -------
    pandas.DataFrame
        DataFrame aligned with (levels_a x levels_b) containing uncertainty measures.
    """
    # If input is a DataFrame with MultiIndex
    if isinstance(bootstrap_values, pd.DataFrame) and isinstance(bootstrap_values.index, pd.MultiIndex):
        # assume columns are replicate indices
        df = bootstrap_values.copy()
        if levels_a is None:
            levels_a = df.index.get_level_values(0).unique().tolist()
        if levels_b is None:
            levels_b = df.index.get_level_values(1).unique().tolist()

        agg_map = {
            "std": lambda arr: np.std(arr, ddof=1, axis=1),
            "se": lambda arr: np.std(arr, ddof=1, axis=1) / np.sqrt(arr.shape[1]),
            "iqr": lambda arr: np.subtract(*np.percentile(arr, [75, 25], axis=1)),
        }

        if aggfunc in agg_map:
            vals = agg_map[aggfunc](df.values)
        else:
            # try to use numpy ufunc name
            fun = getattr(np, aggfunc, None)
            if fun is None:
                raise ValueError(f"Unknown aggfunc {aggfunc}")
            vals = fun(df.values, axis=1)

        ser = pd.Series(vals, index=df.index)
        out = ser.unstack(level=1).reindex(index=levels_a, columns=levels_b)
        return out

    # If input is dict-like mapping (a_level, b_level) -> array
    else:
        if levels_a is None or levels_b is None:
            # infer levels from keys
            keys = list(bootstrap_values.keys())
            levels_a = sorted({k[0] for k in keys})
            levels_b = sorted({k[1] for k in keys})

        result = pd.DataFrame(index=levels_a, columns=levels_b, dtype=float)
        for (a, b), arr in bootstrap_values.items():
            arr = np.asarray(arr, dtype=float)
            if aggfunc == "std":
                result.loc[a, b] = float(np.std(arr, ddof=1))
            elif aggfunc == "se":
                result.loc[a, b] = float(np.std(arr, ddof=1) / np.sqrt(arr.size))
            elif aggfunc == "iqr":
                result.loc[a, b] = float(np.subtract(*np.percentile(arr, [75, 25])))
            else:
                fun = getattr(np, aggfunc, None)
                if fun is None:
                    raise ValueError(f"Unknown aggfunc {aggfunc}")
                result.loc[a, b] = float(fun(arr))
        return result


def normalize_costs(costs: pd.DataFrame, eps: float = 1e-9) -> pd.DataFrame:
    """
    Normalize cost table to [0, 1] by dividing by the maximum cost.
    If all costs are zero, returns zeros.

    Parameters
    ----------
    costs :
        DataFrame of costs aligned with cell means.
    eps :
        Small constant to avoid division by zero.

    Returns
    -------
    pandas.DataFrame
        Normalized cost matrix in [0, 1].
    """
    cm = costs.copy().astype(float)
    maxc = float(np.nanmax(cm.values)) if cm.size > 0 else 0.0
    if maxc <= eps:
        return cm.fillna(0.0)
    return cm / maxc


def compute_risk_adjusted_score(
    cell_means: pd.DataFrame,
    uncertainty: Optional[pd.DataFrame] = None,
    cost: Optional[pd.DataFrame] = None,
    kappa: float = 1.0,
    rho: float = 0.0,
    normalize_costs_flag: bool = True,
) -> pd.DataFrame:
    """
    Compute a risk-adjusted score for each cell:
        Score = mean - kappa * uncertainty - rho * normalized_cost

    Parameters
    ----------
    cell_means :
        DataFrame of estimated means per cell.
    uncertainty :
        Optional DataFrame of uncertainty (same shape as cell_means). If None, treated as zeros.
    cost :
        Optional DataFrame of costs (same shape). If None, treated as zeros.
    kappa :
        Risk-aversion multiplier for uncertainty.
    rho :
        Cost weight.
    normalize_costs_flag :
        If True, normalize costs to [0,1] before applying rho.

    Returns
    -------
    pandas.DataFrame
        DataFrame of scores aligned with input.
    """
    means = cell_means.copy().astype(float)
    if uncertainty is None:
        uncertainty = pd.DataFrame(0.0, index=means.index, columns=means.columns)
    else:
        uncertainty = uncertainty.reindex(index=means.index, columns=means.columns).fillna(0.0).astype(float)

    if cost is None:
        cost_norm = pd.DataFrame(0.0, index=means.index, columns=means.columns)
    else:
        cost = cost.reindex(index=means.index, columns=means.columns).astype(float)
        cost_norm = normalize_costs(cost) if normalize_costs_flag else cost

    score = means - kappa * uncertainty - rho * cost_norm
    return score
