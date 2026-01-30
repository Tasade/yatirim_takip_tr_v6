from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Tuple

from providers.base import PriceProvider, ProviderError
from utils.http import build_retry_session


class KapaliCarsiApilunaProvider(PriceProvider):
    name = "kapalicarsi_apiluna"

    def __init__(self, timeout_s: int = 10):
        self.session = build_retry_session(timeout_s=timeout_s)

    def _to_dec(self, x) -> Decimal:
        s = str(x).strip()
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s and "." not in s:
            s = s.replace(",", ".")
        return Decimal(s)

    def _read_bid_ask(self, it: dict) -> Tuple[Decimal, Decimal]:
        bid = it.get("alis") or it.get("buy") or it.get("bid")
        ask = it.get("satis") or it.get("sell") or it.get("ask")
        last = it.get("son") or it.get("last") or it.get("price")

        if bid is None and ask is None and last is None:
            raise KeyError("no price fields")

        if last is not None and (bid is None and ask is None):
            v = self._to_dec(last)
            return v, v

        if bid is None:
            bid = ask
        if ask is None:
            ask = bid

        return self._to_dec(bid), self._to_dec(ask)

    def _fetch_items(self) -> List[dict]:
        r = self.session.get("https://kapalicarsi.apiluna.org/", timeout=getattr(self.session, "request_timeout_s", 10))
        r.raise_for_status()
        j = r.json()

        items: List[dict] = []
        for v in j.values():
            if isinstance(v, list):
                items.extend(v)
        return items

    def _find(self, items: List[dict], keywords: List[str]) -> dict | None:
        for it in items:
            name = str(it.get("name") or it.get("adi") or it.get("kod") or "").lower()
            if any(k in name for k in keywords):
                return it
        return None

    def get_prices_try(self, assets: List[str]) -> Dict[str, Decimal]:
        want = set(assets)
        items = self._fetch_items()
        out: Dict[str, Decimal] = {}

        def put(asset: str, keywords: List[str]):
            it = self._find(items, keywords)
            if not it:
                return
            bid, ask = self._read_bid_ask(it)
            out[asset] = (bid + ask) / Decimal("2")

        if "XAU_G" in want:
            put("XAU_G", ["gram alt", "gramalt", "altın", "altin"])
        if "XAG_G" in want:
            put("XAG_G", ["gram güm", "gram gum", "gümüş", "gumus", "silver"])

        if not out:
            raise ProviderError("Kapalıçarşı: nothing matched")
        return out
