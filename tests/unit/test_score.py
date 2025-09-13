from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import pandas as pd
import numpy as np
import pytest

from factors import score as fs


def make_cell_matrices():
    # 2x2 example matrices
    cm = pd.DataFrame([[1.0, 2.0], [3.0, 4.0]], index=["A1", "A2"], columns=["B1", "B2"])
    unc = pd.DataFrame([[0.1, 0.2], [0.3, 0.4]], index=cm.index, columns=cm.columns)
    cost = pd.DataFrame([[10.0, 0.0], [5.0, 1.0]], index=cm.index, columns=cm.columns)
    return cm, unc, cost


def test_compute_risk_adjusted_score_basic():
    cm, unc, cost = make_cell_matrices()
    # kappa=1.0, rho=0.0 -> score = mean - uncertainty
    s = fs.compute_risk_adjusted_score(cm, uncertainty=unc, cost=None, kappa=1.0, rho=0.0)
    assert float(s.loc["A1", "B1"]) == pytest.approx(1.0 - 0.1)
    assert float(s.loc["A2", "B2"]) == pytest.approx(4.0 - 0.4)


def test_normalize_costs_and_apply_rho():
    cm, unc, cost = make_cell_matrices()
    # normalize costs divides by max which is 10 -> normalized cost for A1,B1 =1.0
    s = fs.compute_risk_adjusted_score(cm, uncertainty=unc, cost=cost, kappa=0.0, rho=0.5, normalize_costs_flag=True)
    expected = cm - 0.5 * (cost / 10.0)
    # element-wise compare
    pd.testing.assert_frame_equal(s, expected)


def test_compute_uncertainty_from_bootstrap_dict_input():
    # small bootstrap dict mapping
    boot = {("A1", "B1"): [1.0, 1.1, 0.9], ("A1", "B2"): [2.0, 2.1, 1.9]}
    unc_df = fs.compute_uncertainty_from_bootstrap(boot, aggfunc="std")
    assert unc_df.loc["A1", "B1"] > 0.0
    assert "A1" in unc_df.index
