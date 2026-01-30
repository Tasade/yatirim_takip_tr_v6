from __future__ import annotations
import os
from decimal import Decimal
from typing import Dict

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import select, text, func

from db.init_db import init_db
from db.session import SessionLocal, get_db_path
from db.models import Transaction, Price, Setting
from utils.decimal import D, q2, q4
from utils.logging import setup_logging
from utils.time import iso_now_tr


# ✅ Warmup için router
from providers.router import ProviderRouter

logger = setup_logging("app", os.getenv("LOG_DIR", "logs"))

ASSETS_META = {
    "XAU_G": {"name": "Gram Altın", "unit": "gr"},
    "XAG_G": {"name": "Gram Gümüş", "unit": "gr"},
    "XCU_G": {"name": "Bakır", "unit": "gr"},
    "USDTRY": {"name": "USD/TRY", "unit": "USD"},
    "EURTRY": {"name": "EUR/TRY", "unit": "EUR"},
}
ASSETS = list(ASSETS_META.keys())


def asset_label(a: str) -> str:
    return ASSETS_META.get(a, {"name": a})["name"]


def get_settings(db) -> Dict[str, str]:
    rows = db.execute(select(Setting)).scalars().all()
    return {r.key: r.value for r in rows}


def set_setting(db, key: str, value: str):
    s = db.get(Setting, key)
    if s is None:
        db.add(Setting(key=key, value=value))
    else:
        s.value = value


def latest_prices(db) -> pd.DataFrame:
    q = text(
        """
    SELECT p1.*
    FROM prices p1
    JOIN (
      SELECT asset, MAX(id) AS max_id
      FROM prices
      GROUP BY asset
    ) p2
    ON p1.asset = p2.asset AND p1.id = p2.max_id
    """
    )
    return pd.read_sql(q, db.bind)


def insert_manual_price(db, asset: str, price: Decimal, source: str = "manual"):
    db.add(
        Price(
            ts=iso_now_tr(),
            asset=asset,
            price=str(price),
            currency="TRY",
            source=source,
            is_stale=0,
            error_msg=None,
        )
    )


def insert_tx(asset: str, side: str, qty: Decimal, unit_price: Decimal, fee: Decimal, note: str | None):
    """Transaction insert (kalıcı)."""
    with SessionLocal() as db:
        db.add(
            Transaction(
                ts=iso_now_tr(),
                asset=asset,
                side=side,
                qty=str(qty),
                unit_price=str(unit_price),
                fee=str(fee),
                currency="TRY",
                note=note,
            )
        )
        db.commit()


def load_transactions_df(db) -> pd.DataFrame:
    tx = db.execute(select(Transaction).order_by(Transaction.id.asc())).scalars().all()
    if not tx:
        return pd.DataFrame(columns=["id", "ts", "asset", "side", "qty", "unit_price", "fee", "currency", "note"])
    return pd.DataFrame(
        [
            {
                "id": t.id,
                "ts": t.ts,
                "asset": t.asset,
                "side": t.side,
                "qty": t.qty,
                "unit_price": t.unit_price,
                "fee": t.fee,
                "currency": t.currency,
                "note": t.note,
            }
            for t in tx
        ]
    )


