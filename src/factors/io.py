# src/factors/io.py
# Input/output helpers for saving metrics, figures, checkpoints, and run metadata.
# The functions aim to be robust and dependency-light. They use pathlib and the standard library.

from __future__ import annotations

import json
import os
import pickle
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Union
import datetime

try:
    import torch
except Exception:  # torch is optional
    torch = None

from matplotlib.figure import Figure


def ensure_dir(path: Union[str, Path]) -> Path:
    """Ensure a directory exists and return a pathlib.Path object."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def atomic_write_json(obj: Any, path: Union[str, Path], indent: int = 2) -> None:
    """
    Write a JSON file atomically by writing to a temporary file and moving it into place.
    """
    p = Path(path)
    ensure_dir(p.parent)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False)
    tmp.replace(p)


def save_metrics_json(metrics: Dict[str, Any], out_path: Union[str, Path]) -> None:
    """
    Save metrics dict as JSON. This function ensures the parent directory exists.
    """
    p = Path(out_path)
    ensure_dir(p.parent)
    atomic_write_json(metrics, p)


def save_figure(fig: Figure, out_path: Union[str, Path], dpi: int = 300, bbox_inches: str = "tight") -> None:
    """
    Save a matplotlib Figure to file. Accepts common image formats based on filename suffix.
    """
    p = Path(out_path)
    ensure_dir(p.parent)
    fig.savefig(str(p), dpi=dpi, bbox_inches=bbox_inches)


def save_checkpoint(obj: Any, out_path: Union[str, Path]) -> None:
    """
    Save a model checkpoint. If torch is available and the object looks like a torch state_dict,
    prefer torch.save for compatibility; otherwise use pickle.
    """
    p = Path(out_path)
    ensure_dir(p.parent)
    # Prefer torch.save if torch is present and object is dict-like
    if torch is not None:
        try:
            torch.save(obj, str(p))
            return
        except Exception:
            # fallback to pickle
            pass
    # Pickle fallback
    with p.open("wb") as f:
        pickle.dump(obj, f)


def load_checkpoint(path: Union[str, Path]) -> Any:
    """
    Load a checkpoint saved by save_checkpoint. Try torch.load first if available, otherwise pickle.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    if torch is not None:
        try:
            return torch.load(str(p), map_location="cpu")
        except Exception:
            # fallback to pickle
            pass
    with p.open("rb") as f:
        return pickle.load(f)


def git_commit_hash() -> str:
    """
    Return the current git commit hash if available, otherwise return 'no-git'.
    This function calls git via subprocess; it will not fail the program on error.
    """
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return "no-git"


def write_run_metadata(
    out_dir: Union[str, Path],
    config: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Write run metadata including commit hash, timestamp, and optional config and extra info.
    The metadata file is saved as out_dir/run_metadata.json.
    """
    od = ensure_dir(out_dir)
    metadata = {
        "commit": git_commit_hash(),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "platform": {
            "os": os.name,
            "python_version": f"{os.sys.version}",
        },
    }
    if config is not None:
        metadata["config"] = config
    if extra is not None:
        metadata["extra"] = extra
    atomic_write_json(metadata, od / "run_metadata.json")
