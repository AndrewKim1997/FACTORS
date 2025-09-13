from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import pandas as pd
import numpy as np
import pytest

from factors import optimizer as fo


def make_score_and_cost():
    # 3x2 score matrix with descending values
    score = pd.DataFrame([[10.0, 8.0], [6.0, 4.0], [2.0, 1.0]], index=["A1", "A2", "A3"], columns=["B1", "B2"])
    cost = pd.DataFrame([[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]], index=score.index, columns=score.columns)
    return score, cost


def test_greedy_select_under_budget_basic():
    score, cost = make_score_and_cost()
    selected, total_cost = fo.greedy_select_under_budget(score, cost=cost, budget=2.0)
    # with budget 2, greedy picks top two cells by score: (A1,B1) and (A1,B2) or second best depending tie-breaking
    assert len(selected) == 2
    assert total_cost <= 2.0


def test_exhaustive_best_k_small_enumeration():
    score, cost = make_score_and_cost()
    # choose best pair (k=2)
    best_sel, best_score = fo.exhaustive_best_k(score, cost=cost, k=2, budget=10.0)
    assert len(best_sel) == 2
    assert best_score > 0.0


def test_beam_search_pair_selection_returns_reasonable_solution():
    score, cost = make_score_and_cost()
    sel, sc = fo.beam_search_pair_selection(score, cost=cost, budget=3.0, beam_width=3, max_iters=3)
    # Should return between 1 and budget cells (cost units)
    assert isinstance(sel, list)
    assert sc >= 0.0
