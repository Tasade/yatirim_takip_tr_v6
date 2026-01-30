from __future__ import annotations
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, List

class ProviderError(Exception):
    pass

class PriceProvider(ABC):
    name: str

    @abstractmethod
    def get_prices_try(self, assets: List[str]) -> Dict[str, Decimal]:
        raise NotImplementedError
