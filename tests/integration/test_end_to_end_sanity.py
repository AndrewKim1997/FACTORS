# Lightweight end-to-end sanity test that runs the CI-friendly config in configs/runs/sanity.yaml.
# The test executes scripts/run_experiment.py for the first sanity entry and verifies outputs exist.
# This test is intentionally conservative: it runs only one small sanity job and times out after a short interval.

from __future__ import annotations

import sys
import json
import subprocess
from pathlib import Path
import tempfile
import yaml
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts"
RUN_SCRIPT = SCRIPT_DIR / "run_experiment.py"
SANITY_YAML = ROOT / "configs" / "runs" / "sanity.yaml"

# ensure script is executable with current python interpreter
PY = sys.executable


def load_first_sanity_job():
    with SANITY_YAML.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    runs = cfg.get("sanity_runs", [])
    if not runs:
        raise RuntimeError("No sanity_runs found in configs/runs/sanity.yaml")
    return runs[0]


@pytest.mark.integration
def test_run_single_sanity_job(tmp_path):
    job = load_first_sanity_job()
    config = job["config"]
    seed = int(job["seeds"][0]) if isinstance(job.get("seeds"), list) and job.get("seeds") else int(job.get("seed", 0))
    out = tmp_path / "sanity_run"
    out.mkdir(parents=True, exist_ok=True)

    # Run the script with a reasonable timeout; the sanity config is expected to be fast.
    cmd = [PY, str(RUN_SCRIPT), "--config", str(config), "--seed", str(seed), "--out", str(out)]
    try:
        # allow up to 120 seconds for the sanity run
        subprocess.run(cmd, check=True, timeout=120)
    except subprocess.TimeoutExpired:
        pytest.fail("Sanity run timed out")
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Sanity run failed with exit code {e.returncode}")

    # Verify outputs
    metrics_file = out / "metrics.json"
    metadata_file = out / "run_metadata.json"
    assert metrics_file.exists(), f"Expected metrics.json at {metrics_file}"
    assert metadata_file.exists(), f"Expected run_metadata.json at {metadata_file}"

    # Ensure metrics.json is valid JSON and contains expected keys
    with metrics_file.open("r", encoding="utf-8") as f:
        metrics = json.load(f)
    assert "seed" in metrics or "n_rows" in metrics or "dataset" in metrics
