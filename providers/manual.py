from __future__ import annotations
from decimal import Decimal
from typing import Dict, List
from providers.base import PriceProvider, ProviderError

class ManualProvider(PriceProvider):
    name = "manual"
    def __init__(self, manual_prices: Dict[str, Decimal] | None = None):
        self.manual_prices = manual_prices or {}

    def get_prices_try(self, assets: List[str]) -> Dict[str, Decimal]:
        out: Dict[str, Decimal] = {a:self.manual_prices[a] for a in assets if a in self.manual_prices}
        if not out:
            raise ProviderError("No manual prices for requested assets")
        return out
