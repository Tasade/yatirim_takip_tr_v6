from __future__ import annotations
import shutil
from datetime import datetime
from pathlib import Path

def daily_sqlite_backup(db_path: str, backup_dir: str) -> str:
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d")
    dst = Path(backup_dir) / f"portfolio_{ts}.sqlite"
    if not dst.exists():
        shutil.copy2(db_path, dst)
    return str(dst)
