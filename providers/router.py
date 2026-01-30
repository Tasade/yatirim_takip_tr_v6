from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Tuple

from providers.base import ProviderError
from providers.fx_frankfurter import FrankfurterFXProvider
from providers.metals_kapalicarsi_apiluna import KapaliCarsiApilunaProvider
from providers.copper_stooq import CopperStooqProvider, LB_TO_GRAM


class ProviderRouter:
    def __init__(
        self,
        fx_primary: str = "frankfurter",
        fx_fallback: str = "frankfurter",
        metals_primary: str = "kapalicarsi_apiluna",
        metals_fallback: str = "kapalicarsi_apiluna",
        copper_provider: str = "copper_stooq",
        timeout_s: int = 10,
    ):
        self.timeout_s = timeout_s
        self.fx = FrankfurterFXProvider(timeout_s=timeout_s)
        self.metals = KapaliCarsiApilunaProvider(timeout_s=timeout_s)
        self.copper = CopperStooqProvider(timeout_s=timeout_s)

    def get_all_quotes_try(self, assets: List[str], manual_prices=None) -> Tuple[Dict[str, dict], Dict[str, str]]:
        want = set(assets)
        quotes: Dict[str, dict] = {}
        sources: Dict[str, str] = {}

        # 1) FX (USDTRY/EURTRY) — partial
        try:
            fx = self.fx.get_prices_try([a for a in want if a in ("USDTRY", "EURTRY")])
            for a, v in fx.items():
                quotes[a] = {"mid": v, "bid": v, "ask": v}
                sources[a] = self.fx.name
        except Exception:
            pass  # partial

        # 2) Metals (XAU_G/XAG_G) — partial
        try:
            met = self.metals.get_prices_try([a for a in want if a in ("XAU_G", "XAG_G")])
            for a, v in met.items():
                quotes[a] = {"mid": v, "bid": v, "ask": v}
                sources[a] = self.metals.name
        except Exception:
            pass  # partial

        # 3) Copper: HG.F USD/lb -> USD/gr -> TRY/gr (USDTRY şart)
        if "XCU_G" in want:
            try:
                usdtry = quotes.get("USDTRY", {}).get("mid")
                if usdtry is None:
                    # USDTRY yoksa bakır hesaplamayı atla
                    raise ProviderError("USDTRY missing for copper conversion")

                usd_per_lb = self.copper._parse_last_close_usd_per_lb()
                usd_per_gr = usd_per_lb / LB_TO_GRAM
                try_per_gr = usd_per_gr * Decimal(str(usdtry))

                quotes["XCU_G"] = {"mid": try_per_gr, "bid": try_per_gr, "ask": try_per_gr}
                sources["XCU_G"] = "stooq_hg.f"
            except Exception:
                pass  # partial

        return quotes, sources
