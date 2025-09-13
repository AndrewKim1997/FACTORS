#!/usr/bin/env python3
# scripts/run_experiment.py
# Run a single experiment described by a YAML config.
# Key CLI:
#   --config PATH   : path to dataset/experiment YAML
#   --seed INT
#   --out PATH      : output directory for run artifacts (metrics, figures, metadata)
#   --device DEVICE : optional override ('cpu' or 'cuda')
#   --deterministic : optional flag to enable deterministic torch backends (best-effort)
#
# This script implements a compact pipeline:
#  - load config YAML and merge with global defaults (if available)
#  - prepare data (basic CSV/parquet loader or torchvision hook)
#  - compute two-factor cell means using src/factors/effects
#  - bootstrap cell means and compute CIs using src/factors/bootstrap
#  - compute risk-adjusted score using src/factors/score
#  - compute PCI diagnostics using src/factors/pci
#  - save metrics and run metadata via src/factors/io
#
# The goal is to provide a reproducible, auditable run that writes:
#   <out>/metrics.json
#   <out>/run_metadata.json
#   <out>/cell_means.csv
#   <out>/bootstrap_replicates.parquet  (if applicable)

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
import warnings

# third-party libs
import yaml
import pandas as pd
import numpy as np

# factors modules
from factors import (
    estimate_two_factor_cell_means,
)
from factors import bootstrap as fb
from factors import score as fs
from factors import pci as fp
from factors import io as fio
from factors import utils as fut

# optional: torchvision for fmnist
try:
    import torchvision
    from torchvision.datasets import FashionMNIST
    from torchvision import transforms
except Exception:
    FashionMNIST = None


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def merge_dicts(a: dict, b: dict) -> dict:
    """Shallow merge with b overriding a."""
    out = dict(a or {})
    out.update(b or {})
    return out


