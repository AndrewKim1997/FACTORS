#!/usr/bin/env bash
# scripts/download_data.sh
# Minimal dataset downloader for commonly used datasets in this repo.
# Usage:
#   scripts/download_data.sh all
#   scripts/download_data.sh concrete car fmnist
#
# This script does not require external YAML parsing tools; it uses
# hard-coded dataset download commands that match configs/datasets/*.
# If you prefer automatic parsing, replace this script with a Python downloader.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="${REPO_ROOT}/data/raw"

mkdir -p "${DATA_DIR}"

download_concrete() {
  echo "[download] Concrete dataset"
  url="https://archive.ics.uci.edu/ml/machine-learning-databases/concrete/compressive/Concrete_Data.csv"
  out="${DATA_DIR}/concrete/Concrete_Data.csv"
  mkdir -p "$(dirname "$out")"
  if [ -f "$out" ]; then
    echo "[download] Concrete already exists at $out, skipping"
    return
  fi
  echo "[download] fetching $url -> $out"
  curl -L --fail -o "$out" "$url"
  echo "[download] done"
}

download_car() {
  echo "[download] Car dataset"
  url="https://archive.ics.uci.edu/ml/machine-learning-databases/car/car.data"
  out="${DATA_DIR}/car/car.data"
  mkdir -p "$(dirname "$out")"
  if [ -f "$out" ]; then
    echo "[download] Car already exists at $out, skipping"
    return
  fi
  echo "[download] fetching $url -> $out"
  curl -L --fail -o "$out" "$url"
  echo "[download] done"
}

download_fmnist() {
  echo "[download] Fashion-MNIST (via torchvision will download automatically on first run)"
  # Touch directory to indicate intent; actual download is handled by torchvision in run_experiment
  outdir="${DATA_DIR}/fmnist"
  mkdir -p "$outdir"
  echo "[download] Created directory $outdir. If you want to prefetch files, run a short Python snippet:"
  echo "    python - <<PY
from torchvision.datasets import FashionMNIST
FashionMNIST(root='${outdir}', download=True)
print('Downloaded Fashion-MNIST to ${outdir}')
PY"
}

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <dataset|all>"
  echo "Supported datasets: concrete car fmnist all"
  exit 1
fi

for name in "$@"; do
  case "$name" in
    concrete)
      download_concrete
      ;;
    car)
      download_car
      ;;
    fmnist)
      download_fmnist
      ;;
    all)
      download_concrete
      download_car
      download_fmnist
      ;;
    *)
      echo "Unknown dataset: $name"
      exit 2
      ;;
  esac
done

echo "[download] finished"
