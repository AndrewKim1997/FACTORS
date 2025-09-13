# Makefile for FACTORS repository
# All comments and messages are in English.
# Usage:
#   make help                # show available targets
#   make setup               # create local dev environment and install package
#   make test                # run unit tests
#   make reproduce           # run full reproduction pipeline (calls scripts/reproduce_all.sh)
#   make docker-cpu-build    # build CPU Docker image
#   make docker-gpu-build    # build GPU Docker image
#   make docker-cpu-reproduce# run reproduction inside CPU Docker container
#   make docker-gpu-reproduce# run reproduction inside GPU Docker container

SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c

# ---------- Configuration variables (tweak as needed) ----------
CONDA_ENV_NAME ?= factors-dev
PYTHON ?= python3
PIP ?= pip
# pip requirements for CPU/GPU
PIP_REQ_CPU ?= envs/pip-cpu.txt
PIP_REQ_GPU ?= envs/pip-gpu.txt

# docker / registry config
DOCKER_REGISTRY ?= ghcr.io/yourorg
GIT_SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo local)
IMAGE_CPU := $(DOCKER_REGISTRY)/factors:cpu-$(GIT_SHA)
IMAGE_GPU := $(DOCKER_REGISTRY)/factors:gpu-$(GIT_SHA)

# default python module entrypoints (scripts must exist)
RUN_SCRIPT ?= scripts/run_experiment.py
REPRODUCE_SCRIPT ?= scripts/reproduce_all.sh

# ---------- Convenience / meta targets ----------
.PHONY: help
help:
	@echo "FACTORS Makefile - available targets"
	@echo "  help                    - show this message"
	@echo "  setup                   - create development environment (conda preferred) and install package"
	@echo "  env-export              - export current env (conda or pip freeze) into experiments/<run>/"
	@echo "  lint                    - run linters (ruff/flake8 if available)"
	@echo "  format                  - format code with black"
	@echo "  test                    - run unit tests (pytest)"
	@echo "  smoke                   - run quick sanity experiment (configs/runs/sanity.yaml)"
	@echo "  reproduce               - run full reproduction script (scripts/reproduce_all.sh)"
	@echo "  docker-cpu-build        - build CPU Docker image ($(IMAGE_CPU))"
	@echo "  docker-gpu-build        - build GPU Docker image ($(IMAGE_GPU))"
	@echo "  docker-cpu-reproduce    - run reproduce inside CPU Docker container"
	@echo "  docker-gpu-reproduce    - run reproduce inside GPU Docker container"
	@echo "  clean                   - remove generated artifacts (experiments/ results/)"
	@echo ""
	@echo "Variables you can override on the command line:"
	@echo "  make setup CONDA_ENV_NAME=myenv"
	@echo "  make docker-cpu-build DOCKER_REGISTRY=myreg"

# ---------- Environment setup ----------
.PHONY: setup
setup:
	@echo ">>> Setup development environment"
	# Prefer conda if available
	if command -v conda >/dev/null 2>&1; then
	  echo "Creating conda environment '$(CONDA_ENV_NAME)' from envs/conda-cpu.yml"
	  conda env create -f envs/conda-cpu.yml -n $(CONDA_ENV_NAME) || echo "Conda env may already exist"
	  echo "Activate with: conda activate $(CONDA_ENV_NAME)"
	  echo "Installing package in editable mode"
	  source activate $(CONDA_ENV_NAME)
	  pip install -e .
	else
	  echo "Conda not found, falling back to virtualenv"
	  $(PYTHON) -m venv .venv
	  source .venv/bin/activate
	  $(PIP) install -r $(PIP_REQ_CPU)
	  $(PIP) install -e .
	fi
	@echo ">>> Setup complete"

