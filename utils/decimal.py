from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP, getcontext

getcontext().prec = 28
TWOPLACES = Decimal("0.01")
FOURPLACES = Decimal("0.0001")

def D(x) -> Decimal:
    if x is None:
        return Decimal("0")
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))

def q2(x: Decimal) -> Decimal:
    return D(x).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

def q4(x: Decimal) -> Decimal:
    return D(x).quantize(FOURPLACES, rounding=ROUND_HALF_UP)
