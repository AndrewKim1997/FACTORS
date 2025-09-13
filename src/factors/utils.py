# src/factors/utils.py
# Small utility helpers: deterministic seed setting, timers, simple checkpoint directory helpers.
# These functions are frequently used across experiment scripts.

from __future__ import annotations

import os
import time
import random
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import numpy as np
except Exception:  # pragma: no cover - numpy expected in scientific envs
    np = None

try:
    import torch
except Exception:
    torch = None


def set_seed(seed: Optional[int]) -> None:
    """
    Set random seed for python, numpy, and torch (if available) for reproducibility.
    This function sets common RNGs but does not guarantee bitwise reproducibility across systems.
    """
    if seed is None:
        return
    random.seed(seed)
    if np is not None:
        np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    if torch is not None:
        torch.manual_seed(seed)
        try:
            torch.cuda.manual_seed_all(seed)
        except Exception:
            pass


def enable_deterministic_torch() -> None:
    """
    Attempt to enable deterministic behavior in PyTorch. Use with caution as it may
    reduce performance or not be supported for some ops.
    """
    if torch is None:
        return
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        # Older torch versions
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


@contextmanager
def Timer(name: Optional[str] = None, warmup: bool = False):
    """
    Context manager to measure elapsed wall-clock time.

    Usage:
        with Timer("train"):
            do_work()
    """
    start = time.time()
    try:
        yield
    finally:
        end = time.time()
        elapsed = end - start
        if name:
            print(f"[Timer] {name} finished in {elapsed:.3f} s")
        else:
            print(f"[Timer] finished in {elapsed:.3f} s")


def ensure_dir(path: str | Path) -> Path:
    """Ensure directory exists and return Path object. Duplicate helper for convenience."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class CheckpointManager:
    """
    Simple checkpoint manager that saves items into a run directory with monotonic filenames.
    Example:
        mgr = CheckpointManager("experiments/run1/checkpoints")
        mgr.save({"model_state": state_dict}, "step_100")
    """
    run_dir: str | Path

    def __post_init__(self):
        self.dir = ensure_dir(self.run_dir)

    def save(self, obj: object, name: str) -> Path:
        """
        Save Python object using pickle or torch.save (if available) under <run_dir>/<name>.pt
        Returns the path to the saved file.
        """
        from .io import save_checkpoint  # local import to avoid cycle at module import time

        filename = f"{name}.pt"
        path = self.dir / filename
        save_checkpoint(obj, path)
        return path

    def latest(self) -> Optional[Path]:
        """Return latest checkpoint file or None if none exist."""
        files = sorted(self.dir.glob("*.pt"), key=lambda p: p.stat().st_mtime)
        return files[-1] if files else None
