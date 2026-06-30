"""Shared utilities: logging setup, safe type coercions, and helpers."""

import logging
import time
from pathlib import Path
from typing import Any

from config import LOGS_DIR


def get_logger(name: str) -> logging.Logger:
    """Return a logger that writes to both stdout and a rotating log file."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)

    fh = logging.FileHandler(LOGS_DIR / "pipeline.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger


def safe_float(value: Any, default: float | None = None) -> float | None:
    """Convert value to float, returning default on failure."""
    if value is None or value == "":
        return default
    try:
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int | None = None) -> int | None:
    """Convert value to int, returning default on failure."""
    f = safe_float(value)
    if f is None:
        return default
    return int(f)


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def innings_to_float(ip_str: Any) -> float | None:
    """Convert '6.2' (6 innings, 2 outs) → 6.667 actual innings."""
    val = safe_float(ip_str)
    if val is None:
        return None
    whole = int(val)
    outs = round((val - whole) * 10)
    return round(whole + outs / 3, 4)


def rate_limited_call(func, *args, pause: float = 0.3, **kwargs):
    """Call func(*args, **kwargs) then sleep pause seconds."""
    result = func(*args, **kwargs)
    time.sleep(pause)
    return result
