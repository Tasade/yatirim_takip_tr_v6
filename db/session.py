# db/session.py
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

def get_db_path() -> str:
    # Yerel için öneri: proje içinde data/ klasörü
    # Cloud için öneri: /tmp (kalıcı değil ama çalışır)
    default = "data/yatirim.db"
    p = os.getenv("DB_PATH", default)

    # Cloud ortamlarında /mount/src bazen read-only / garip olabiliyor.
    # Eğer yazılamazsa otomatik /tmp'ye düşmek istersen:
    # p = os.getenv("DB_PATH", "/tmp/yatirim.db")

    return p

DB_PATH = get_db_path()
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    future=True,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

# PRAGMA’ları import-time connect ile değil, her bağlantıda uygula
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
