from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is importable when tests run without editable install
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import pandas as pd
import numpy as np
import pytest

from factors import effects as fe


def make_toy_df():
    # 2x2 balanced table with simple values
    rows = []
    for a, b, val in [
        ("A1", "B1", 1.0),
        ("A1", "B2", 2.0),
        ("A2", "B1", 3.0),
        ("A2", "B2", 4.0),
    ]:
        rows.append({"A": a, "B": b, "y": val})
    return pd.DataFrame(rows)


def test_estimate_two_factor_cell_means_shape_and_values():
    df = make_toy_df()
    cm = fe.estimate_two_factor_cell_means(df, "A", "B", "y")
    # shape must be 2x2 and values should match
    assert cm.shape == (2, 2)
    assert float(cm.loc["A1", "B1"]) == pytest.approx(1.0)
    assert float(cm.loc["A2", "B2"]) == pytest.approx(4.0)


def test_estimate_main_effects_unweighted():
    df = make_toy_df()
    effects = fe.estimate_main_effects(df, ["A", "B"], "y")
    # For factor A: A1 mean = (1+2)/2 = 1.5, A2 mean = (3+4)/2 = 3.5
    assert "A" in effects and "B" in effects
    assert float(effects["A"].loc["A1"]) == pytest.approx(1.5)
    assert float(effects["A"].loc["A2"]) == pytest.approx(3.5)
    # For factor B: B1 mean = (1+3)/2 = 2.0
    assert float(effects["B"].loc["B1"]) == pytest.approx(2.0)


def test_two_factor_interaction_matrix_properties():
    df = make_toy_df()
    cm = fe.estimate_two_factor_cell_means(df, "A", "B", "y")
    I = fe.two_factor_interaction_matrix(cm)
    # Interaction residuals should sum to approx 0 across matrix (definition yields centered residuals)
    total = np.nansum(I.values)
    assert total == pytest.approx(0.0, abs=1e-8)
    # Check one known residual manually (compute expected)
    overall = np.nanmean(cm.values)
    row_means = cm.mean(axis=1)
    col_means = cm.mean(axis=0)
    expected = cm.loc["A1", "B1"] - row_means.loc["A1"] - col_means.loc["B1"] + overall
    assert float(I.loc["A1", "B1"]) == pytest.approx(float(expected))
