# src/factors/shap_fit.py
# Functions to compute SHAP values and to fit a two-factor least-squares approximation
# to scalar targets derived from model outputs or SHAP attributions.
#
# The implementation is intentionally straightforward: it constructs one-hot encodings
# for factor levels and interaction terms, then fits ridge-regularized least squares.
# This is suitable for small-to-moderate numbers of factor levels; for very large cardinality
# consider level grouping or sparse solvers.

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict
import sklearn.linear_model as lm

try:
    import shap  # optional dependency
except Exception:  # pragma: no cover - shap optional
    shap = None


def compute_shap_explainer_values(model, X: pd.DataFrame, background: Optional[pd.DataFrame] = None):
    """
    Compute SHAP values using shap.Explainer where available.

    Parameters
    ----------
    model :
        A fitted model object. shap.Explainer will attempt to pick an appropriate explainer.
    X :
        DataFrame of inputs (n_samples x n_features).
    background :
        Optional background dataset for explainer; if None, shap will set one automatically.

    Returns
    -------
    tuple (expected_value, shap_values)
      - expected_value: scalar or list of expected values returned by explainer
      - shap_values: numpy array of shape (n_samples, n_features) or the structure returned by shap
    """
    if shap is None:
        raise ImportError("shap library is required to compute SHAP values. Install with `pip install shap`.")

    explainer = shap.Explainer(model, background) if background is not None else shap.Explainer(model)
    sv = explainer(X)
    return sv.base_values, np.asarray(sv.values)


def _build_design_matrix_for_two_factors(
    levels_a: np.ndarray, levels_b: np.ndarray, drop_first: bool = False
) -> Tuple[pd.DataFrame, list, list]:
    """
    Build a design matrix for main effects of A, main effects of B and their interactions.
    Returns (design_df, a_level_names, b_level_names).

    If drop_first is True, the first level of each factor is dropped to avoid perfect multicollinearity.
    We still use ridge regularization in fitting which handles identifiability.
    """
    df = pd.DataFrame({"__A__": levels_a, "__B__": levels_b})
    # One-hot encode factors
    A_dummies = pd.get_dummies(df["__A__"], prefix="A", drop_first=drop_first)
    B_dummies = pd.get_dummies(df["__B__"], prefix="B", drop_first=drop_first)

    # Interaction columns: outer product of A_dummies and B_dummies column-wise
    inter_cols = []
    inter_df = []
    for a_col in A_dummies.columns:
        for b_col in B_dummies.columns:
            name = f"{a_col}__x__{b_col}"
            inter_cols.append(name)
            inter_df.append(A_dummies[a_col].values * B_dummies[b_col].values)
    if inter_df:
        Inter = pd.DataFrame(np.column_stack(inter_df), columns=inter_cols, index=df.index)
        design = pd.concat([pd.Series(1, index=df.index, name="Intercept"), A_dummies, B_dummies, Inter], axis=1)
    else:
        design = pd.concat([pd.Series(1, index=df.index, name="Intercept"), A_dummies, B_dummies], axis=1)

    a_level_names = list(A_dummies.columns)
    b_level_names = list(B_dummies.columns)
    return design, a_level_names, b_level_names