def compute_inventory_and_pnl(tx: pd.DataFrame, price_map: Dict[str, Decimal]) -> pd.DataFrame:
    state: Dict[str, Dict[str, Decimal]] = {}
    rows = []
    for _, r in tx.iterrows():
        asset = r["asset"]
        side = r["side"]
        qty = D(r["qty"])
        unit_price = D(r["unit_price"])
        fee = D(r["fee"])

        st_ = state.get(asset, {"qty": Decimal("0"), "avg": Decimal("0"), "realized": Decimal("0")})

        if side == "BUY":
            total_cost = qty * unit_price + fee
            new_qty = st_["qty"] + qty
            if new_qty > 0:
                st_["avg"] = (st_["avg"] * st_["qty"] + total_cost) / new_qty
            st_["qty"] = new_qty
        else:
            if qty > st_["qty"]:
                raise ValueError(f"{asset_label(asset)} stok yetersiz: elde {st_['qty']} var, satmak istedin {qty}")
            proceeds = qty * unit_price - fee
            cost = qty * st_["avg"]
            st_["realized"] += (proceeds - cost)
            st_["qty"] -= qty
            if st_["qty"] == 0:
                st_["avg"] = Decimal("0")

        state[asset] = st_

    for asset, st_ in state.items():
        qty = st_["qty"]
        avg = st_["avg"]
        cur = price_map.get(asset)
        value = qty * cur if cur is not None else Decimal("0")
        cost = qty * avg
        unreal = value - cost
        unreal_pct = (unreal / cost * Decimal("100")) if cost > 0 else None
        rows.append(
            {
                "asset": asset,
                "qty": qty,
                "avg_cost_try": avg,
                "last_price_try": cur,
                "value_try": value,
                "unrealized_try": unreal,
                "unrealized_pct": unreal_pct,
                "realized_try": st_["realized"],
            }
        )

    for a in ASSETS_META.keys():
        if not any(x["asset"] == a for x in rows):
            rows.append(
                {
                    "asset": a,
                    "qty": Decimal("0"),
                    "avg_cost_try": Decimal("0"),
                    "last_price_try": price_map.get(a),
                    "value_try": Decimal("0"),
                    "unrealized_try": Decimal("0"),
                    "unrealized_pct": None,
                    "realized_try": Decimal("0"),
                }
            )
    return pd.DataFrame(rows)


def warmup_prices_if_missing():
    """
    İlk açılışta:
    - DB'de hiç fiyat yoksa veya bazı varlıkların fiyatı yoksa
    - 1 kez fiyat çekip prices tablosuna yazar.
    """
    try:
        with SessionLocal() as db:
            cnt = db.execute(select(func.count(Price.id))).scalar() or 0
            if cnt == 0:
                missing = ASSETS[:]
            else:
                existing = set(pd.read_sql(text("SELECT DISTINCT asset FROM prices"), db.bind)["asset"].tolist())
                missing = [a for a in ASSETS if a not in existing]

        if not missing:
            return

        with SessionLocal() as db:
            settings = get_settings(db)

        router = ProviderRouter(
            fx_primary=os.getenv("FX_PRIMARY", settings.get("fx_primary", "exchangerate_host")),
            fx_fallback=os.getenv("FX_FALLBACK", settings.get("fx_fallback", "frankfurter")),
            metals_primary=os.getenv("METALS_PRIMARY", settings.get("metals_primary", "kapalicarsi_apiluna")),
            metals_fallback=os.getenv("METALS_FALLBACK", settings.get("metals_fallback", "metals_dev")),
            copper_provider=os.getenv("COPPER_PROVIDER", settings.get("copper_provider", "kitco")),
            timeout_s=10,
        )

        ts = iso_now_tr()
        quotes, sources = router.get_all_quotes_try(missing, manual_prices=None)

        with SessionLocal() as db:
            wrote_any = False
            for a in missing:
                if a in quotes:
                    q = quotes[a]
                    mid = q.get("mid")
                    if mid is None:
                        continue
                    db.add(
                        Price(
                            ts=ts,
                            asset=a,
                            price=str(mid),
                            currency="TRY",
                            source=sources.get(a, "warmup"),
                            is_stale=0,
                            error_msg=None,
                        )
                    )
                    wrote_any = True
            if wrote_any:
                db.commit()

    except Exception as e:
        logger.warning(f"Warmup price fetch failed (ignored): {e}")


