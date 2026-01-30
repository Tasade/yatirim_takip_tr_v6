from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_PATH = os.getenv("DB_PATH", "data/portfolio.sqlite")

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    future=True,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

# Apply SQLite pragmas for concurrency and durability
with engine.connect() as conn:
    conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
    conn.exec_driver_sql("PRAGMA synchronous=NORMAL;")
    conn.exec_driver_sql("PRAGMA busy_timeout=5000;")
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_db_path() -> str:
    return DB_PATH
