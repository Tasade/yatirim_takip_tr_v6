from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Tuple

from providers.base import ProviderError
from providers.fx_exchangerate_host import ExchangerateHostFX
from providers.fx_frankfurter import FrankfurterFX
from providers.fx_tcmb import TCMBFX
from providers.metals_metalsdev import MetalsDevProvider
from providers.metals_kapalicarsi_apiluna import KapaliCarsiApilunaProvider
from providers.manual import ManualProvider
from providers.copper_kitco import KitcoCopperProvider

@dataclass
class ProviderRouter:
    fx_primary: str = "exchangerate_host"
    fx_fallback: str = "frankfurter"
    metals_primary: str = "metals_dev"
    metals_fallback: str = "manual"
    copper_provider: str = "kitco"
    timeout_s: int = 10

    def _fx(self, name: str):
        if name == "exchangerate_host": return ExchangerateHostFX(self.timeout_s)
        if name == "frankfurter": return FrankfurterFX(self.timeout_s)
        if name == "tcmb": return TCMBFX(self.timeout_s)
        raise ValueError(name)

    def _metals(self, name: str, manual_prices: Dict[str, Decimal] | None):
        if name == "metals_dev": return MetalsDevProvider(self.timeout_s)
        if name == "manual": return ManualProvider(manual_prices)
        raise ValueError(name)

    def get_all_prices_try(self, assets: List[str], manual_prices: Dict[str, Decimal] | None = None) -> Tuple[Dict[str, Decimal], Dict[str, str]]:
        want = set(assets)
        prices: Dict[str, Decimal] = {}
        sources: Dict[str, str] = {}

        # FX
        fx_assets = [a for a in want if a in {"USDTRY","EURTRY"}]
        if fx_assets:
            for name in [self.fx_primary, self.fx_fallback, "tcmb"]:
                try:
                    got = self._fx(name).get_prices_try(fx_assets)
                    prices.update(got)
                    for k in got: sources[k] = name
                    break
                except Exception:
                    continue

        # Metals
        metals_assets = [a for a in want if a in {"XAU_G","XAG_G"}]
        if metals_assets:
            for name in [self.metals_primary, self.metals_fallback]:
                try:
                    got = self._metals(name, manual_prices).get_prices_try(metals_assets)
                    prices.update(got)
                    for k in got: sources[k] = name
                    break
                except Exception:
                    continue

        # Copper TRY/gr (USD/lb -> TRY/gr)
        if "XCU_G" in want:
            try:
                if "USDTRY" not in prices:
                    got = self._fx(self.fx_primary).get_prices_try(["USDTRY"])
                    prices.update(got)
                    for k in got: sources[k] = self.fx_primary
                usdtry = prices.get("USDTRY")
                if usdtry is None:
                    raise ProviderError("USDTRY missing")
                if self.copper_provider == "kitco":
                    usd_lb = KitcoCopperProvider(self.timeout_s).fetch_usd_per_lb()
                    lb_to_g = Decimal("453.59237")
                    prices["XCU_G"] = (usd_lb * usdtry) / lb_to_g
                    sources["XCU_G"] = "kitco"
                else:
                    if manual_prices and "XCU_G" in manual_prices:
                        prices["XCU_G"] = manual_prices["XCU_G"]
                        sources["XCU_G"] = "manual"
                    else:
                        raise ProviderError("Copper manual missing")
            except Exception:
                if manual_prices and "XCU_G" in manual_prices:
                    prices["XCU_G"] = manual_prices["XCU_G"]
                    sources["XCU_G"] = "manual"

        return prices, sources
