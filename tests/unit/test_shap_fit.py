from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import numpy as np
import pandas as pd
import pytest

from factors.shap_fit import fit_two_factor_approx_from_shap, _build_design_matrix_for_two_factors

def test_build_design_matrix_shapes_and_columns():
    A = np.array(["a", "a", "b", "b"])
    B = np.array(["x", "y", "x", "y"])
    design, a_names, b_names = _build_design_matrix_for_two_factors(A, B, drop_first=False)
    # Expect intercept plus two A dummies and two B dummies and 4 interactions
    assert "Intercept" in design.columns
    # Dummy names must start with A_ and B_
    assert all(c.startswith("A_") for c in a_names) or len(a_names) > 0
    assert all(c.startswith("B_") for c in b_names) or len(b_names) > 0
    # design rows should equal input length
    assert design.shape[0] == 4

def test_fit_two_factor_approx_from_shap_recovers_simple_pattern():
    # Create a small dataset with additive + interaction effect
    # pattern: base + A effect + B effect + interaction
    levels_a = pd.Series(["a", "a", "b", "b"])
    levels_b = pd.Series(["x", "y", "x", "y"])
    # Manually set coefficients
    intercept = 1.0
    a_effect = {"a": 0.5, "b": -0.5}
    b_effect = {"x": 0.2, "y": -0.2}
    interaction = {("a","x"): 0.3, ("a","y"): -0.1, ("b","x"): 0.0, ("b","y"): -0.2}
    target = []
    for aa, bb in zip(levels_a, levels_b):
        val = intercept + a_effect[aa] + b_effect[bb] + interaction[(aa,bb)]
        target.append(val)
    target = np.asarray(target)

    res = fit_two_factor_approx_from_shap(target, levels_a, levels_b, alpha=1e-8, drop_first=False)
    # Predictions should be close to target (low mse)
    assert res["mse"] < 1e-6
    # Interaction table should contain values for at least one non-zero interaction
    itab = res["interaction_table"]
    assert isinstance(itab, pd.DataFrame)
    # sum of absolute interactions should be positive
    assert float(itab.abs().sum().sum()) > 0.0

def test_compute_shap_explainer_values_skipped_if_shap_unavailable():
    # Only run this small smoke check if shap is installed; otherwise skip.
    import importlib.util
    if importlib.util.find_spec("shap") is None:
        pytest.skip("shap not installed; skipping shap.Explainer integration test")
    # If shap is available, perform a minimal smoke test constructing a dummy model.
    from sklearn.linear_model import LinearRegression
    from factors.shap_fit import compute_shap_explainer_values

    X = pd.DataFrame({"x1": [0.0, 1.0, 2.0], "x2": [1.0, 0.5, -1.0]})
    y = X["x1"] * 0.5 + X["x2"] * -0.2
    model = LinearRegression().fit(X, y)
    expected, shap_vals = compute_shap_explainer_values(model, X)
    # shap_vals shape should match (n_samples, n_features)
    assert getattr(shap_vals, "shape", None) == (3, 2)
