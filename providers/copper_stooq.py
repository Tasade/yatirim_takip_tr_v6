from __future__ import annotations

from decimal import Decimal

from providers.base import PriceProvider, ProviderError
from utils.http import build_retry_session

LB_TO_GRAM = Decimal("453.59237")  # 1 lb = 453.59237 gram


class CopperStooqProvider(PriceProvider):
    """
    Stooq HG.F -> cent/lb verir.
    USD/lb = cent/lb / 100
    """
    name = "copper_stooq"

    def __init__(self, timeout_s: int = 10):
        self.session = build_retry_session(timeout_s=timeout_s)

    def _parse_last_close_usd_per_lb(self) -> Decimal:
        url = "https://stooq.com/q/l/?s=hg.f&f=sd2t2ohlcv&h&e=csv"
        r = self.session.get(url, timeout=getattr(self.session, "request_timeout_s", 10))
        r.raise_for_status()

        lines = r.text.strip().splitlines()
        if len(lines) < 2:
            raise ValueError("stooq csv empty")

        parts = lines[1].split(",")
        if len(parts) < 7:
            raise ValueError("stooq csv malformed")

        close = parts[6]  # Close (cent/lb)
        cent_per_lb = Decimal(close)
        usd_per_lb = cent_per_lb / Decimal("100")
        return usd_per_lb

    def get_prices_try(self, assets):
        # Bu provider TRY fiyatını Router'da USDTRY ile dönüştürerek üretir.
        raise ProviderError("CopperStooqProvider must be used via ProviderRouter.")
