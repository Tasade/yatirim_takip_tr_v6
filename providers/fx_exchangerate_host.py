from __future__ import annotations
from decimal import Decimal
from typing import Dict, List
import requests
from providers.base import PriceProvider, ProviderError

class ExchangerateHostFX(PriceProvider):
    name = "exchangerate_host"
    def __init__(self, timeout_s: int = 10):
        self.timeout_s = timeout_s

    def get_prices_try(self, assets: List[str]) -> Dict[str, Decimal]:
        want = set(assets)
        symbols = []
        if "USDTRY" in want: symbols.append("USD")
        if "EURTRY" in want: symbols.append("EUR")
        if not symbols: return {}
        try:
            url = "https://api.exchangerate.host/latest?base=TRY&symbols=" + ",".join(symbols)
            r = requests.get(url, timeout=self.timeout_s); r.raise_for_status()
            j = r.json(); rates = j.get("rates", {})
            out: Dict[str, Decimal] = {}
            if "USDTRY" in want and "USD" in rates:
                out["USDTRY"] = (Decimal("1") / Decimal(str(rates["USD"])))
            if "EURTRY" in want and "EUR" in rates:
                out["EURTRY"] = (Decimal("1") / Decimal(str(rates["EUR"])))
            return out
        except Exception as e:
            raise ProviderError(f"exchangerate.host FX failed: {e}") from e
