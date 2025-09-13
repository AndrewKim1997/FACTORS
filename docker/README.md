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
