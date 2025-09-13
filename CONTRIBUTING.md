# CONTRIBUTING.md

Thank you for wanting to contribute to FACTORS. This document explains how to report issues, propose changes, and submit code or experiment artifacts in a way that keeps the repository stable and reproducible. All instructions and examples are written in English.

---

## Table of contents

* How to contribute
* Git workflow and branch naming
* Pull request checklist and PR template
* Issue reporting
* Developer environment setup
* Linting and tests
* Running experiments locally
* Docker and CI notes
* Adding new experiments or datasets
* Reproducibility requirements for contributions
* Code style and docstrings
* Maintainers and contact
* Code of conduct

---

## How to contribute

1. Check existing issues and pull requests before opening a new issue or PR.
2. For small fixes use the branch name `fix/<short-descr>`.
3. For features or experiments use `feat/<short-descr>` or `exp/<dataset>-<short-descr>`.
4. Open a PR against the `main` branch. Provide a clear, concise description and list of changes.

---

## Git workflow and branch naming

* Base branch: `main`
* Feature branches: `feat/<ticket>-short-description`
* Bugfix branches: `fix/<ticket>-short-description`
* Experiment branches: `exp/<dataset>-short-description`
* Hotfix branches (critical fixes): `hotfix/<short-description>`
* Keep branch names lowercase, hyphen-separated and meaningful.

Commit messages should follow the Conventional Commits style:

```
feat: add pci calculation and tests
fix: correct seed handling in run_experiment
docs: update reproducibility guide
chore: bump CI python version
```

A good commit message includes a short summary and, when helpful, one sentence more detail in the body.

---

## Pull request checklist and PR template

Before requesting review, ensure the following:

* [ ] Branch is up to date with `main`
* [ ] All unit tests pass locally
* [ ] Linting passes locally
* [ ] New public functions and classes include docstrings
* [ ] New code includes unit tests or integration tests
* [ ] `REPRODUCIBILITY.md` updated if the change affects reproduction
* [ ] `configs/` updated for any new experiments
* [ ] `Makefile` updated when new automation targets are required
* [ ] Dockerfiles updated and tested when runtime or dependency changes are required

Use this minimal PR description template:

**Title**
Short summary following Conventional Commits

**Summary**
One paragraph describing what the PR changes and why

**How to run**
Commands to reproduce the change locally, for example:

```bash
make setup
pytest tests/unit/test_new_feature.py
python scripts/run_experiment.py --config configs/datasets/new_dataset.yaml --seed 0
```

**Checklist**
Include the checklist above and tick items that apply

---

## Issue reporting

When opening an issue include:

* Repository commit hash. Run `git rev-parse HEAD` and paste result.
* Operating system, Python version, CUDA and driver versions if applicable.
* Full error trace or failing test output.
* Short reproduction steps and commands.
* Attach relevant log files from `experiments/<run>/logs/` or CI artifact links when available.

Label issues by type: `bug`, `feature`, `experiment`, `docs`, `reproducibility`.

---

## Developer environment setup

Quick dev setup using conda:

```bash
# create CPU development environment
conda env create -f envs/conda-cpu.yml -n factors-dev
conda activate factors-dev

# install the package in editable mode
pip install -e .

# run a quick smoke test
python scripts/run_experiment.py --config configs/runs/sanity.yaml --seed 0 --out experiments/sanity/run0
```

If you prefer pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r envs/pip-cpu.txt
pip install -e .
```

---

## Linting and tests

We use ruff or flake8 for linting and pytest for tests.

Run linting:

```bash
# ruff
ruff check src tests