# ---------------- UI ----------------
st.set_page_config(page_title="Yatırım Takip (TR)", layout="wide")
init_db(seed=False)
def warmup_prices_if_missing():
    try:
        with SessionLocal() as db:
            cnt = db.execute(select(func.count(Price.id))).scalar() or 0
            if cnt == 0:
                missing = list(ASSETS_META.keys())
            else:
                existing = set(pd.read_sql(text("SELECT DISTINCT asset FROM prices"), db.bind)["asset"].tolist())
                missing = [a for a in ASSETS_META.keys() if a not in existing]

        if not missing:
            return

        router = ProviderRouter(timeout_s=10)
        ts = iso_now_tr()
        quotes, sources = router.get_all_quotes_try(missing, manual_prices=None)

        with SessionLocal() as db:
            wrote = False
            for a in missing:
                if a in quotes:
                    mid = quotes[a]["mid"]
                    db.add(Price(ts=ts, asset=a, price=str(mid), currency="TRY",
                                 source=sources.get(a, "warmup"), is_stale=0, error_msg=None))
                    wrote = True
            if wrote:
                db.commit()
    except Exception as e:
        logger.warning(f"Warmup failed (ignored): {e}")

with st.spinner("İlk açılış fiyatları çekiliyor..."):
    warmup_prices_if_missing()

# ✅ İlk açılışta fiyatlar boşsa doldur
with st.spinner("İlk açılış fiyatları çekiliyor..."):
    warmup_prices_if_missing()

with SessionLocal() as db:
    settings = get_settings(db)
    prices_df = latest_prices(db)
    tx_df = load_transactions_df(db)

price_map: Dict[str, Decimal] = {}
source_map: Dict[str, str] = {}
stale_assets = []
last_ts = None

if not prices_df.empty:
    for _, r in prices_df.iterrows():
        price_map[r["asset"]] = D(r["price"])
        source_map[r["asset"]] = r.get("source", "")
        if int(r.get("is_stale", 0)) == 1:
            stale_assets.append(r["asset"])
        last_ts = r.get("ts", last_ts)


def fmt(v: Decimal | None, d=2) -> str:
    if v is None:
        return "—"
    q = q2(v) if d == 2 else q4(v)
    s = f"{q}"
    if "." in s:
        left, right = s.split(".")
    else:
        left, right = s, ""
    left = "{:,}".format(int(left)).replace(",", ".")
    return left + ("," + right if right else "")


st.markdown(
    """
<style>
.ticker-wrap {background:#0b0f14;border-radius:14px;padding:18px 16px;margin:8px 0 14px 0;border:1px solid rgba(255,255,255,0.08);}
.ticker-title {color:#c9d1d9;font-size:13px;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:10px;}
.ticker-grid {display:flex;flex-wrap:wrap;gap:10px;}
.ticker-card {flex:1 1 180px;background:#111823;border-radius:12px;padding:12px 12px;border:1px solid rgba(255,255,255,0.06);}
.ticker-label {color:#9aa4af;font-size:12px;margin-bottom:6px;}
.ticker-value {color:#f0f6fc;font-size:24px;font-weight:700;}
.ticker-sub {color:#9aa4af;font-size:11px;margin-top:6px;}
</style>
""",
    unsafe_allow_html=True,
)

cards = [
    ("ALTIN", "XAU_G", 2, "TL / gr"),
    ("GÜMÜŞ", "XAG_G", 2, "TL / gr"),
    ("BAKIR", "XCU_G", 4, "TL / gr"),
    ("USD/TRY", "USDTRY", 4, "TL / 1 USD"),
    ("EUR/TRY", "EURTRY", 4, "TL / 1 EUR"),
]

card_html = ""
for label, code, decs, unit in cards:
    v = price_map.get(code)
    src = source_map.get(code, "—")
    stale = " • STALE" if code in stale_assets else ""
    card_html += f'<div class="ticker-card"><div class="ticker-label">{label}</div><div class="ticker-value">{fmt(v,decs)}</div><div class="ticker-sub">{unit} • {src}{stale}</div></div>'

st.markdown(
    f'<div class="ticker-wrap"><div class="ticker-title">KUYUMCU TABLOSU • Son: {last_ts or "—"} • DB: {get_db_path()}</div><div class="ticker-grid">{card_html}</div></div>',
    unsafe_allow_html=True,
)

