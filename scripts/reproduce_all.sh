#!/usr/bin/env bash
# scripts/reproduce_all.sh
# Reproduce pipeline driver: iterate entries in configs/runs/main.yaml and execute run_experiment.py for each listed seed.
# This script is intentionally conservative: it runs sequentially by default to simplify resource usage.
#
# Usage:
#   scripts/reproduce_all.sh            # run all canonical runs (may be long)
#   scripts/reproduce_all.sh --limit 2  # only run first 2 canonical entries
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
RUN_SCRIPT="${REPO_ROOT}/scripts/run_experiment.py"
MAIN_YAML="${REPO_ROOT}/configs/runs/main.yaml"

if [ ! -f "$MAIN_YAML" ]; then
  echo "Main runs file not found: $MAIN_YAML"
  exit 1
fi

LIMIT="${1:-}"  # optional positional limit (number of canonical run entries)
if [ "$LIMIT" != "" ] && [ "$LIMIT" != "--limit" ]; then
  # if user passed a number as first arg
  LIMIT="$1"
fi

# Use Python to parse the YAML and emit JSON lines describing each run to execute.
PY_SCRIPT=$(cat <<'PY'
import sys, yaml, json, pathlib
p = pathlib.Path(sys.argv[1])
data = yaml.safe_load(p.read_text())
runs = data.get("canonical_runs", [])
limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "" else None
count = 0
for r in runs:
    if limit is not None and count >= limit:
        break
    seeds = r.get("seeds", [0])
    template = r.get("output_template", "experiments/{dataset}/{id}/seed_{seed}")
    cfg = r.get("config")
    for s in seeds:
        out = template.format(dataset=r.get("dataset", "unknown"), id=r.get("id", "run"), seed=s)
        print(json.dumps({"config": cfg, "seed": int(s), "out": out}))
    count += 1
PY
)

# Run the Python snippet to produce job list
JOBLIST=$($PYTHON - <<PY
$PY_SCRIPT
import sys
# arguments: main yaml path and optional limit
args = sys.argv
PY
PY "$MAIN_YAML" "${LIMIT:-}")

# Above attempt may be brittle on some shells; fallback: invoke a temporary python file
if [ -z "$JOBLIST" ]; then
  TMPPY="$(mktemp --suffix=.py)"
  cat > "$TMPPY" <<'PY'
import sys, yaml, json, pathlib
p = pathlib.Path(sys.argv[1])
data = yaml.safe_load(p.read_text())
runs = data.get("canonical_runs", [])
limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "" else None
count = 0
for r in runs:
    if limit is not None and count >= limit:
        break
    seeds = r.get("seeds", [0])
    template = r.get("output_template", "experiments/{dataset}/{id}/seed_{seed}")
    cfg = r.get("config")
    for s in seeds:
        out = template.format(dataset=r.get("dataset", "unknown"), id=r.get("id", "run"), seed=s)
        print(json.dumps({"config": cfg, "seed": int(s), "out": out}))
    count += 1
PY
  JOBLIST=$($PYTHON "$TMPPY" "$MAIN_YAML" "${LIMIT:-}")
  rm -f "$TMPPY"
fi

echo "$JOBLIST" | jq -c -r '. as $j | ($j.config + " " + ($j.seed|tostring) + " " + $j.out)' | while read -r config seed out; do
  echo "[reproduce_all] running config=$config seed=$seed out=$out"
  mkdir -p "$(dirname "$REPO_ROOT/$out")" || true
  $PYTHON "$RUN_SCRIPT" --config "$config" --seed "$seed" --out "$out" || {
    echo "[reproduce_all] run failed for config=$config seed=$seed; continuing"
  }
done

echo "[reproduce_all] all done"
