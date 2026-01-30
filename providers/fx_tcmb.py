from __future__ import annotations
from decimal import Decimal
from typing import Dict, List
import requests
import xml.etree.ElementTree as ET
from providers.base import PriceProvider, ProviderError

class TCMBFX(PriceProvider):
    name = "tcmb"
    def __init__(self, timeout_s: int = 10):
        self.timeout_s = timeout_s

    def get_prices_try(self, assets: List[str]) -> Dict[str, Decimal]:
        want = set(assets)
        if not ({"USDTRY","EURTRY"} & want):
            return {}
        try:
            r = requests.get("https://www.tcmb.gov.tr/kurlar/today.xml", timeout=self.timeout_s)
            r.raise_for_status()
            root = ET.fromstring(r.text)
            def find(code: str):
                for cur in root.findall("Currency"):
                    if cur.attrib.get("CurrencyCode") == code:
                        fs = cur.findtext("ForexSelling")
                        return Decimal(fs) if fs else None
                return None
            out: Dict[str, Decimal] = {}
            if "USDTRY" in want:
                v = find("USD"); 
                if v is not None: out["USDTRY"] = v
            if "EURTRY" in want:
                v = find("EUR");
                if v is not None: out["EURTRY"] = v
            return out
        except Exception as e:
            raise ProviderError(f"TCMB FX failed: {e}") from e