colA, colB = st.columns([1, 4])
with colA:
    if st.button("🔄 Şimdi Güncelle", key="btn_refresh_prices"):
        with st.spinner("Güncelleniyor..."):
            warmup_prices_if_missing()
        st.rerun()

if stale_assets:
    st.warning("⚠️ Stale fiyatlar: " + ", ".join(stale_assets))

tabs = st.tabs(["Özet", "İşlem Ekle", "İşlem Geçmişi", "Envanter", "Analiz", "Ayarlar", "Servis/Log", "Manuel Fiyat"])

# Inventory + PnL
inventory_df = pd.DataFrame()
pnl_alert = None
total_value = realized = unreal = total_pnl = None

try:
    inventory_df = compute_inventory_and_pnl(tx_df, price_map)
    total_value = sum([D(x) for x in inventory_df["value_try"]])
    realized = sum([D(x) for x in inventory_df["realized_try"]])
    unreal = sum([D(x) for x in inventory_df["unrealized_try"]])
    total_pnl = realized + unreal
    thr = D(settings.get("pnl_alert_threshold_try", "-5000"))
    if total_pnl <= thr:
        pnl_alert = (total_pnl, thr)
except Exception as e:
    st.error(f"Envanter hesaplama hatası: {e}")
    logger.exception(e)

with tabs[0]:
    st.subheader("Özet")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portföy Değeri (TRY)", fmt(total_value, 2) if total_value is not None else "—")
    c2.metric("Realized (TRY)", fmt(realized, 2) if realized is not None else "—")
    c3.metric("Unrealized (TRY)", fmt(unreal, 2) if unreal is not None else "—")
    c4.metric("Toplam PnL (TRY)", fmt(total_pnl, 2) if total_pnl is not None else "—")

    if pnl_alert:
        tp, thr = pnl_alert
        try:
            @st.dialog("🚨 PnL Uyarısı")
            def _dlg():
                st.write(f"Toplam PnL: **{fmt(tp,2)} TL**")
                st.write(f"Eşik: **{fmt(thr,2)} TL**")
                st.warning("Bu alarm otomatik. Plan + makas/işçilik kontrol et.")
                st.button("Tamam", type="primary", key="btn_pnl_ok")
            _dlg()
        except Exception:
            st.error(f"🚨 PnL UYARISI: {fmt(tp,2)} <= {fmt(thr,2)}")

    if not inventory_df.empty:
        dist = inventory_df.copy()
        dist["asset_name"] = dist["asset"].apply(asset_label)
        dist["value_try_num"] = dist["value_try"].apply(lambda x: float(D(x)))
        chart = alt.Chart(dist).mark_arc().encode(
            theta="value_try_num:Q",
            color="asset_name:N",
            tooltip=["asset_name:N", "value_try_num:Q"],
        )
        st.altair_chart(chart, use_container_width=True)

