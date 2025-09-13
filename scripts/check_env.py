#!/usr/bin/env python3
# scripts/check_env.py
# Simple environment checker: verifies python, numpy, pandas, torch (if present), and GPU availability.
# Usage:
#   python scripts/check_env.py

from __future__ import annotations

import subprocess
import sys
from importlib import util

def check_module(name: str):
    spec = util.find_spec(name)
    return spec is not None

def run_cmd(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
        return out.strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.output.strip()}"

def main():
    print("Environment check for FACTORS")
    print("-----------------------------")
    print(f"Python: {sys.executable} ({sys.version.splitlines()[0]})")
    for m in ["numpy", "pandas", "yaml"]:
        print(f"{m}: {'installed' if check_module(m) else 'MISSING'}")
    # torch check
    if check_module("torch"):
        import torch
        print(f"torch: {torch.__version__}")
        print(f"  cuda available: {torch.cuda.is_available()}")
        try:
            print("  nvidia-smi:", run_cmd("nvidia-smi -L || true"))
        except Exception:
            pass
    else:
        print("torch: MISSING")

    # docker availability
    print("docker:", "installed" if run_cmd("docker --version") else "not found")
    print("nvidia-docker (nvidia-container-toolkit):", "check nvidia-smi output above for GPU visibility")
    print("Done.")

if __name__ == "__main__":
    main()