def load_tabular_from_config(cfg: dict, repo_root: Path) -> pd.DataFrame:
    """
    Generic loader for CSV / parquet based dataset configs. For FMNIST use torchvision hook.
    """
    ds = cfg.get("dataset", {})
    provider = ds.get("source", {}).get("provider", None)
    if provider and "FashionMNIST" in str(provider) and FashionMNIST is not None:
        # prepare torchvision download path
        root = repo_root / ds.get("files", {}).get("raw", "data/raw/fmnist")
        transform = transforms.Compose([transforms.ToTensor()])
        dataset = FashionMNIST(root=str(root), train=True, download=True, transform=transform)
        # Convert to a small DataFrame with 'image' and 'label' columns for quick sanity; for full runs user should use dedicated training script
        rows = []
        for i in range(len(dataset)):
            img, label = dataset[i]
            # flatten small image to vector summary: mean pixel value (toy metric)
            rows.append({"label": int(label), "mean_pixel": float(img.mean().item())})
        return pd.DataFrame(rows)
    # otherwise load file path
    raw = ds.get("files", {}).get("raw")
    processed = ds.get("files", {}).get("processed")
    if processed and (repo_root / processed).exists():
        path = repo_root / processed
    elif raw and (repo_root / raw).exists():
        path = repo_root / raw
    else:
        raise FileNotFoundError(f"Neither processed nor raw file found for dataset in config: raw={raw}, processed={processed}")
    if str(path).endswith(".csv"):
        return pd.read_csv(path)
    elif str(path).endswith(".parquet") or str(path).endswith(".pq"):
        return pd.read_parquet(path)
    else:
        # try pandas read_table
        return pd.read_csv(path)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Run a single FACTORS experiment (config + seed -> outputs)")
    parser.add_argument("--config", required=True, help="Path to dataset or experiment YAML config")
    parser.add_argument("--seed", type=int, required=True, help="RNG seed")
    parser.add_argument("--out", required=True, help="Output directory for this run")
    parser.add_argument("--device", choices=["cpu", "cuda"], default=None, help="Override device")
    parser.add_argument("--deterministic", action="store_true", help="Enable deterministic torch flags (best-effort)")
    parser.add_argument("--quiet", action="store_true", help="Less verbose output")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    cfg_path = Path(args.config)
    cfg = load_yaml(cfg_path)

    # Merge with global config if present
    global_cfg_path = repo_root / "configs" / "global.yaml"
    if global_cfg_path.exists():
        global_cfg = load_yaml(global_cfg_path)
        cfg = merge_dicts(global_cfg, cfg)

    # prepare output dir
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # set seed and determinism
    fut.set_seed(args.seed)
    if args.deterministic:
        fut.enable_deterministic_torch()

    # write run metadata early
    fio.write_run_metadata(out_dir, config=cfg)

    # load data
    try:
        df = load_tabular_from_config(cfg, repo_root)
    except Exception as e:
        msg = f"Failed to load dataset from config {cfg_path}: {e}"
        print(msg, file=sys.stderr)
        raise

    # determine factor columns
    factors = cfg.get("factors_for_doe", {})
    factor_a = factors.get("factor_a")
    factor_b = factors.get("factor_b")

    results = {"dataset": cfg.get("dataset", {}).get("id", str(cfg_path)), "seed": args.seed}

    if factor_a and factor_b:
        # Ensure factor columns exist; if not, try to create from suggested binning (basic)
        if factor_a not in df.columns or factor_b not in df.columns:
            # Attempt simple binning per config
            suggested = cfg.get("preprocessing", {}).get("suggested_binning", {}) or {}
            for key, rule in suggested.items():
                col = rule.get("column")
                if col in df.columns:
                    if rule.get("method") == "edges":
                        edges = rule.get("edges", [])
                        df[key] = pd.cut(df[col], bins=edges, labels=False, include_lowest=True).astype(str)
                    elif rule.get("method") == "quantiles":
                        qs = rule.get("quantiles", [])
                        df[key] = pd.qcut(df[col], q=[0.0] + qs + [1.0], labels=False, duplicates="drop").astype(str)
            # re-check
        if factor_a not in df.columns or factor_b not in df.columns:
            raise KeyError(f"Required factor columns not found in data: {factor_a}, {factor_b}")

        target_col = cfg.get("columns", {}).get("target") or cfg.get("dataset", {}).get("target") or "target"
        if target_col not in df.columns:
            # try common defaults
            if "compressive_strength" in df.columns:
                target_col = "compressive_strength"
            elif "class" in df.columns or "label" in df.columns:
                target_col = "label"
            elif "mean_pixel" in df.columns:
                target_col = "mean_pixel"
            else:
                raise KeyError(f"Cannot determine target column for dataset; looked for {target_col}")

        # compute cell means
        cell_means = estimate_two_factor_cell_means(df, factor_a, factor_b, outcome_col=target_col)
        # save cell means
        cell_means.to_csv(out_dir / "cell_means.csv")

        # bootstrap pipeline (may be expensive; controlled by config or defaults)
        bootstrap_n = int(cfg.get("bootstrap", {}).get("n_boot", cfg.get("bootstrap", {}).get("n_boot", 200)))
        boot_dict = fb.bootstrap_cell_statistics(df, group_cols=[factor_a, factor_b], value_col=target_col, n_boot=bootstrap_n, random_state=args.seed)
        boot_df = fb.bootstrap_to_dataframe(boot_dict)
        # Save replicates in parquet for compactness
        try:
            boot_df.to_parquet(out_dir / "bootstrap_replicates.parquet")
        except Exception:
            # fallback to pickle if parquet not available
            boot_df.to_pickle(out_dir / "bootstrap_replicates.pkl")

        ci_df = fb.compute_bootstrap_ci(boot_df, alpha=float(cfg.get("bootstrap", {}).get("ci_alpha", 0.05)))
        ci_df.to_csv(out_dir / "bootstrap_ci.csv")

        # uncertainty matrix aligned with cell_means
        uncertainty = fs.compute_uncertainty_from_bootstrap(boot_dict, levels_a=list(cell_means.index), levels_b=list(cell_means.columns), aggfunc="se")

        # optional cost matrix - if not provided, default zeros
        # look for a cost table in config.path costs -> file, or generated synthetic costs
        cost_df = None
        if "cost" in cfg:
            cost_file = cfg["cost"].get("file")
            if cost_file and (repo_root / cost_file).exists():
                cost_df = pd.read_csv(repo_root / cost_file, index_col=0)
        # compute score
        kappa = float(cfg.get("scoring", {}).get("kappa", 1.0))
        rho = float(cfg.get("scoring", {}).get("rho", 0.0))
        score = fs.compute_risk_adjusted_score(cell_means, uncertainty=uncertainty, cost=cost_df, kappa=kappa, rho=rho, normalize_costs_flag=bool(cfg.get("scoring", {}).get("normalize_costs", True)))
        score.to_csv(out_dir / "score.csv")

        # compute PCI
        pci_val = fp.pci_simple(cell_means)
        results.update({"pci": float(pci_val)})

        # select best cells under budget if optimizer config present
        optimizer_cfg = cfg.get("optimizer", {})
        budget = float(optimizer_cfg.get("budget", cfg.get("optimizer", {}).get("budget", 10.0)))
        from factors import optimizer as fo

        selected, total_cost = fo.greedy_select_under_budget(score, cost=cost_df, budget=budget)
        results.update({"selected_cells": selected, "selected_total_cost": float(total_cost)})

        # summary metrics: MSE to cell_means? For demonstration compute simple dispersion stats
        results.update(
            {
                "n_cells": int(np.prod(cell_means.shape)),
                "cell_means_mean": float(np.nanmean(cell_means.values)),
                "cell_means_std": float(np.nanstd(cell_means.values)),
            }
        )

    else:
        # If no factors specified, do a simple sanity summary of loaded dataframe
        results.update({"n_rows": int(len(df)), "columns": list(df.columns[:50])})

    # Save metrics to JSON
    fio.save_metrics_json(results, out_dir / "metrics.json")
    print(f"[run_experiment] done. outputs written to {out_dir}")


if __name__ == "__main__":
    main()
