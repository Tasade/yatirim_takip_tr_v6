from __future__ import annotations
from decimal import Decimal
from typing import Dict, List
import requests
from providers.base import PriceProvider, ProviderError

class FrankfurterFX(PriceProvider):
    name = "frankfurter"
    def __init__(self, timeout_s: int = 10):
        self.timeout_s = timeout_s

    def get_prices_try(self, assets: List[str]) -> Dict[str, Decimal]:
        want = set(assets)
        if not ({"USDTRY","EURTRY"} & want):
            return {}
        try:
            r = requests.get("https://api.frankfurter.app/latest?base=EUR", timeout=self.timeout_s)
            r.raise_for_status()
            j = r.json(); rates = j.get("rates", {})
            eur_try = Decimal(str(rates.get("TRY"))) if rates.get("TRY") else None
            eur_usd = Decimal(str(rates.get("USD"))) if rates.get("USD") else None
            out: Dict[str, Decimal] = {}
            if "EURTRY" in want and eur_try is not None:
                out["EURTRY"] = eur_try
            if "USDTRY" in want and eur_try is not None and eur_usd is not None:
                out["USDTRY"] = (eur_try / eur_usd)
            return out
        except Exception as e:
            raise ProviderError(f"Frankfurter FX failed: {e}") from e
