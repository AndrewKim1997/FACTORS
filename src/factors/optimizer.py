# src/factors/optimizer.py
# Simple optimizers for selecting cells or small designs based on a score matrix.
# Includes:
#  - greedy_select_under_budget: pick cells in descending score order until budget exhausted
#  - beam_search_pair_selection: beam search that builds small sets of (A_level, B_level) pairs
#  - exhaustive_best_k: exact search for very small problems (k selection)

from __future__ import annotations

from typing import Iterable, List, Tuple, Optional
import numpy as np
import pandas as pd


def greedy_select_under_budget(
    score: pd.DataFrame,
    cost: Optional[pd.DataFrame] = None,
    budget: float = np.inf,
    return_selected_mask: bool = False,
) -> Tuple[List[Tuple[str, str]], float]:
    """
    Greedy selection of cells sorted by score descending, subject to a total cost budget.
    This is useful as a simple baseline optimizer.

    Parameters
    ----------
    score :
        DataFrame with score values indexed by A levels (rows) and B levels (columns).
    cost :
        DataFrame with same shape providing costs for each cell. If None, uniform cost = 1.
    budget :
        Total cost budget. Selection stops when next cell would exceed budget.
    return_selected_mask :
        If True, returns (selected_list, total_cost, mask_df) where mask_df is boolean DataFrame.

    Returns
    -------
    selected_cells, total_cost
      - selected_cells: list of tuples (a_level, b_level) in selection order
      - total_cost: sum of costs of selected cells
    """
    if cost is None:
        cost = pd.DataFrame(1.0, index=score.index, columns=score.columns)

    # Flatten
    flat = []
    for a in score.index:
        for b in score.columns:
            val = score.loc[a, b]
            c = float(cost.loc[a, b]) if (a in cost.index and b in cost.columns) else 1.0
            flat.append((a, b, float(val), c))
    # Sort by score descending
    flat_sorted = sorted(flat, key=lambda x: (-np.nan_to_num(x[2], -np.inf), x[3]))
    selected = []
    total_cost = 0.0
    mask = pd.DataFrame(False, index=score.index, columns=score.columns)
    for a, b, val, c in flat_sorted:
        if np.isnan(val):
            continue
        if total_cost + c <= budget:
            selected.append((a, b))
            total_cost += c
            mask.loc[a, b] = True
        else:
            continue
    if return_selected_mask:
        return selected, total_cost, mask
    return selected, total_cost


def exhaustive_best_k(
    score: pd.DataFrame,
    cost: Optional[pd.DataFrame] = None,
    k: int = 1,
    budget: float = np.inf,
) -> Tuple[List[Tuple[str, str]], float]:
    """
    Exhaustive search for the best subset of k cells maximizing total score subject to budget.
    Only suitable for very small boards (n_cells choose k small).

    Parameters
    ----------
    score :
        DataFrame with scores.
    cost :
        Optional cost DataFrame. If None, uniform cost = 1.
    k :
        Number of cells to select.
    budget :
        Cost budget.

    Returns
    -------
    best_selection, best_score_sum
    """
    import itertools

    flat = []
    indices = []
    for a in score.index:
        for b in score.columns:
            val = score.loc[a, b]
            if np.isnan(val):
                continue
            flat.append(((a, b), float(val), float(cost.loc[a, b]) if cost is not None else 1.0))
            indices.append((a, b))
    best_score = -np.inf
    best_sel = []
    # quick path: if number of available cells is small, enumerate
    for comb in itertools.combinations(flat, r=k):
        sel = [c[0] for c in comb]
        ssum = sum(c[1] for c in comb)
        csum = sum(c[2] for c in comb)
        if csum <= budget and ssum > best_score:
            best_score = ssum
            best_sel = sel
    if best_score == -np.inf:
        return [], 0.0
    return best_sel, float(best_score)


def beam_search_pair_selection(
    score: pd.DataFrame,
    cost: Optional[pd.DataFrame] = None,
    budget: float = np.inf,
    beam_width: int = 5,
    max_iters: Optional[int] = None,
) -> Tuple[List[Tuple[str, str]], float]:
    """
    Beam search to greedily compose a small selection of cells that approximately maximize total score.
    This procedure builds selections incrementally while keeping only the top `beam_width` partial solutions.

    Parameters
    ----------
    score :
        DataFrame of scores (rows = A levels, cols = B levels).
    cost :
        DataFrame of costs aligned with score. If None, all costs = 1.
    budget :
        Maximum allowed total cost.
    beam_width :
        Number of partial solutions to keep per iteration.
    max_iters :
        Maximum number of cells to select. If None, upper bound is total number of non-NaN cells.

    Returns
    -------
    best_selection, best_score_sum
    """
    if cost is None:
        cost = pd.DataFrame(1.0, index=score.index, columns=score.columns)

    # Flatten candidate list
    candidates = []
    for a in score.index:
        for b in score.columns:
            val = score.loc[a, b]
            if np.isnan(val):
                continue
            candidates.append(((a, b), float(val), float(cost.loc[a, b])))

    # sort candidates by score descending for deterministic behavior
    candidates = sorted(candidates, key=lambda x: -x[1])

    total_cells = len(candidates)
    if max_iters is None:
        max_iters = total_cells

    # Beam entries: tuple (selected_list, total_score, total_cost)
    beam = [([], 0.0, 0.0)]
    best = ([], 0.0, 0.0)

    for _iter in range(int(max_iters)):
        new_beam = []
        for sel, ssum, csum in beam:
            # try adding any candidate not already in sel
            for cand, val, c in candidates:
                if cand in sel:
                    continue
                new_cost = csum + c
                if new_cost > budget:
                    continue
                new_sel = sel + [cand]
                new_sum = ssum + val
                new_beam.append((new_sel, new_sum, new_cost))
                # track best
                if new_sum > best[1]:
                    best = (new_sel, new_sum, new_cost)
        if not new_beam:
            break
        # keep top-k partial solutions by score
        new_beam_sorted = sorted(new_beam, key=lambda x: -x[1])
        beam = new_beam_sorted[:beam_width]
    # return best found
    if best[1] <= 0.0:
        # fallback to greedy single selection if nothing selected
        sel, sc = greedy_select_under_budget(score, cost=cost, budget=budget)
        return sel, sc
    return best[0], float(best[1])
