from __future__ import annotations
from decimal import Decimal
from typing import Dict, List
import os, requests
from providers.base import PriceProvider, ProviderError

class MetalsDevProvider(PriceProvider):
    name = "metals_dev"
    def __init__(self, timeout_s: int = 10):
        self.timeout_s = timeout_s
        self.api_key = os.getenv("METALS_DEV_API_KEY","").strip()

    def get_prices_try(self, assets: List[str]) -> Dict[str, Decimal]:
        if not self.api_key:
            raise ProviderError("METALS_DEV_API_KEY missing")
        want = set(assets)
        symbols = []
        if "XAU_G" in want: symbols.append("XAU")
        if "XAG_G" in want: symbols.append("XAG")
        if not symbols: return {}
        try:
            url = f"https://metals.dev/api/latest?api_key={self.api_key}&base=TRY&symbols={','.join(symbols)}"
            r = requests.get(url, timeout=self.timeout_s); r.raise_for_status()
            j = r.json(); rates = j.get("rates", {})
            OZ_TO_G = Decimal("31.1034768")
            out: Dict[str, Decimal] = {}
            if "XAU" in rates and "XAU_G" in want:
                try_oz = Decimal("1") / Decimal(str(rates["XAU"]))
                out["XAU_G"] = try_oz / OZ_TO_G
            if "XAG" in rates and "XAG_G" in want:
                try_oz = Decimal("1") / Decimal(str(rates["XAG"]))
                out["XAG_G"] = try_oz / OZ_TO_G
            return out
        except Exception as e:
            raise ProviderError(f"Metals.dev failed: {e}") from e
