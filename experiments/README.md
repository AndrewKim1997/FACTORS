# experiments/ — run artifacts and per-run outputs

This directory contains experiment run outputs produced by scripts (e.g., `scripts/run_experiment.py`, `scripts/reproduce_all.sh`). The repository tracks *lightweight* run artifacts (JSON/CSV/metadata) only; large binaries and model checkpoints should be stored externally or ignored via `.gitignore`.

## Purpose
- Collect per-run artifacts needed for reproducibility and post-processing.
- Provide a predictable layout so downstream scripts (`scripts/make_tables_figs.py`, paper build) can find metrics, logs, and metadata.
- Encourage small, curated artifacts to be tracked in Git while preventing repo bloat.

## Expected structure
```

experiments/
├─ main/
│  ├─ concrete/
│  │  ├─ \<run\_id>/
│  │  │  ├─ seed\_<N>/
│  │  │  │  ├─ metrics.json
│  │  │  │  ├─ run\_metadata.json
│  │  │  │  ├─ cell\_means.csv
│  │  │  │  ├─ bootstrap\_replicates.parquet   # optional (or .pkl)
│  │  │  │  ├─ bootstrap\_ci.csv
│  │  │  │  ├─ score.csv
│  │  │  │  └─ logs/
│  └─ ...
└─ ablation/
├─ shrinkage/
└─ ...

````

## Files you should produce for each run (recommended)
- `metrics.json` — small summary of scalars and selections (JSON). Keep this ≤ 1 MB.
  - Example keys: `dataset`, `seed`, `pci`, `n_cells`, `selected_cells`, `selected_total_cost`, `cell_means_mean`.
- `run_metadata.json` — provenance information (commit, timestamp, python version, config used).
  - Fields: `commit`, `timestamp` (UTC ISO), `config` (copied YAML or path), `platform` (os, python_version), `seed`.
- `cell_means.csv` — two-factor table (rows = A levels, cols = B levels).
- `bootstrap_replicates.parquet` or `bootstrap_replicates.pkl` — optional. If present, prefer Parquet for compactness.
- `bootstrap_ci.csv` — bootstrap CIs and SEs for each cell (flattened or MultiIndex-friendly CSV).
- `score.csv` — risk-adjusted score matrix saved as CSV.
- `logs/` — human-readable run logs (plain text). Keep logs reasonably small.
- `checkpoints/` — **do not commit large model checkpoints**; if you must, follow the project snapshot policy and document it in `data/README.md`.

## Naming conventions
- Run folder: `experiments/<category>/<dataset>/<run_id>/seed_<seed>/`
- Metrics file: `metrics.json`
- Metadata file: `run_metadata.json`

## Best practices
- Create output directories programmatically (`mkdir -p`) before writing files.
- Save small metrics and metadata to the run folder and include them in the repo (or CI artifacts) for easy inspection.
- Large artifacts (multi-GB checkpoints) should be stored externally (S3, Zenodo, DVC remote). Store only pointers or checksums in the run folder.
- Keep `metrics.json` concise — use it as the canonical input for `scripts/make_tables_figs.py`.

## Example `metrics.json` (compact)
```json
{
  "dataset": "concrete",
  "run_id": "concrete_main_table",
  "seed": 0,
  "pci": 0.127,
  "n_cells": 12,
  "cell_means_mean": 32.45,
  "selected_cells": [["age_bin_0","cement_bin_2"], ["age_bin_3", "cement_bin_1"]],
  "selected_total_cost": 7.0
}
````

## Retention and cleanup

* Keep a small number of recent checkpoints or none in the repository. Use `experiments/<run>/checkpoints/README.md` to document checkpoint retention policy if needed.
* Consider compressing older run directories (`tar.gz`) for archival and remove bulky files from the working tree.

## Git tracking guidance

* Recommended `.gitignore` patterns (project root):

  ```
  experiments/*
  !experiments/**/metrics.json
  !experiments/**/run_metadata.json
  !experiments/**/.gitkeep
  ```

  This ignores heavy outputs by default but allows small, important metadata to be committed.

## How to share runs with reviewers

* Provide a tarball of a single run, or upload the relevant `metrics.json`, `run_metadata.json`, and small figures to the paper artifact storage.
* For GPU-heavy experiments, share Docker image digest and a small `experiments/` summary produced by the authors.
