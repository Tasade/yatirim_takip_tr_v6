from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from providers.base import PriceProvider, ProviderError
from utils.http import build_retry_session


class FrankfurterFXProvider(PriceProvider):
    name = "frankfurter"

    def __init__(self, timeout_s: int = 10):
        self.session = build_retry_session(timeout_s=timeout_s)

    def _fetch(self, frm: str, to: str) -> Decimal:
        url = f"https://api.frankfurter.dev/v1/latest?from={frm}&to={to}"
        r = self.session.get(url, timeout=getattr(self.session, "request_timeout_s", 10))
        r.raise_for_status()
        j = r.json()
        return Decimal(str(j["rates"][to]))

    def get_prices_try(self, assets: List[str]) -> Dict[str, Decimal]:
        want = set(assets)
        out: Dict[str, Decimal] = {}

        try:
            if "USDTRY" in want:
                out["USDTRY"] = self._fetch("USD", "TRY")
            if "EURTRY" in want:
                out["EURTRY"] = self._fetch("EUR", "TRY")
        except Exception as e:
            raise ProviderError(f"Frankfurter FX failed: {e}") from e

        if not out:
            raise ProviderError("Frankfurter: no assets returned")
        return out
