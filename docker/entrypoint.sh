#!/usr/bin/env bash
# entrypoint.sh for FACTORS Docker images
# - This script provides a small, predictable interface for running experiments inside a container.
# - It either runs the reproduce script, forwards to the run_experiment entrypoint or prints help.
# - All arguments are passed through to the underlying Python script when applicable.
# Usage examples:
#   docker run --rm -v "$(pwd)":/workspace -w /workspace factors:cpu reproduce
#   docker run --rm -v "$(pwd)":/workspace -w /workspace factors:cpu run --config configs/datasets/concrete.yaml --seed 0
#   docker run --rm -v "$(pwd)":/workspace -w /workspace factors:cpu help

set -euo pipefail

# Default paths (relative to /workspace inside container)
REPRODUCE_SCRIPT="./scripts/reproduce_all.sh"
RUN_SCRIPT="./scripts/run_experiment.py"

show_help() {
  cat <<'EOF'
FACTORS container entrypoint

Usage:
  entrypoint.sh help
    - show this help message

  entrypoint.sh reproduce
    - run the full reproduction script (scripts/reproduce_all.sh). This is the recommended
      command for reviewers who want to reproduce paper artifacts within the container.

  entrypoint.sh run --config <config.yaml> [--seed N] [--out <path>] [--device cpu|cuda] [other flags]
    - run a single experiment using scripts/run_experiment.py. All flags after 'run' are forwarded.

  entrypoint.sh shell
    - start an interactive bash shell (useful for debugging inside the container)

Examples:
  # run the canonical reproduction
  entrypoint.sh reproduce

  # run a single config
  entrypoint.sh run --config configs/datasets/concrete.yaml --seed 42 --out experiments/main/concrete_seed42

EOF
}

# No arguments -> help
if [ $# -eq 0 ]; then
  show_help
  exit 0
fi

COMMAND="$1"
shift || true

case "${COMMAND}" in
  help|-h|--help)
    show_help
    ;;

  reproduce)
    # Make reproduce script executable if needed and run it
    if [ -f "${REPRODUCE_SCRIPT}" ]; then
      chmod +x "${REPRODUCE_SCRIPT}" || true
      echo "[entrypoint] running reproduction: ${REPRODUCE_SCRIPT}"
      exec bash -lc "${REPRODUCE_SCRIPT}"
    else
      echo "[entrypoint] reproduce script not found at ${REPRODUCE_SCRIPT}"
      exit 2
    fi
    ;;

  run)
    # Forward to Python run script with all remaining args
    if [ -f "${RUN_SCRIPT}" ]; then
      echo "[entrypoint] running single experiment: python ${RUN_SCRIPT} $*"
      exec python ${RUN_SCRIPT} "$@"
    else
      echo "[entrypoint] run script not found at ${RUN_SCRIPT}"
      exit 2
    fi
    ;;

  shell)
    exec /bin/bash
    ;;

  *)
    # If unknown command, try to run it as a direct shell command to allow flexibility
    echo "[entrypoint] executing arbitrary command: ${COMMAND} $*"
    exec ${COMMAND} "$@"
    ;;
esac
