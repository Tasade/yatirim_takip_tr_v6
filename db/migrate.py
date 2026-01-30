from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from utils.logging import setup_logging

logger = setup_logging("migrate", os.getenv("LOG_DIR", "logs"))

def _column_exists(cur: sqlite3.Cursor, table: str, col: str) -> bool:
    cur.execute(f"PRAGMA table_info({table});")
    cols = [r[1] for r in cur.fetchall()]
    return col in cols

def migrate_sqlite(db_path: str) -> None:
    """Lightweight SQLite migrations (safe to run every startup)."""
    Path(os.path.dirname(db_path) or ".").mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()

        # prices: add price_buy/price_sell if missing
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prices';")
        if cur.fetchone():
            if not _column_exists(cur, "prices", "price_buy"):
                cur.execute("ALTER TABLE prices ADD COLUMN price_buy TEXT;")
                logger.info("Migrated: prices.price_buy added")
            if not _column_exists(cur, "prices", "price_sell"):
                cur.execute("ALTER TABLE prices ADD COLUMN price_sell TEXT;")
                logger.info("Migrated: prices.price_sell added")

        con.commit()
    finally:
        con.close()
