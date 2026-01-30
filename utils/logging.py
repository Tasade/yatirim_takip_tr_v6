from __future__ import annotations
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(name: str, log_dir: str = "logs", level: int = logging.INFO) -> logging.Logger:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    fh = RotatingFileHandler(os.path.join(log_dir, f"{name}.log"), maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt); fh.setLevel(level)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt); ch.setLevel(level)

    logger.addHandler(fh); logger.addHandler(ch)
    return logger