with tabs[1]:
    st.subheader("İşlem Ekle")

    auto_price = st.toggle(
        "Otomatik fiyat kullan (mevcut son fiyatı kullanır)",
        value=True,
        key="toggle_auto_price",
    )

    asset = st.selectbox(
        "Varlık",
        list(ASSETS_META.keys()),
        format_func=asset_label,
        key="select_asset",
    )

    side = st.selectbox(
        "İşlem",
        ["BUY", "SELL"],
        format_func=lambda x: "ALIŞ" if x == "BUY" else "SATIŞ",
        key="select_side",
    )

    qty = st.text_input(
        "Miktar (metaller: gram, USD/EUR: adet)",
        value="0",
        key="input_qty",
    )

    fee = st.text_input(
        "Fee / Komisyon (TRY)",
        value="0",
        key="input_fee",
    )

    note = st.text_input(
        "Not (opsiyonel)",
        value="",
        key="input_note",
    )

    unit_price_manual = st.text_input(
        "Birim Fiyat (TRY) — (auto kapalıysa zorunlu)",
        value="0",
        disabled=auto_price,
        key="input_unit_price",
    )

    # ✅ İşlem kaydet butonu doğru sekmede
    if st.button("✅ İşlemi Kaydet", key="btn_tx_save"):
        try:
            qty_d = D(qty)
            fee_d = D(fee)

            if qty_d <= 0 or fee_d < 0:
                raise ValueError("Miktar pozitif olmalı; fee negatif olamaz.")

            if auto_price:
                unit_price_d = price_map.get(asset)
                if unit_price_d is None or unit_price_d <= 0:
                    raise ValueError("Bu varlık için DB'de fiyat yok. Önce fiyat güncelle.")
            else:
                unit_price_d = D(unit_price_manual)
                if unit_price_d <= 0:
                    raise ValueError("Birim fiyat pozitif olmalı.")

            # stok kontrolü (simulate)
            sim = tx_df.copy()
            new_row = pd.DataFrame([{
                "asset": asset, "side": side,
                "qty": str(qty_d), "unit_price": str(unit_price_d), "fee": str(fee_d)
            }])
            sim2 = pd.concat([sim, new_row], ignore_index=True)
            _ = compute_inventory_and_pnl(sim2, price_map)  # yetersiz stok varsa patlar

            insert_tx(asset, side, qty_d, unit_price_d, fee_d, note or None)
            st.success("İşlem kaydedildi.")
            st.rerun()

        except Exception as e:
            st.error(f"Kayıt hatası: {e}")

with tabs[2]:
    st.subheader("İşlem Geçmişi")
    if tx_df.empty:
        st.info("İşlem yok.")
    else:
        filt = st.selectbox(
            "Varlık filtresi",
            ["ALL"] + list(ASSETS_META.keys()),
            format_func=lambda x: "Hepsi" if x == "ALL" else asset_label(x),
            key="tx_filter_asset",
        )
        df = tx_df.copy()
        if filt != "ALL":
            df = df[df["asset"] == filt]
        df["asset_name"] = df["asset"].apply(asset_label)
        st.dataframe(df[["id", "ts", "asset_name", "side", "qty", "unit_price", "fee", "note"]], use_container_width=True)
        st.download_button(
            "CSV Export",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="transactions_export.csv",
            key="dl_tx_csv",
        )

with tabs[3]:
    st.subheader("Envanter")
    if inventory_df.empty:
        st.info("Envanter yok.")
    else:
        inv = inventory_df.copy()
        inv["Varlık"] = inv["asset"].apply(asset_label)
        inv["Miktar"] = inv["qty"].apply(lambda x: str(D(x)))
        inv["Ort. Maliyet"] = inv["avg_cost_try"].apply(lambda x: str(q4(D(x))))
        inv["Güncel Fiyat"] = inv["last_price_try"].apply(lambda x: str(q4(D(x))) if x is not None else "—")
        inv["Değer"] = inv["value_try"].apply(lambda x: str(q2(D(x))))
        inv["Unreal"] = inv["unrealized_try"].apply(lambda x: str(q2(D(x))))
        inv["Realized"] = inv["realized_try"].apply(lambda x: str(q2(D(x))))
        st.dataframe(inv[["Varlık", "Miktar", "Ort. Maliyet", "Güncel Fiyat", "Değer", "Unreal", "Realized"]], use_container_width=True)

with tabs[4]:
    st.subheader("Analiz (Fiyat Serileri)")
    with SessionLocal() as db:
        p = pd.read_sql(text("SELECT ts, asset, price, is_stale FROM prices ORDER BY id DESC LIMIT 2000"), db.bind)
    if p.empty:
        st.info("Fiyat geçmişi yok.")
    else:
        p["price_num"] = p["price"].apply(lambda x: float(D(x)))
        p["asset_name"] = p["asset"].apply(asset_label)
        chart = alt.Chart(p).mark_line().encode(
            x="ts:T",
            y="price_num:Q",
            color="asset_name:N",
            tooltip=["ts:T", "asset_name:N", "price_num:Q", "is_stale:Q"],
        ).interactive()
        st.altair_chart(chart, use_container_width=True)