# or flake8
flake8 src tests
```

Run unit tests:

```bash
pytest tests/unit -q
```

Run integration (slow) tests:

```bash
pytest tests/integration -q
```

Tests are grouped by markers:

* unit: fast unit tests
* integration: longer end-to-end sanity checks
* gpu: tests that require GPU hardware or GPU-specific ops

CI runs `pytest -q` for unit tests and the sanity integration test configured in `configs/runs/sanity.yaml`. Avoid adding heavy GPU-only tests to CI unless they are gated to run on self-hosted runners.

---

## Running experiments locally

To run an experiment:

```bash
python scripts/run_experiment.py --config configs/datasets/concrete.yaml --seed 42 --out experiments/main/concrete_seed42
```

Generate paper tables and figures for a run:

```bash
python scripts/make_tables_figs.py --metrics experiments/main/concrete_seed42/metrics.json --out results/figures/concrete_seed42
```

Use `configs/runs/main.yaml` to see canonical runs used to build the paper artifacts. To add a new canonical run, update that YAML and include it in `scripts/reproduce_all.sh`.

---

## Docker and CI notes

The repository has two CI workflows:

* `ci.yml` runs lint, unit tests, and a fast sanity integration run.
* `docker-ci.yml` builds Docker images and validates entrypoint behavior.

Dockerfiles are split to reduce environment mismatch:

* `docker/Dockerfile.cpu` for CPU builds
* `docker/Dockerfile.gpu` for GPU builds

Build locally:

```bash
docker build -f docker/Dockerfile.cpu -t factors:cpu .
docker build -f docker/Dockerfile.gpu -t factors:gpu .
```

Run local reproduce inside CPU container:

```bash
docker run --rm -v "$(pwd)":/workspace -w /workspace factors:cpu bash -c "make reproduce_docker_cpu"
```

Note: GPU builds require a proper NVIDIA driver on the host and Docker Engine that supports `--gpus`.

CI considerations:

* Avoid adding long-running GPU experiments to `ci.yml`
* `docker-ci.yml` should validate image build and a short smoke command only
* If a contribution requires GPU verification, request a self-hosted GPU runner or provide prebuilt image digests and sample outputs

---

## Adding new experiments or datasets

When adding an experiment or dataset, follow these steps:

1. Add a YAML config under `configs/datasets/` or `configs/ablations/`.
2. Add any dataset download logic to `scripts/download_data.sh` and ensure checksums are added to `data/hashes.json`.
3. Add a fast `sanity` variant for CI under `configs/runs/` if appropriate.
4. Add a test in `tests/integration/` that runs the new config with reduced settings.
5. Add an entry to `configs/runs/main.yaml` only when you want the run included in the paper reproduction.
6. Document reproducibility steps and expected outputs in `REPRODUCIBILITY.md` and update `results/` paths if necessary.

Do not commit raw dataset files. Use `data/raw/snapshots/` with clear metadata only when the source dataset is removed from public access. Large files must be stored externally and referenced with download scripts.

---

## Reproducibility requirements for contributions

Any contribution that affects experiments must include:

* The exact config YAML used for the run copied into the run folder
* The seed or seed list used
* A snapshot of the conda or pip environment saved in the run folder
* SHA256 checksums for input datasets used
* If Docker is used, the image tag and digest
* Unit tests that cover new code paths where feasible

When adding or changing a method that appears in the manuscript, update `REPRODUCIBILITY.md` to include the new reproduction commands and expected results.

---

## Code style and documentation

* Python formatting: use `black` for code formatting
* Lint: use `ruff` or `flake8`
* Type hints: prefer adding type annotations for public functions and classes
* Docstrings: use Google or NumPy style docstrings for public API
* Public API: add minimal examples in docstrings when useful

---

## Tests for new code

* Add unit tests for mathematical routines, shape checks, edge cases
* Add small integration tests for experiment code that only run a few iterations and are CI friendly
* Use deterministic seeds in tests and avoid relying on heavy randomness

---

## Maintainers and contact

Primary maintainers:

* Wonjun Jeong
* Dongseok Kim
* Taegkeun Whangbo

For reproducibility issues open an issue with the `reproducibility` label and include run artifacts as described in `REPRODUCIBILITY.md`. For urgent or larger contributions, contact the maintainers via GitHub handle mentioned in the repository.

---

## Code of conduct

Please follow the repository `CODE_OF_CONDUCT.md`. Be respectful, inclusive, and constructive in comments and reviews.

---

Thank you for contributing. Well structured contributions help us keep experiments reproducible and the codebase healthy. If you want, I can now generate a pull request template and an issue template that matches these guidelines. Which would you like next?
