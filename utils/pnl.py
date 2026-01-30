from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Tuple

from utils.decimal import D

@dataclass
class InventoryRow:
    asset: str
    qty: Decimal
    avg_cost_try: Decimal
    realized_try: Decimal

def compute_inventory_wavg(transactions: List[dict]) -> Dict[str, InventoryRow]:
    """Weighted-average inventory with stock blocking."""
    state: Dict[str, InventoryRow] = {}
    for r in transactions:
        asset = r["asset"]
        side = r["side"]
        qty = D(r["qty"])
        unit_price = D(r["unit_price"])
        fee = D(r.get("fee", "0"))

        row = state.get(asset, InventoryRow(asset=asset, qty=Decimal("0"), avg_cost_try=Decimal("0"), realized_try=Decimal("0")))

        if side == "BUY":
            total_cost = qty * unit_price + fee
            new_qty = row.qty + qty
            if new_qty > 0:
                row.avg_cost_try = (row.avg_cost_try * row.qty + total_cost) / new_qty
            row.qty = new_qty
        else:
            if qty > row.qty:
                raise ValueError(f"{asset} stok yetersiz: elde {row.qty}, satılmak istenen {qty}")
            proceeds = qty * unit_price - fee
            cost = qty * row.avg_cost_try
            row.realized_try += (proceeds - cost)
            row.qty -= qty
            if row.qty == 0:
                row.avg_cost_try = Decimal("0")

        state[asset] = row
    return state

def valuation_from_prices(inv: Dict[str, InventoryRow], mid_prices: Dict[str, Decimal]) -> Tuple[Dict[str, dict], Decimal, Decimal, Decimal]:
    breakdown: Dict[str, dict] = {}
    total_value = Decimal("0")
    unrealized = Decimal("0")
    realized = Decimal("0")

    for asset, row in inv.items():
        mid = mid_prices.get(asset, Decimal("0"))
        value = row.qty * mid
        cost = row.qty * row.avg_cost_try
        u = value - cost
        breakdown[asset] = {
            "qty": str(row.qty),
            "avg_cost_try": str(row.avg_cost_try),
            "mid_price_try": str(mid),
            "value_try": str(value),
            "unrealized_try": str(u),
            "realized_try": str(row.realized_try),
        }
        total_value += value
        unrealized += u
        realized += row.realized_try

    return breakdown, total_value, unrealized, realized
