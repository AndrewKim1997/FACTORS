# Data directory policy

This file documents the repository's data handling policy and provides concrete instructions for downloading, verifying, and storing datasets used by experiments. Keep this file in `data/README.md` and update it whenever dataset procedures change.

---

## Purpose

* Avoid committing large binary datasets to Git.
* Provide reproducible, auditable instructions for obtaining input data used by experiments.
* Track minimal metadata (checksums, provenance) necessary for verification and review.
* Offer guidance for snapshotting small files when a public source becomes unavailable.

---

## Directory layout

```
data/
├─ raw/                # raw downloaded files; do NOT commit large binaries
│  ├─ snapshots/       # small archived snapshots if public source disappears (small files only)
│  └─ .gitkeep
└─ processed/          # processed / cached artifacts used by scripts (prefer external storage)
   └─ .gitkeep
```

**Important:** Only placeholder files like `.gitkeep` and small metadata (JSON, YAML, checksums) should be committed. Large raw data files must be downloaded by scripts or stored with a data-management tool.

---

## Recommended files

* `data/hashes.json` — JSON mapping of expected filenames to SHA256 checksums and source URLs. Example:

```json
{
  "raw/concrete/Concrete_Data.csv": {
    "sha256": "012345abcdef...7890",
    "url": "https://archive.ics.uci.edu/...",
    "notes": "UCI Concrete dataset, downloaded 2025-09-01"
  }
}
```

* `data/README.md` — this document.
* `data/raw/.gitkeep` and `data/processed/.gitkeep` — placeholders so Git keeps the directories.

---

## Guidelines

1. **Do not commit large files.** If a file is larger than a few MBs, prefer external hosting (S3, Zenodo, OSF, figshare, or institutional storage).
2. **Automate downloads.** Use `scripts/download_data.sh` (or a more advanced Python downloader) to fetch public datasets.
3. **Record checksums.** After downloading, compute SHA256 and add entries to `data/hashes.json`. Do not modify hashes except when intentionally updating the canonical snapshot and documenting why.
4. **Use snapshots sparingly.** Only add a small snapshot to `data/raw/snapshots/` when the public source becomes unavailable or the original file must be preserved for reproducibility. Snapshots must be small, licensed for redistribution, and include provenance metadata.
5. **Prefer processed caches over raw commits.** If a processed cache (e.g., cleaned CSV or Parquet subset used in experiments) is small (<10MB), you may commit it under `data/processed/` with a clear `processed/README` describing how it was created.

---

## Download and verification examples

### Download with the provided script

From repository root:

```bash
# download specific datasets supported by scripts/download_data.sh
scripts/download_data.sh concrete car fmnist
```

### Compute SHA256 checksum (Linux/macOS)

```bash
sha256sum data/raw/concrete/Concrete_Data.csv
# or on macOS (BSD coreutils)
shasum -a 256 data/raw/concrete/Concrete_Data.csv
```

### Verify checksum against `data/hashes.json` (simple jq example)

```bash
# prints stored sha for file then compares to computed sha
expected=$(jq -r '."raw/concrete/Concrete_Data.csv".sha256' data/hashes.json)
actual=$(sha256sum data/raw/concrete/Concrete_Data.csv | awk '{print $1}')
if [ "$expected" = "$actual" ]; then
  echo "OK: checksum matches"
else
  echo "MISMATCH: expected $expected but got $actual"
  exit 1
fi
```

---

## Snapshot policy (when to add files to `data/raw/snapshots/`)

* Add a snapshot only if:

  * The original public source was removed, or
  * The canonical file used in the paper has changed and you must preserve the exact artifact for reproducibility.
* Snapshot file restrictions:

  * Keep snapshots small (metadata, curated CSVs). Avoid storing multi-GB binaries in the repository.
  * Include a `snaphots/README` with provenance, license, and a TTL (how long you will keep the snapshot).
  * Add an entry in `data/hashes.json` for each snapshot you add.

---

## Large-data alternatives

If your project needs to handle large data, consider one of these patterns:

* **DVC (Data Version Control)** — track data pointers and store large files in remote storage.
* **Git LFS** — store large files in LFS-backed storage (works for some CI setups).
* **External archive (Zenodo / OSF / S3)** — host large, immutable artifacts and reference them in `data/hashes.json`.

Document whichever approach you adopt in this README.

---

## Adding a new dataset (recommended checklist)

1. Add download logic to `scripts/download_data.sh` (or scripts/download\_data.py).
2. Add a `configs/datasets/<name>.yaml` file describing the dataset and file paths.
3. Download locally and compute SHA256:

   ```bash
   sha256sum path/to/downloaded/file > tmp.sha
   ```
4. Add an entry to `data/hashes.json` with `url`, `sha256`, and `notes`.
5. If the processed artifact is small and useful to share, add it to `data/processed/` with a short `processed/README` describing how it was derived.

---

## .gitignore recommendations

Append these lines to the repository `.gitignore` to prevent accidental commits of large files:

```
# data files (do not commit large datasets)
data/raw/*
!data/raw/.gitkeep
!data/raw/snapshots/
data/processed/*
!data/processed/.gitkeep
# allow small metadata files
!data/hashes.json
```

Adjust whitelist/blacklist rules according to your snapshot policy.

---

## Security and licensing

* Verify dataset licenses before redistributing snapshots. If a dataset forbids redistribution, do not add a snapshot to the repository; instead, provide download instructions and the original URL.
* Never commit API keys, tokens, or other secrets into `data/` or the repository.

---

## Troubleshooting

* If a checksum verification fails, re-download the file and re-check SHA256. If the public source changed, document the new checksum and reason in `data/hashes.json`.
* For corrupted downloads, try using `curl -L --fail -O <url>` or the Python downloader with retries.
* For very large datasets that cannot be re-hosted, create a small reproducible subset and store that under `data/processed/` (document how the subset was created).

---

## Contact

If you need to change the data policy or you believe a snapshot should be added, open a GitHub issue labeled `data` and include:

* dataset identifier and source URL
* reason for snapshot
* expected size and license information

---
