# Reproducibility guide — FACTORS

This document explains how to reproduce every experiment, table, and figure in the FACTORS paper. It gives a one-command quick path for reviewers, and a full path for anyone who wants to re-run the complete suite. All commands assume you are in the repository root (`factors/`). If something fails, follow the troubleshooting section at the end.

---

## Quick sanity check (CI-style)

These commands run a fast smoke test that verifies the repo, environment, and a tiny end-to-end run.

```bash
# 1. create a minimal environment (CPU)
conda env create -f envs/conda-cpu.yml -n factors-sanity
conda activate factors-sanity

# 2. install the package in editable mode
pip install -e .

# 3. run the fast sanity configuration used by CI
python scripts/run_experiment.py --config configs/runs/sanity.yaml --seed 0 --out experiments/sanity/run0

# 4. generate the paper artifacts from the produced metrics
python scripts/make_tables_figs.py --metrics experiments/sanity/run0/metrics.json --out results/figures/sanity
```

If the above succeeds and `results/figures/sanity` contains PDF/PNG files, the basic reproduction stack is working.

---

## Full reproduction (single command)

A single command that attempts to reproduce all main-paper figures and tables and store them under `results/`:

```bash
# local full reproduction (CPU)
make setup                       # installs dependencies, prepares data (see Makefile)
make reproduce                   # runs reproduce_all.sh which executes the main run list
```

`make reproduce` is a wrapper for `scripts/reproduce_all.sh` and will:

* create required conda or pip environment,
* download and validate datasets,
* run the main experiments listed in `configs/runs/main.yaml` with the canonical seed list,
* assemble tables and figures into `results/tables` and `results/figures`.

Use `MAKEFLAGS="-j4"` if you want parallel execution where applicable, but be mindful of memory.

---

## Docker reproduction (recommended for reviewers)

We provide separate Dockerfiles for CPU and GPU to reduce environment mismatch.

### Build images

```bash
# Build CPU image
docker build -f docker/Dockerfile.cpu -t factors:cpu .

# Build GPU image (requires a host with NVIDIA drivers and buildx if cross-platform)
docker build -f docker/Dockerfile.gpu -t factors:gpu .
```

### Run reproduction inside Docker

```bash
# CPU
docker run --rm -v "$(pwd)":/workspace -w /workspace factors:cpu bash -c "make reproduce_docker_cpu"

# GPU (use --gpus all on supported Docker engine)
docker run --rm --gpus all -v "$(pwd)":/workspace -w /workspace factors:gpu bash -c "make reproduce_docker_gpu"
```

Notes:

* Docker builds verify package installation and reproducibility scripts but do not guarantee bitwise identical GPU floating point outputs across different driver versions. See "Determinism and randomness" below.
* If you cannot run GPU Docker on GitHub runners, use a local or self-hosted runner for GPU tests.

---

## How to run a single experiment (fine control)

To reproduce a single plot or table, run the corresponding config:

```bash
# run one config, with explicit output folder and seed
python scripts/run_experiment.py \
  --config configs/datasets/concrete.yaml \
  --seed 42 \
  --out experiments/main/concrete_seed42
```

After the experiment finishes, create figures/tables for that run:

```bash
python scripts/make_tables_figs.py \
  --metrics experiments/main/concrete_seed42/metrics.json \
  --out results/figures/concrete_seed42
```

`run_experiment.py` accepts the following important flags:

* `--config` path to a YAML config
* `--seed` integer RNG seed
* `--out` output directory for logs, checkpoints, metrics
* `--device` optional override (`cpu` or `cuda`)
* `--deterministic` optional flag to turn on deterministic mode

See `scripts/run_experiment.py --help` for details.

---

## Environment and versioning

To make reproduction verifiable, always record and share the following:

1. **Git commit**: the exact commit hash used to run experiments.

   ```bash
   git rev-parse HEAD > experiments/<run>/commit.txt
   ```

2. **Environment spec**: record conda or pip specs used.

   ```bash
   conda env export > experiments/<run>/env.yaml
   pip freeze > experiments/<run>/pip-freeze.txt
   ```

3. **Docker image**: save the built image tag and digest if using Docker.

   ```bash
   docker image inspect factors:cpu --format='{{index .RepoDigests 0}}' > experiments/<run>/image_digest.txt
   ```

4. **Data checksums**: validate all input datasets with SHA256 and save hashes in `experiments/<run>/data_hashes.json`.

5. **Config snapshot**: copy the exact YAML(s) used into the run folder.

   ```bash
   cp configs/runs/main.yaml experiments/<run>/config_used.yaml
   ```

Our `scripts/reproduce_all.sh` performs these bookkeeping steps automatically.

---

## Determinism and randomness

Bitwise exact reproduction across different machines is hard, especially on GPU. Use these practices to maximize reproducibility:

* Set all RNG seeds at process start:

  * `PYTHONHASHSEED` environment variable
  * `numpy.random.seed(seed)`
  * `random.seed(seed)`
  * `torch.manual_seed(seed)` and `torch.cuda.manual_seed_all(seed)`

