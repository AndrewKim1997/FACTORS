# src/factors/bootstrap.py
# Utilities to compute bootstrap-based uncertainty estimates and confidence intervals
# for cell means or other aggregated statistics.
#
# The functions are intentionally lightweight and rely on numpy/pandas only.
# They accept a pandas DataFrame and produce DataFrames or dictionaries that
# align with the rest of the FACTORS codebase.

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Callable, Dict, Iterable, Tuple, Optional, Any
from collections import defaultdict


def _rng_from_seed(seed: Optional[int]) -> np.random.Generator:
    """Create a numpy Generator from an integer seed or None (uses default)."""
    if seed is None:
        return np.random.default_rng()
    return np.random.default_rng(seed)


def bootstrap_cell_statistics(
    df: pd.DataFrame,
    group_cols: Iterable[str],
    value_col: str,
    stat: Callable[[np.ndarray], float] = np.mean,
    n_boot: int = 1000,
    random_state: Optional[int] = None,
) -> Dict[Tuple[Any, ...], np.ndarray]:
    """
    Compute bootstrap replicates of a statistic for each group defined by group_cols.

    Parameters
    ----------
    df :
        Input DataFrame.
    group_cols :
        Iterable of column names to group by (for 2-factor cells use two names).
    value_col :
        Name of the numeric column to aggregate.
    stat :
        Callable that maps a 1D numpy array to a scalar (e.g., np.mean, np.median).
    n_boot :
        Number of bootstrap replicates.
    random_state :
        Optional integer seed for reproducibility.

    Returns
    -------
    dict
        Mapping from group key tuple (level1, level2, ...) to numpy array of shape (n_boot,)
        containing bootstrap replicate values.
    """
    rng = _rng_from_seed(random_state)
    boot_results: Dict[Tuple[Any, ...], np.ndarray] = {}
    grouped = df.groupby(list(group_cols))[value_col]

    for key, series in grouped:
        arr = np.asarray(series.dropna(), dtype=float)
        n = arr.size
        if n == 0:
            boot_results[key if isinstance(key, tuple) else (key,)] = np.full(n_boot, np.nan)
            continue
        # For each bootstrap replicate draw with replacement from arr
        replicates = np.empty(n_boot, dtype=float)
        for i in range(n_boot):
            # sample indices then compute stat
            idx = rng.integers(0, n, size=n)
            sample = arr[idx]
            replicates[i] = float(stat(sample))
        boot_results[key if isinstance(key, tuple) else (key,)] = replicates
    return boot_results


def bootstrap_to_dataframe(
    boot_dict: Dict[Tuple[Any, ...], np.ndarray],
    levels_a: Optional[Iterable] = None,
    levels_b: Optional[Iterable] = None,
) -> pd.DataFrame:
    """
    Convert a bootstrap dictionary (from bootstrap_cell_statistics) into a DataFrame
    with MultiIndex rows (a_level, b_level) and columns representing bootstrap replicates.

    If levels_a/levels_b are provided, the output will be reindexed accordingly; otherwise
    the index is inferred from keys.

    Parameters
    ----------
    boot_dict :
        Mapping (a_level, b_level, ...) -> replicates array
    levels_a, levels_b :
        Optional ordered lists to reindex rows/columns.

    Returns
    -------
    pandas.DataFrame
        MultiIndex DataFrame with shape (n_cells, n_boot).
    """
    # Build rows
    rows = []
    values = []
    for key, arr in boot_dict.items():
        # ensure key is a tuple
        if not isinstance(key, tuple):
            key = (key,)
        rows.append(tuple(key))
        values.append(np.asarray(arr, dtype=float))

    if not rows:
        return pd.DataFrame()

    # Determine max replicates length and pad shorter arrays with nan
    n_rep = max(len(v) for v in values)
    vals_padded = np.vstack([np.pad(v, (0, n_rep - len(v)), constant_values=np.nan) for v in values])

    # Create MultiIndex
    index = pd.MultiIndex.from_tuples(rows)
    col_names = [f"boot_{i}" for i in range(vals_padded.shape[1])]
    df = pd.DataFrame(vals_padded, index=index, columns=col_names)

    # Optionally reindex ordering for readability when two factors expected
    if len(index.names) == 2 and levels_a is not None and levels_b is not None:
        # create full index from cartesian product to ensure consistent ordering
        mi = pd.MultiIndex.from_product([list(levels_a), list(levels_b)])
        df = df.reindex(mi)

    return df


def compute_bootstrap_ci(
    boot_df: pd.DataFrame, alpha: float = 0.05, ci_method: str = "percentile"
) -> pd.DataFrame:
    """
    Compute point estimates, standard error and confidence intervals from bootstrap replicates.

    Parameters
    ----------
    boot_df :
        DataFrame with MultiIndex rows (cell keys) and bootstrap replicates as columns.
    alpha :
        Two-sided significance level (default 0.05 for 95% CI).
    ci_method :
        'percentile' or 'se' (standard error + normal approx). 'percentile' uses empirical quantiles.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns: estimate, se, ci_lower, ci_upper (index same as boot_df.index)
    """
    if boot_df.empty:
        return pd.DataFrame(columns=["estimate", "se", "ci_lower", "ci_upper"])

    estimates = boot_df.mean(axis=1)
    se = boot_df.std(axis=1, ddof=1)
    if ci_method == "percentile":
        lower = boot_df.quantile(q=alpha / 2.0, axis=1)
        upper = boot_df.quantile(q=1.0 - alpha / 2.0, axis=1)
    elif ci_method == "se":
        # normal approximation
        z = abs(np.percentile(np.random.standard_normal(100000), 100 * (1 - alpha / 2.0)))  # approx z
        lower = estimates - z * se
        upper = estimates + z * se
    else:
        raise ValueError("ci_method must be 'percentile' or 'se'")

    out = pd.DataFrame(
        {
            "estimate": estimates,
            "se": se,
            "ci_lower": lower,
            "ci_upper": upper,
        }
    )
    return out


def bootstrap_pipeline_cellmeans(
    df: pd.DataFrame,
    factor_a: str,
    factor_b: str,
    outcome_col: str,
    n_boot: int = 1000,
    stat: Callable[[np.ndarray], float] = np.mean,
    random_state: Optional[int] = None,
    alpha: float = 0.05,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convenience pipeline that runs bootstrap for two-factor cell means and returns:
      - boot_df: MultiIndex DataFrame of replicates
      - ci_df: DataFrame with estimate, se, ci_lower, ci_upper

    Parameters
    ----------
    df :
        Input DataFrame.
    factor_a, factor_b :
        Column names for factor A and factor B.
    outcome_col :
        Numeric outcome column.
    n_boot :
        Number of bootstrap replicates.
    stat :
        Statistic to bootstrap (default mean).
    random_state :
        Optional seed.
    alpha :
        CI significance level.

    Returns
    -------
    (boot_df, ci_df)
    """
    boot_dict = bootstrap_cell_statistics(
        df, group_cols=[factor_a, factor_b], value_col=outcome_col, stat=stat, n_boot=n_boot, random_state=random_state
    )
    boot_df = bootstrap_to_dataframe(boot_dict)
    ci_df = compute_bootstrap_ci(boot_df, alpha=alpha, ci_method="percentile")
    return boot_df, ci_df
