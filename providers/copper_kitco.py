from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from providers.base import PriceProvider, ProviderError
from utils.http import build_retry_session


LB_TO_GRAM = Decimal("453.59237")  # 1 lb = 453.59237 gram


class CopperStooqProvider(PriceProvider):
    """
    Stooq HG.F -> cent/lb verir.
    TRY/gr = (cent_per_lb / 100) USD/lb  -> USD/gr -> TRY/gr
    """
    name = "copper_stooq"

    def __init__(self, timeout_s: int = 10):
        self.session = build_retry_session(timeout_s=timeout_s)

    def _parse_last_close_usd_per_lb(self) -> Decimal:
        # CSV endpoint
        # stooq: q/l/?s=hg.f... veya q/l/?s=hg.f&f=...
        url = "https://stooq.com/q/l/?s=hg.f&f=sd2t2ohlcv&h&e=csv"
        r = self.session.get(url, timeout=getattr(self.session, "request_timeout_s", 10))
        r.raise_for_status()
        lines = r.text.strip().splitlines()
        if len(lines) < 2:
            raise ValueError("stooq csv empty")
        # header: Symbol,Date,Time,Open,High,Low,Close,Volume
        parts = lines[1].split(",")
        if len(parts) < 7:
            raise ValueError("stooq csv malformed")
        close = parts[6]  # "589.20" => cent/lb
        cent_per_lb = Decimal(close)
        usd_per_lb = cent_per_lb / Decimal("100")
        return usd_per_lb

    def get_prices_try(self, assets: List[str]) -> Dict[str, Decimal]:
        if "XCU_G" not in set(assets):
            raise ProviderError("CopperStooq only supports XCU_G")

        # USDTRY mutlaka lazım; Router bunu FX provider'dan verir.
        raise ProviderError("CopperStooq must be called via Router with usdtry supplied.")
