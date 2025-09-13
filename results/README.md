# results/ — aggregated paper artifacts (figures, tables, logs)

This directory stores aggregated outputs intended for the paper and reviewers: figures, tables, short logs, and summary metrics. Files here are the final artifacts (publication-quality figures, CSV/TeX tables) generated from `experiments/` outputs.

## Purpose
- Keep polished, ready-to-use figures and tables used in the manuscript.
- Central place for CI to upload artifacts and for reviewers to download final outputs.
- Ensure artifact provenance (which run/commit produced the figures).

## Suggested layout
````

results/
├─ logs/                 # small run logs or aggregation logs
├─ metrics/              # aggregated metrics CSV/JSON used for table generation
├─ figures/              # publication-ready figures (.pdf, .png)
│  ├─ fig1\_model\_comparison.pdf
│  └─ pci\_by\_dataset.png
└─ tables/               # CSV / .tex versions of tables used in the paper
├─ table1\_main.csv
└─ table1\_main.tex

````

## File conventions and quality
- **Figures**
  - Preferred formats: `pdf` (vector) for plots, `png` for raster where appropriate.
  - DPI: raster exports should be ≥ 300 DPI for publication.
  - Filenames: use descriptive short names, e.g., `fig2_score_surface.pdf`.
  - Include a small JSON or text sidecar (e.g., `fig2_score_surface.metadata.json`) linking the figure to the run(s)/commit(s) used to produce it.
- **Tables**
  - Save as both CSV (for machine-readability) and `.tex` (for manuscript inclusion) when possible.
  - Include a header comment or separate metadata file that lists the generating command and input metrics file(s).

## Provenance
Each artifact should include provenance information. Minimal required items:
- commit hash used to generate artifact
- input metrics file(s) / run IDs
- generation timestamp (UTC)

Example sidecar `results/figures/fig1.metadata.json`:
```json
{
  "commit": "abcdef1234567890",
  "generated_at": "2025-09-01T12:00:00Z",
  "inputs": ["experiments/main/concrete/concrete_main_table/seed_0/metrics.json"]
}
````

## Regeneration

To regenerate results from raw experiments:

1. Ensure experiments are present under `experiments/`.
2. Run:

```bash
# aggregate and produce summary tables/figures
scripts/make_tables_figs.py --inputs "experiments/**/metrics.json" --out results/figures
```

3. Inspect `results/figures/summary_metadata.json` after generation.

## CI artifact handling

* CI should upload `results/figures/*` and `results/tables/*` as job artifacts for reviewers.
* Keep artifacts small — avoid committing large assets (>50MB) to the repository.

## Archival and sharing

* For final submission, bundle `results/figures` and `results/tables` alongside a text file listing the commit hashes and exact commands used to generate the artifacts.
* If reproducibility requires heavy data or GPU runs, provide Docker image digest and a small sample run tarball.

## Recommended `.gitignore` rules (project root)

```
results/*
!results/figures/*.pdf
!results/tables/*.csv
!results/metrics/*
!results/.gitkeep
```

Adjust these rules depending on whether you prefer to commit final figures/tables or to rely on CI artifacts.

## Tips

* Keep figure generation code deterministic where possible (record seeds and library versions).
* Store small preview thumbnails (PNG) alongside PDFs for quick browsing in code hosting UIs.
* When updating figures, update sidecar provenance files to reflect the new commit and inputs.
