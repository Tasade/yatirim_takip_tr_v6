from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text

class Base(DeclarativeBase):
    pass

class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[str] = mapped_column(String, nullable=False)
    asset: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)  # BUY/SELL
    qty: Mapped[str] = mapped_column(String, nullable=False)   # Decimal as string
    unit_price: Mapped[str] = mapped_column(String, nullable=False)
    fee: Mapped[str] = mapped_column(String, nullable=False, default="0")
    currency: Mapped[str] = mapped_column(String, nullable=False, default="TRY")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

class Price(Base):
    __tablename__ = "prices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[str] = mapped_column(String, nullable=False)          # ISO datetime
    asset: Mapped[str] = mapped_column(String, nullable=False)
    # price = mid (TRY/birim)
    price: Mapped[str] = mapped_column(String, nullable=False)       # Decimal as string
    # Optional bid/ask (fiziki piyasa)
    price_buy: Mapped[str | None] = mapped_column(String, nullable=True)   # bid
    price_sell: Mapped[str | None] = mapped_column(String, nullable=True)  # ask
    currency: Mapped[str] = mapped_column(String, nullable=False, default="TRY")
    source: Mapped[str] = mapped_column(String, nullable=False)
    is_stale: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0/1
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)

class Snapshot(Base):
    __tablename__ = "snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[str] = mapped_column(String, nullable=False)
    total_value_try: Mapped[str] = mapped_column(String, nullable=False)
    breakdown_json: Mapped[str] = mapped_column(Text, nullable=False)