def fit_two_factor_approx_from_shap(
    target: np.ndarray,
    factor_a: pd.Series,
    factor_b: pd.Series,
    alpha: float = 1e-6,
    drop_first: bool = False,
) -> Dict[str, object]:
    """
    Fit a ridge-regularized linear model that approximates the provided scalar target
    as an additive combination of factor A main effects, factor B main effects, and A x B interactions.

    Parameters
    ----------
    target :
        1D numpy array of shape (n_samples,) containing the scalar target.
        This can be the model predictions or a scalar summary of SHAP attributions (e.g., sum over features).
    factor_a :
        pandas Series of length n_samples containing categorical factor A (levels).
    factor_b :
        pandas Series of length n_samples containing categorical factor B (levels).
    alpha :
        Regularization strength for Ridge regression (lambda).
    drop_first :
        Whether to drop the first level dummy to reduce multicollinearity.

    Returns
    -------
    dict
        {
          "model": fitted sklearn.linear_model.Ridge,
          "design_matrix": pandas.DataFrame,
          "a_levels": list of A dummy names,
          "b_levels": list of B dummy names,
          "main_effects_A": pandas.Series indexed by A level dummy names,
          "main_effects_B": pandas.Series indexed by B level dummy names,
          "interaction_table": pandas.DataFrame indexed by A levels and columns by B levels (may refer to dropped levels),
          "pred": numpy.ndarray predicted values,
          "mse": float mean squared error between target and prediction
        }

    Notes
    -----
    The returned main effects correspond to the coefficients in the design matrix.
    Interpreting coefficients when drop_first=True requires mapping dummy names back to original levels.
    """
    if target.ndim != 1:
        raise ValueError("target must be a 1-dimensional array of shape (n_samples,)")

    if len(target) != len(factor_a) or len(target) != len(factor_b):
        raise ValueError("target and factor series must have the same length")

    design, a_names, b_names = _build_design_matrix_for_two_factors(
        np.asarray(factor_a), np.asarray(factor_b), drop_first=drop_first
    )

    # Fit ridge regression (closed-form via sklearn)
    ridge = lm.Ridge(alpha=alpha, fit_intercept=False)  # intercept already present in design
    ridge.fit(design.values, target)
    coefs = ridge.coef_
    pred = ridge.predict(design.values)
    mse = float(np.mean((target - pred) ** 2))

    coef_series = pd.Series(coefs, index=design.columns)

    # Extract main effects and interaction effects
    main_A = coef_series[[c for c in design.columns if c.startswith("A_")]].copy()
    main_B = coef_series[[c for c in design.columns if c.startswith("B_")]].copy()

    # Reconstruct interaction table: entries for each pair of (A_dummy, B_dummy) that were present
    inter_cols = [c for c in design.columns if "__x__" in c]
    # derive original level names for rows/cols (dummy names include 'A_<level>' format)
    # Build a matrix with index=unique A dummy prefixes, columns=unique B dummy suffixes
    # We'll attempt to map back to readable A and B levels when possible.
    # Parse names like "A_level__x__B_other"
    interactions = {}
    for c in inter_cols:
        left, _, right = c.partition("__x__")
        # left like "A_<lvl>", right like "B_<lvl2>"
        interactions[c] = coef_series[c]

    # Build a DataFrame for interactions with human-readable axis if possible
    # Extract A level names (after prefix "A_") and B level names (after prefix "B_")
    a_levels = sorted({name.split("A_", 1)[1] for name in main_A.index}) if len(main_A) > 0 else []
    b_levels = sorted({name.split("B_", 1)[1] for name in main_B.index}) if len(main_B) > 0 else []

    # When drop_first=True, some original levels are not present in dummy lists; interpret with caution.
    interaction_table = pd.DataFrame(index=a_levels if a_levels else ["A_dummy"], columns=b_levels if b_levels else ["B_dummy"])
    for c, val in interactions.items():
        a_dummy, _, b_dummy = c.partition("__x__")
        # parse a and b readable
        a_read = a_dummy.split("A_", 1)[1] if "A_" in a_dummy else a_dummy
        b_read = b_dummy.split("B_", 1)[1] if "B_" in b_dummy else b_dummy
        # create cells if possible
        try:
            interaction_table.loc[a_read, b_read] = val
        except KeyError:
            # If mapping fails because we dropped first level or names mismatch, add to table dynamically
            if a_read not in interaction_table.index:
                interaction_table.loc[a_read] = np.nan
            if b_read not in interaction_table.columns:
                interaction_table[b_read] = np.nan
            interaction_table.loc[a_read, b_read] = val

    # Fill any remaining NaNs with 0.0 to indicate no estimated interaction for that dummy pair
    interaction_table = interaction_table.fillna(0.0)

    return {
        "model": ridge,
        "design_matrix": design,
        "a_levels": a_names,
        "b_levels": b_names,
        "main_effects_A": main_A,
        "main_effects_B": main_B,
        "interaction_table": interaction_table,
        "pred": pred,
        "mse": mse,
    }
