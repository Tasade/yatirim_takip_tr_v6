from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Tuple

from providers.fx_frankfurter import FrankfurterFXProvider
from providers.metals_kapalicarsi_apiluna import KapaliCarsiApilunaProvider


class ProviderRouter:
    def __init__(self, timeout_s: int = 10):
        self.fx = FrankfurterFXProvider(timeout_s=timeout_s)
        self.metals = KapaliCarsiApilunaProvider(timeout_s=timeout_s)

    def get_all_quotes_try(self, assets: List[str], manual_prices=None) -> Tuple[Dict[str, dict], Dict[str, str]]:
        want = set(assets)
        quotes: Dict[str, dict] = {}
        sources: Dict[str, str] = {}

        # FX partial
        try:
            fx = self.fx.get_prices_try([a for a in want if a in ("USDTRY", "EURTRY")])
            for a, v in fx.items():
                quotes[a] = {"mid": v, "bid": v, "ask": v}
                sources[a] = self.fx.name
        except Exception:
            pass

        # Metals partial
        try:
            met = self.metals.get_prices_try([a for a in want if a in ("XAU_G", "XAG_G")])
            for a, v in met.items():
                quotes[a] = {"mid": v, "bid": v, "ask": v}
                sources[a] = self.metals.name
        except Exception:
            pass

        # Copper: manual fallback
        if "XCU_G" in want:
            if manual_prices and "XCU_G" in manual_prices:
                v = manual_prices["XCU_G"]
                quotes["XCU_G"] = {"mid": v, "bid": v, "ask": v}
                sources["XCU_G"] = "manual"
            # else: bırak boş kalsın, sistem yine çalışır

        return quotes, sources
