"""Broker interface for abstracting trade execution."""

from typing import Protocol, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"

@dataclass
class Position:
    """A position held in a broker account."""
    symbol: str
    quantity: float
    avg_cost: float
    exchange: str
    asset_class: str

@dataclass
class AccountInfo:
    """Account information from broker."""
    account_id: str
    cash: float
    buying_power: float
    currency: str = "USD"
    last_updated: datetime = None

@dataclass
class OrderDraft:
    """Draft order before submission."""
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    exchange: str = ""
    asset_class: str = ""

@dataclass
class OrderResult:
    """Result of order submission."""
    order_id: str
    status: str  # "pending", "filled", "cancelled", "rejected"
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    message: str = ""

class BrokerProtocol(Protocol):
    """Abstract interface for broker implementations."""

    @property
    def name(self) -> str:
        ...

    async def connect(self) -> bool:
        ...

    async def disconnect(self) -> None:
        ...

    async def is_connected(self) -> bool:
        ...

    async def get_positions(self) -> list[Position]:
        ...

    async def get_account_info(self) -> AccountInfo:
        ...

    async def draft_order(self, draft: OrderDraft) -> str:
        ...

    async def submit_order(self, draft: OrderDraft) -> OrderResult:
        ...

    async def cancel_order(self, order_id: str) -> bool:
        ...