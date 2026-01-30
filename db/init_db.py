from __future__ import annotations
from sqlalchemy import select
from db.session import engine, SessionLocal
from db.models import Base, Setting
from db.migrate import migrate_sqlite
from db.session import get_db_path

DEFAULT_SETTINGS = {
    "update_interval_min": "30",
    "pnl_alert_threshold_try": "-5000",
    "cost_method": "WAVG",
    "fx_primary": "exchangerate_host",
    "fx_fallback": "frankfurter",
    "metals_primary": "kapalicarsi_apiluna",
    "metals_fallback": "manual",
    "copper_provider": "kitco",
}

def init_db(seed: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    migrate_sqlite(get_db_path())
    with SessionLocal() as db:
        for k, v in DEFAULT_SETTINGS.items():
            if db.get(Setting, k) is None:
                db.add(Setting(key=k, value=v))
        db.commit()
