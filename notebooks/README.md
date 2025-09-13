# notebooks/ — analysis and figure sketchbook

This folder contains optional exploratory Jupyter notebooks used for additional analyses, figure sketches, and reproducibility checks. Notebooks are *not required* for running the core reproduction pipeline, but they are useful for interactive data inspection, diagnostics, and preparing supplementary figures.

## Recommended usage
- Keep notebooks lightweight: prefer to save only plots, small summaries, and the code needed to reproduce them.
- Avoid committing large outputs (embedded images, datasets). Clear notebook outputs (`Kernel -> Restart & Clear Output`) before committing.
- When a notebook supports a figure used in the paper, create a short provenance note in the notebook (commit hash, input metrics file paths).

## Naming conventions
- Use descriptive names: `analysis_fmnist.ipynb`, `figure3_score_surface.ipynb`, `diagnostics_concrete.ipynb`.
- For one-off exploratory work, include the date in the filename, e.g. `explore_2025-09-01.ipynb`.

## Environment / kernel
- Use the project development environment (e.g., the `factors-cpu` conda env or `.venv`) to run notebooks. The notebook kernel should match Python >= 3.10 and have the same packages as specified in `envs/`.
- If you publish a notebook for reviewers, include a short header cell with:
  - `git rev-parse HEAD` commit hash
  - `python --version`
  - paths to input `experiments/.../metrics.json` or `results/...` used to generate figures

## Minimal provenance cell (paste at the top of a notebook)
```python
# Notebook provenance (run and save)
import subprocess, json, sys
from datetime import datetime
def git_hash():
    try:
        return subprocess.check_output(["git","rev-parse","HEAD"]).decode().strip()
    except Exception:
        return "no-git"
print("commit:", git_hash())
print("generated_at:", datetime.utcnow().isoformat()+"Z")
print("python:", sys.version.splitlines()[0])
````

## Git and CI guidance

* Add notebook `.ipynb` files to git only when they are cleaned (no large embedded outputs).
* Optionally add `notebooks/` to `.gitignore` if you do not wish to track exploratory work.
* Prefer exporting final, publication-ready figures to `results/figures/` and commit those small files instead of the full notebook outputs.

## Binder / interactive preview (optional)

* If you want to provide an interactive environment for reviewers, add a `binder/` or `.github/workflows/` configuration that references `envs/` and points to a kernel compatible with Python 3.10–3.12.

## Placeholder

If you want to keep the directory in Git, add a placeholder file:

```
notebooks/.gitkeep
```
