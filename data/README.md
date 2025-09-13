# Data directory — FACTORS

This folder contains dataset artifacts used by experiments. Large binary files **must not** be committed to the repository. The repository keeps only tiny placeholders and metadata; actual dataset files are downloaded or stored externally.

Structure
- `data/raw/` — raw downloaded files (original archives, CSVs). Do **not** commit large files.
- `data/processed/` — cleaned / preprocessed files (parquet, npz) used by experiments. Keep only small caches here; prefer reproducing processed files from raw when possible.
- `data/raw/.gitkeep` and `data/processed/.gitkeep` exist to ensure the directories are tracked when empty.

Principles
- Never check in large binaries or model checkpoints into git. Use external storage (institutional S3, Zenodo, figshare, or Git LFS when appropriate).
- For datasets that may disappear from the web, include a **snapshot** under `data/raw/snapshots/` with clear metadata and the reason for snapshotting.
- Always record checksums (SHA256) for any raw file used in experiments in `data/hashes.json` at repo root or `data/hashes.json`.
- Provide a short provenance note (download URL, date, commit hash of downloader) in the dataset folder or a central metadata file.

Quick workflow examples
```bash
# create dataset folder and placeholder
mkdir -p data/raw/mydataset
touch data/raw/.gitkeep

# download a file (example)
curl -L -o data/raw/mydataset/myfile.csv "https://example.com/data.csv"

# compute and show sha256
sha256sum data/raw/mydataset/myfile.csv

# add checksum entry (manual): add to data/hashes.json with key "mydataset/myfile.csv"
