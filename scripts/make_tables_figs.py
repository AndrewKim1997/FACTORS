#!/usr/bin/env python3
# scripts/make_tables_figs.py
# Simple utility to aggregate metrics JSON files and produce summary tables/figures.
# Usage:
#   scripts/make_tables_figs.py --inputs "experiments/**/metrics.json" --out results/figures/summary
#
# The script:
#  - reads all metrics JSON files matching the inputs glob
#  - assembles a pandas DataFrame summarizing keys
#  - writes results/ tables and a simple bar plot of PCI by dataset/run

from __future__ import annotations

import argparse
from pathlib import Path
import json
import glob
import pandas as pd
import matplotlib.pyplot as plt

from factors import io as fio


def load_metrics_glob(pattern: str) -> pd.DataFrame:
    files = sorted(glob.glob(pattern, recursive=True))
    rows = []
    for f in files:
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            # best-effort flattening for nested objects
            row = {"_path": f}
            for k, v in d.items():
                if isinstance(v, (str, int, float, bool)):
                    row[k] = v
                else:
                    # store JSON repr for non-scalar
                    row[k] = json.dumps(v)
            rows.append(row)
        except Exception as e:
            print(f"[make_tables_figs] failed to read {f}: {e}")
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def make_summary_figure(df: pd.DataFrame, out_dir: Path):
    # If PCI column present, plot mean PCI by dataset
    if "pci" in df.columns:
        agg = df.groupby("dataset")["pci"].agg(["mean", "std", "count"]).reset_index()
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(agg["dataset"], agg["mean"], yerr=agg["std"].fillna(0), alpha=0.8)
        ax.set_ylabel("PCI (mean ± std)")
        ax.set_title("PCI by dataset")
        out_dir.mkdir(parents=True, exist_ok=True)
        fig_path = out_dir / "pci_by_dataset.png"
        fig.savefig(str(fig_path), dpi=200, bbox_inches="tight")
        plt.close(fig)
        print(f"[make_tables_figs] saved figure {fig_path}")


def save_summary_table(df: pd.DataFrame, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "metrics_summary.csv"
    df.to_csv(csv_path, index=False)
    print(f"[make_tables_figs] saved table {csv_path}")


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Aggregate metrics JSONs and create simple tables/figures")
    parser.add_argument("--inputs", required=True, help="Glob pattern for metrics.json files (e.g. 'experiments/**/metrics.json')")
    parser.add_argument("--out", required=True, help="Output directory for tables/figures")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    df = load_metrics_glob(args.inputs)
    if df.empty:
        print("[make_tables_figs] no metrics found for pattern:", args.inputs)
        return

    # Try to coerce pci column to numeric
    if "pci" in df.columns:
        df["pci"] = pd.to_numeric(df["pci"], errors="coerce")

    save_summary_table(df, out_dir)
    make_summary_figure(df, out_dir)
    # write a small run metadata file listing input files
    fio.atomic_write_json({"inputs_glob": args.inputs, "n_files": int(len(df)), "generated_at": pd.Timestamp.utcnow().isoformat()}, out_dir / "summary_metadata.json")
    print("[make_tables_figs] done")


if __name__ == "__main__":
    main()