.PHONY: env-export
env-export:
	@echo ">>> Exporting environment information (conda env or pip freeze)"
	mkdir -p experiments/env_exports || true
	if command -v conda >/dev/null 2>&1 && conda env list | grep -q $(CONDA_ENV_NAME); then
	  conda env export -n $(CONDA_ENV_NAME) > experiments/env_exports/$(CONDA_ENV_NAME)-env.yaml
	else
	  pip freeze > experiments/env_exports/pip-freeze.txt
	fi
	@echo ">>> Environment export saved to experiments/env_exports/"

# ---------- Code quality ----------
.PHONY: lint
lint:
	@echo ">>> Running linters (ruff then flake8 if available)"
	if command -v ruff >/dev/null 2>&1; then
	  ruff check src tests || true
	else
	  echo "ruff not found, skipping"
	fi
	if command -v flake8 >/dev/null 2>&1; then
	  flake8 src tests || true
	else
	  echo "flake8 not found, skipping"
	fi

.PHONY: format
format:
	@echo ">>> Formatting code with black (if installed)"
	if command -v black >/dev/null 2>&1; then
	  black src tests
	else
	  echo "black not found, skipping"
	fi

# ---------- Tests ----------
.PHONY: test
test:
	@echo ">>> Running unit tests with pytest"
	pytest tests/unit -q

# ---------- Quick smoke / sanity run ----------
.PHONY: smoke
smoke:
	@echo ">>> Running quick sanity experiment (configs/runs/sanity.yaml)"
	$(PYTHON) $(RUN_SCRIPT) --config configs/runs/sanity.yaml --seed 0 --out experiments/sanity/run0
	@echo ">>> Sanity run complete. Check experiments/sanity/run0/"

# ---------- Full reproduction ----------
.PHONY: reproduce
reproduce:
	@echo ">>> Running full reproduction script"
	chmod +x $(REPRODUCE_SCRIPT) || true
	./$(REPRODUCE_SCRIPT)

# ---------- Docker images and reproduce inside container ----------
.PHONY: docker-cpu-build
docker-cpu-build:
	@echo ">>> Building CPU Docker image: $(IMAGE_CPU)"
	docker build -f docker/Dockerfile.cpu -t $(IMAGE_CPU) .

.PHONY: docker-gpu-build
docker-gpu-build:
	@echo ">>> Building GPU Docker image: $(IMAGE_GPU)"
	docker build -f docker/Dockerfile.gpu -t $(IMAGE_GPU) .

.PHONY: docker-cpu-reproduce
docker-cpu-reproduce:
	@echo ">>> Running reproduction inside CPU Docker container (image: $(IMAGE_CPU))"
	# mount current repo into /workspace and run the container command that calls reproduction
	docker run --rm -v "$(PWD)":/workspace -w /workspace $(IMAGE_CPU) bash -lc "chmod +x $(REPRODUCE_SCRIPT) && ./$(REPRODUCE_SCRIPT)"

.PHONY: docker-gpu-reproduce
docker-gpu-reproduce:
	@echo ">>> Running reproduction inside GPU Docker container (image: $(IMAGE_GPU))"
	# note: host must support --gpus flag and have NVIDIA drivers installed
	docker run --rm --gpus all -v "$(PWD)":/workspace -w /workspace $(IMAGE_GPU) bash -lc "chmod +x $(REPRODUCE_SCRIPT) && ./$(REPRODUCE_SCRIPT)"

# ---------- Helper: build wheel and install (useful for CI) ----------
.PHONY: build-wheel
build-wheel:
	@echo ">>> Building wheel package"
	$(PYTHON) -m pip install --upgrade build
	$(PYTHON) -m build

# ---------- Clean generated artifacts ----------
.PHONY: clean
clean:
	@echo ">>> Cleaning experiments/ and results/ (keep data/ and scripts/)"
	rm -rf experiments/* results/* results || true
	find . -type d -name "__pycache__" -exec rm -rf {} + || true
	@echo ">>> Clean complete"

# ---------- Convenience: show docker image tags (local) ----------
.PHONY: docker-images
docker-images:
	@echo "Local built images for this repo may include:"
	docker images | grep factors || true