* Force deterministic algorithms when possible:

  ```python
  import torch
  torch.backends.cudnn.deterministic = True
  torch.backends.cudnn.benchmark = False
  torch.use_deterministic_algorithms(True)  # pytorch >=1.8
  ```

  Warning: enabling deterministic algorithms may degrade performance and may not be supported by all ops. Some operations have no deterministic kernel on GPU.

* Record the list of seeds used for multi-seed runs in `experiments/<run>/seeds.txt`.

* For final verification, prefer *distributional* reproduction: re-run with the same seed list and confirm that key statistics (means, 95% CIs) match within reported confidence intervals rather than requiring exact identical floating values.

---

## Data download and validation

All public datasets are downloaded by `scripts/download_data.sh`. After download, the script computes SHA256 checksums and writes them to `data/hashes.json`. To validate manually:

```bash
sha256sum data/raw/<dataset_file>   # compare with data/hashes.json
```

If a public dataset is removed or updated, keep a snapshot of the original file under `data/raw/snapshots/` and add a reference in `data/hashes.json`.

---

## Expected outputs and file layout

* Experiment outputs are under `experiments/<experiment_name>/<seed>/` and include:

  * `metrics.json` (CSV-compatible summary for table generation)
  * `logs/` (training logs and stdout)
  * `checkpoints/` (model checkpoints, optional)
  * `commit.txt`, `env.yaml`, `data_hashes.json`, `config_used.yaml`, `seeds.txt`

* Paper artifacts are under `results/`:

  * `results/figures/*.pdf` and `results/figures/*.png`
  * `results/tables/*.csv` and `results/tables/*.tex`
  * The `paper/` folder expects `results/figures` and `results/tables` to exist for final compilation.

---

## CI behavior

The repository contains two CI workflows:

* `.github/workflows/ci.yml` runs:

  * linter (ruff/flake8), unit tests (`pytest -q`), and the quick sanity experiment (`configs/runs/sanity.yaml`).
  * artifacts from the sanity run are uploaded as CI artifacts.

* `.github/workflows/docker-ci.yml` runs:

  * CPU and GPU Docker image builds and basic container smoke checks. It does not run long training on GPU; it only validates build and entrypoint.

CI will fail if:

* Unit tests fail
* The sanity experiment fails to complete within the workflow timeouts
* Docker images fail to build

---

## Troubleshooting (common issues)

* **CUDA / driver mismatch**: Check `nvidia-smi` and CUDA toolkit versions inside the Docker image. Use `docker/Dockerfile.gpu` CUDA base that matches your driver.
* **Out of memory**: reduce batch size in the config, or run on CPU for a smaller test.
* **Dataset download fails**: check network, mirror, or manually place dataset into `data/raw/` and run `sha256sum` to validate.
* **Non-deterministic metrics on GPU**: rerun with deterministic flags, or run multiple seeds and compare mean ± CI.
* **Permission issues with Docker**: run `docker` as a user in the `docker` group or use `sudo` for local experiments.
* **CI failure for docker-ci**: check builder logs for missing buildkit or incompatible multi-stage steps on the runner.

If everything fails, open an issue on the repository with label `reproducibility` and include:

* `experiments/<run>/logs/` content
* `experiments/<run>/env.yaml` or `pip-freeze`
* `experiments/<run>/commit.txt`
* brief description of the hardware you used (CPU model, RAM, GPU model, driver version, OS release)

---

## Tips for reviewers

* The fastest way to confirm reproducibility is:

  1. run the Quick sanity check,
  2. inspect `results/figures/sanity` and `experiments/sanity/run0/metrics.json`,
  3. then run a single full configuration from `configs/runs/main.yaml` that corresponds to a figure or table you care about.

* If you need GPU validation for some heavy experiment and cannot run it locally, request the docker image digest and a saved `experiments/<run>` tarball from the authors.

---

## Contact and bug reporting

When reporting problems, please include:

* repository commit hash (`git rev-parse HEAD`)
* OS and CPU/GPU specs
* exact command used
* contents of `experiments/<run>/env.yaml` and `experiments/<run>/logs/`

Open a GitHub issue with label `reproducibility` and attach the above artifacts.

---

## Minimal reproducibility checklist (copy into `REPRODUCIBILITY.md` top of run)

1. commit hash recorded
2. environment dumped (`env.yaml` or `pip-freeze.txt`)
3. data checksums recorded
4. config(s) used are copied to run folder
5. seed list recorded
6. outputs (metrics, figures, tables) saved under `results/`
7. Docker image digest recorded if Docker used

---

If you want, I can now:

* produce `REPRODUCIBILITY.md` as a file in the repository (ready to paste),
* or generate the `Makefile` targets referenced above and skeletons for `scripts/reproduce_all.sh` and `scripts/run_experiment.py` usage examples. Which one should I generate next?
