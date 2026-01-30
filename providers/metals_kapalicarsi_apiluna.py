from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Tuple

from providers.base import PriceProvider, ProviderError
from utils.http import build_retry_session

class KapaliCarsiApilunaProvider(PriceProvider):
    """Türkiye odaklı fiyatlar (Kapalıçarşı) — community endpoint.
    - bid = alis
    - ask = satis
    - mid = (bid+ask)/2
    """
    name = "kapalicarsi_apiluna"

    def __init__(self, timeout_s: int = 10):
        self.session = build_retry_session(timeout_s=timeout_s)

    def _norm_dec(self, x) -> Decimal:
        if x is None or x == "":
            raise ValueError("empty")
        if isinstance(x, (int, float, Decimal)):
            return Decimal(str(x))
        s = str(x).strip()
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s and "." not in s:
            s = s.replace(",", ".")
        return Decimal(s)

    def _read_bid_ask(self, it: dict) -> Tuple[Decimal, Decimal]:
        bid = None
        ask = None
        for k in ["alis", "buy"]:
            if k in it and it[k] not in (None, ""):
                bid = self._norm_dec(it[k])
                break
        for k in ["satis", "sell"]:
            if k in it and it[k] not in (None, ""):
                ask = self._norm_dec(it[k])
                break
        if bid is None and ask is None:
            for k in ["son", "last", "price"]:
                if k in it and it[k] not in (None, ""):
                    v = self._norm_dec(it[k])
                    return v, v
            raise KeyError("no bid/ask fields")
        if bid is None: bid = ask
        if ask is None: ask = bid
        return bid, ask

    def fetch_bid_ask_map(self) -> Dict[str, Tuple[Decimal, Decimal]]:
        try:
            r = self.session.get("https://kapalicarsi.apiluna.org/", timeout=getattr(self.session, "request_timeout_s", 10))
            r.raise_for_status()
            j = r.json()

            items = []
            for _, v in j.items():
                if isinstance(v, list):
                    items.extend(v)

            def match(subs: List[str]):
                for it in items:
                    name = str(it.get("name", "") or it.get("adi", "") or it.get("kod", "") or "").lower()
                    if any(s in name for s in subs):
                        return it
                return None

            out: Dict[str, Tuple[Decimal, Decimal]] = {}

            def put(asset: str, subs: List[str]):
                it = match(subs)
                if it:
                    out[asset] = self._read_bid_ask(it)

            put("XAU_G", ["gram alt", "gram-alt", "gram_alt", "gramalt", "altın", "altin"])
            put("XAG_G", ["gram güm", "gram gum", "gümüş", "gumus", "silver"])
            put("USDTRY", ["usd"])
            put("EURTRY", ["eur"])

            if not out:
                raise ProviderError("Kapalıçarşı: eşleşen sembol bulunamadı")
            return out
        except Exception as e:
            raise ProviderError(f"Kapalıçarşı API failed: {e}") from e

    def get_prices_try(self, assets: List[str]) -> Dict[str, Decimal]:
        want = set(assets)
        bidask = self.fetch_bid_ask_map()
        out: Dict[str, Decimal] = {}
        for a in want:
            if a in bidask:
                bid, ask = bidask[a]
                out[a] = (bid + ask) / Decimal("2")
        if not out:
            raise ProviderError("Kapalıçarşı: requested assets not available")
        return out
