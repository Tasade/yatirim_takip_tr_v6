from __future__ import annotations
import os, time, json
from decimal import Decimal
from pathlib import Path
from typing import Dict

from apscheduler.schedulers.background import BackgroundScheduler
from filelock import FileLock, Timeout
from sqlalchemy import select

from db.init_db import init_db
from db.session import SessionLocal, get_db_path
from db.models import Price, Setting, Snapshot
from providers.router import ProviderRouter
from utils.logging import setup_logging
from utils.time import iso_now_tr
from utils.backup import daily_sqlite_backup

logger = setup_logging("service", os.getenv("LOG_DIR","logs"))

ASSETS = ["XAU_G","XAG_G","XCU_G","USDTRY","EURTRY"]

def get_settings(db) -> Dict[str,str]:
    rows = db.execute(select(Setting)).scalars().all()
    return {r.key:r.value for r in rows}

def insert_price(db, ts: str, asset: str, price: Decimal, source: str, is_stale: int, error_msg: str | None):
    db.add(Price(ts=ts, asset=asset, price=str(price), currency="TRY", source=source, is_stale=is_stale, error_msg=error_msg))

def insert_snapshot(db, ts: str, prices: Dict[str,Decimal]):
    db.add(Snapshot(ts=ts, total_value_try="0", breakdown_json=json.dumps({k:str(v) for k,v in prices.items()}, ensure_ascii=False)))

def fetch_and_store():
    ts = iso_now_tr()
    with SessionLocal() as db:
        s = get_settings(db)
        router = ProviderRouter(
            fx_primary=os.getenv("FX_PRIMARY", s.get("fx_primary","exchangerate_host")),
            fx_fallback=os.getenv("FX_FALLBACK", s.get("fx_fallback","frankfurter")),
            metals_primary=os.getenv("METALS_PRIMARY", s.get("metals_primary","metals_dev")),
            metals_fallback=os.getenv("METALS_FALLBACK", s.get("metals_fallback","manual")),
            copper_provider=os.getenv("COPPER_PROVIDER", s.get("copper_provider","kitco")),
            timeout_s=10,
        )

        manual_prices = {}  # service doesn't input manual; UI can.
        max_tries = 3
        last_err = None
        for i in range(max_tries):
            try:
                prices, sources = router.get_all_prices_try(ASSETS, manual_prices=manual_prices)
                for a in ASSETS:
                    if a in prices:
                        insert_price(db, ts, a, prices[a], sources.get(a,"unknown"), 0, None)
                    else:
                        last = db.execute(select(Price).where(Price.asset==a).order_by(Price.id.desc())).scalars().first()
                        if last:
                            insert_price(db, ts, a, Decimal(last.price), last.source, 1, "provider_unavailable")
                        else:
                            insert_price(db, ts, a, Decimal("0"), "none", 1, "no_data_yet")
                insert_snapshot(db, ts, prices)
                set_kv(db, 'last_success_ts', ts)
                set_kv(db, 'last_error', '')
                db.commit()
                logger.info("Prices updated OK.")
                daily_sqlite_backup(get_db_path(), os.getenv("BACKUP_DIR","backups"))
                return
            except Exception as e:
                last_err = str(e)
                sleep_s = 2 ** i
                logger.warning(f"Fetch {i+1}/{max_tries} failed: {e}; sleep {sleep_s}s")
                time.sleep(sleep_s)

        # total failure -> mark stale from last known
        for a in ASSETS:
            last = db.execute(select(Price).where(Price.asset==a).order_by(Price.id.desc())).scalars().first()
            if last:
                insert_price(db, ts, a, Decimal(last.price), last.source, 1, last_err)
            else:
                insert_price(db, ts, a, Decimal("0"), "none", 1, last_err)
        set_kv(db, 'last_error', last_error or '')
        db.commit()
        logger.error(f"All providers failed; stale written: {last_err}")

def main():
    init_db(seed=False)
    interval_min = 30
    with SessionLocal() as db:
        s = db.get(Setting, "update_interval_min")
        if s:
            try: interval_min = int(s.value)
            except Exception: interval_min = 30

    lock = FileLock(str(Path("service.lock")))
    try:
        with lock.acquire(timeout=1):
            logger.info("Service started (lock acquired).")
            sched = BackgroundScheduler(daemon=False)
            sched.add_job(fetch_and_store, "interval", minutes=interval_min)
            sched.start()
            fetch_and_store()
            while True:
                time.sleep(2)
    except Timeout:
        logger.error("Service already running (lock busy).")

if __name__ == "__main__":
    main()
