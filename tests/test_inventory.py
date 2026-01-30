from decimal import Decimal
import pandas as pd
from app import compute_inventory_and_pnl

def test_stock_block_sell():
    tx = pd.DataFrame([{"asset":"XAU_G","side":"BUY","qty":"10","unit_price":"2000","fee":"0"}])
    prices = {"XAU_G": Decimal("2100")}
    df = compute_inventory_and_pnl(tx, prices)
    assert df[df["asset"]=="XAU_G"]["qty"].iloc[0] == Decimal("10")

    tx2 = pd.concat([tx, pd.DataFrame([{"asset":"XAU_G","side":"SELL","qty":"11","unit_price":"2100","fee":"0"}])], ignore_index=True)
    try:
        compute_inventory_and_pnl(tx2, prices)
        assert False
    except ValueError:
        assert True