with tabs[5]:
    st.subheader("Ayarlar")
    update_interval = st.number_input(
        "Update interval (dk)",
        value=int(settings.get("update_interval_min", "30")),
        step=5,
        min_value=5,
        key="set_update_interval",
    )
    pnl_thr = st.number_input(
        "PnL alarm eşiği (TRY)",
        value=float(settings.get("pnl_alert_threshold_try", "-5000")),
        step=500.0,
        key="set_pnl_thr",
    )

    fx_primary = st.selectbox(
        "FX Primary",
        ["exchangerate_host", "frankfurter", "tcmb"],
        index=["exchangerate_host", "frankfurter", "tcmb"].index(settings.get("fx_primary", "exchangerate_host")),
        key="set_fx_primary",
    )
    fx_fallback = st.selectbox(
        "FX Fallback",
        ["frankfurter", "exchangerate_host", "tcmb"],
        index=["frankfurter", "exchangerate_host", "tcmb"].index(settings.get("fx_fallback", "frankfurter")),
        key="set_fx_fallback",
    )
    metals_primary = st.selectbox(
        "Metals Primary",
        ["kapalicarsi_apiluna", "metals_dev", "manual"],
        index=["kapalicarsi_apiluna", "metals_dev", "manual"].index(settings.get("metals_primary", "kapalicarsi_apiluna")),
        key="set_metals_primary",
    )
    metals_fallback = st.selectbox(
        "Metals Fallback",
        ["manual", "metals_dev", "kapalicarsi_apiluna"],
        index=["manual", "metals_dev", "kapalicarsi_apiluna"].index(settings.get("metals_fallback", "manual")),
        key="set_metals_fallback",
    )
    copper_provider = st.selectbox(
        "Copper Provider",
        ["kitco", "manual"],
        index=["kitco", "manual"].index(settings.get("copper_provider", "kitco")),
        key="set_copper_provider",
    )

    if st.button("💾 Ayarları Kaydet", key="btn_save_settings"):
        with SessionLocal() as db:
            set_setting(db, "update_interval_min", str(int(update_interval)))
            set_setting(db, "pnl_alert_threshold_try", str(Decimal(str(pnl_thr))))
            set_setting(db, "fx_primary", fx_primary)
            set_setting(db, "fx_fallback", fx_fallback)
            set_setting(db, "metals_primary", metals_primary)
            set_setting(db, "metals_fallback", metals_fallback)
            set_setting(db, "copper_provider", copper_provider)
            db.commit()
        st.success("Ayarlar kaydedildi. Interval değiştiyse servisi yeniden başlat.")

with tabs[6]:
    st.subheader("Servis / Log")
    st.code(f"DB: {get_db_path()}\nServis: python service/run_service.py\nLog: logs/service.log")
    with SessionLocal() as db:
        recent = pd.read_sql(text("SELECT id, ts, asset, price, source, is_stale, error_msg FROM prices ORDER BY id DESC LIMIT 25"), db.bind)
    st.dataframe(recent, use_container_width=True)

with tabs[7]:
    st.subheader("Manuel Fiyat (Fail-safe)")
    a = st.selectbox("Varlık", list(ASSETS_META.keys()), format_func=asset_label, key="man_a")
    v = st.text_input("Fiyat (TRY)", value="0", key="man_price")
    if st.button("Kaydet (manual price)", key="btn_manual_price"):
        try:
            vd = D(v)
            if vd <= 0:
                raise ValueError("Fiyat pozitif olmalı.")
            with SessionLocal() as db:
                insert_manual_price(db, a, vd, source="manual")
                db.commit()
            st.success("Manuel fiyat kaydedildi. Yenile.")
        except Exception as e:
            st.error(f"Hata: {e}")
