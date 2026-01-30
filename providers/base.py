from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, List


class ProviderError(RuntimeError):
    pass


class PriceProvider(ABC):
    name: str = "base"

    @abstractmethod
    def get_prices_try(self, assets: List[str]) -> Dict[str, Decimal]:
        """Return TRY-based prices for requested assets."""
        raise NotImplementedError
