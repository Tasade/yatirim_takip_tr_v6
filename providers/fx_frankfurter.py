from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from providers.base import PriceProvider, ProviderError
from utils.http import build_retry_session


class FrankfurterFXProvider(PriceProvider):
    name = "frankfurter"

    def __init__(self, timeout_s: int = 10):
        self.session = build_retry_session(timeout_s=timeout_s)

    def get_prices_try(self, assets: List[str]) -> Dict[str, Decimal]:
        want = set(assets)
        out: Dict[str, Decimal] = {}

        # Frankfurter: https://api.frankfurter.dev/v1/latest?from=USD&to=TRY
        # TRY bazı günler ECB setinde yoksa None gelebilir; o yüzden EUR bazla da deneriz.
        def fetch_pair(frm: str, to: str) -> Decimal:
            url = f"https://api.frankfurter.dev/v1/latest?from={frm}&to={to}"
            r = self.session.get(url, timeout=getattr(self.session, "request_timeout_s", 10))
            r.raise_for_status()
            j = r.json()
            rate = j["rates"][to]
            return Decimal(str(rate))

        try:
            if "USDTRY" in want:
                out["USDTRY"] = fetch_pair("USD", "TRY")
            if "EURTRY" in want:
                out["EURTRY"] = fetch_pair("EUR", "TRY")
        except Exception as e:
            raise ProviderError(f"Frankfurter FX failed: {e}") from e

        if not out:
            raise ProviderError("Frankfurter: requested assets not available")

        return out
