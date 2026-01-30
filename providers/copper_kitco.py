from __future__ import annotations
from decimal import Decimal
import re, requests
from bs4 import BeautifulSoup
from providers.base import ProviderError

class KitcoCopperProvider:
    name = "kitco"
    def __init__(self, timeout_s: int = 10):
        self.timeout_s = timeout_s

    def fetch_usd_per_lb(self) -> Decimal:
        try:
            url = "https://www.kitco.com/price/base-metals/copper"
            r = requests.get(url, timeout=self.timeout_s, headers={"User-Agent":"Mozilla/5.0"})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            text_all = soup.get_text(" ", strip=True)
            nums = re.findall(r"\b(\d+(?:\.\d+)?)\b", text_all)
            for n in nums[:2000]:
                f = Decimal(n)
                if Decimal("2") < f < Decimal("15"):
                    return f
            raise ValueError("parse failed")
        except Exception as e:
            raise ProviderError(f"Kitco copper parse failed: {e}") from e
