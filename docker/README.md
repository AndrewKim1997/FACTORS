# Docker development guide — FACTORS

This README explains how to build and run the local development Compose files for CPU and GPU workflows.

## Prerequisites

- Docker Engine installed.
- For GPU workflows: NVIDIA drivers on the host and NVIDIA Container Toolkit (nvidia-docker2) configured.
- Recommended: Docker Compose v2 (the `docker compose` CLI). If you use the older `docker-compose` binary, replace `docker compose` with `docker-compose` in the commands below.

## Build and start the CPU development container

```bash
# From repository root (one level above this docker/ folder)
docker compose -f docker/compose.dev.cpu.yml build
docker compose -f docker/compose.dev.cpu.yml up -d
````

Open an interactive shell inside the running container:

```bash
docker compose -f docker/compose.dev.cpu.yml exec factors bash
# now you are in /workspace inside the container
```

Run the reproduction script inside the container:

```bash
docker compose -f docker/compose.dev.cpu.yml exec factors bash -lc "./docker/entrypoint.sh reproduce"
```

Run a single experiment interactively:

```bash
docker compose -f docker/compose.dev.cpu.yml exec factors bash -lc "python scripts/run_experiment.py --config configs/datasets/concrete.yaml --seed 0 --out experiments/dev/concrete"
```

## Build and start the GPU development container

> Ensure the host supports GPU containers and has the NVIDIA toolkit installed.

```bash
docker compose -f docker/compose.dev.gpu.yml build
docker compose -f docker/compose.dev.gpu.yml up -d
```

Open an interactive shell with access to GPUs:

```bash
docker compose -f docker/compose.dev.gpu.yml exec factors bash
# check GPUs are visible inside container
nvidia-smi
```

Run the reproduce or a GPU experiment like:

```bash
docker compose -f docker/compose.dev.gpu.yml exec factors bash -lc "python scripts/run_experiment.py --config configs/datasets/fmnist.yaml --device cuda --seed 0 --out experiments/dev/fmnist"
```

## Notes and troubleshooting

* **Volume caching**: On macOS and Windows volume performance may be slow. Using the `:cached` option can help, but heavy IO on mounted volumes may still be slow. Consider running experiments inside the container with data copied to a container-local directory for heavy workloads.
* **Python version**: The Compose files pass build args to choose default Python versions in the Dockerfiles. To change the Python version, either edit the compose file build args or run `docker compose build --build-arg PYTHON_VERSION=3.10`.
* **GPU not visible**: If `nvidia-smi` is not available inside the GPU container:

  * Confirm the host has NVIDIA drivers.
  * Confirm the NVIDIA Container Toolkit is installed and Docker service restarted.
  * Use `docker run --gpus all --rm nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi` on the host to debug.
* **File permissions**: Files created by container processes may be owned by `root`. Use `chown` on the host or run container commands with `--user $(id -u):$(id -g)` if you prefer host-compatible ownership during development.
* **Security**: These Compose files mount the full repository into the container for convenience. Do not use them in untrusted environments without auditing.

## Quick stop and cleanup

```bash
docker compose -f docker/compose.dev.cpu.yml down --volumes --remove-orphans
docker compose -f docker/compose.dev.gpu.yml down --volumes --remove-orphans
```

## Customization tips

* If you want the compose service to run the reproduction automatically on start, replace the `command` with:

  ```yaml
  command: ["bash", "-lc", "./docker/entrypoint.sh reproduce"]
  ```

  Be cautious: long-running experiments will block the container for development use.
* To expose additional ports (for web UIs) add entries under `ports`.
* To limit GPUs for a service (e.g., use only GPU 0), set `NVIDIA_VISIBLE_DEVICES` environment or change `device_requests.count` to `1` and set appropriate device selection logic in your runtime.

---

If you want, I can:

* Add an example `docker-compose.override.yml` that runs the reproduction automatically when `docker compose up` is executed,
* Or produce a short troubleshooting checklist for common Docker build failures tailored to your CI environment. Which would you like next?
