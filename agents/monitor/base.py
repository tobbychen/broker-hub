"""Base monitor class — all monitors inherit this."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Alert:
    """A monitor alert that gets passed to the dispatcher."""
    source: str
    alert_type: str
    symbol: str
    exchange: str
    details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: str = "normal"


@dataclass
class MerchandiseAlert(Alert):
    """Alert for merchandise price changes with cross-platform data."""
    brand: str = ""
    model: str = ""
    variant: str = ""
    platforms: dict = field(default_factory=dict)  # {"eBay": 150.00, "Amazon": 145.00, ...}
    purchase_price: float = 0.0
    purchase_currency: str = "CNY"
    current_price: float = 0.0
    current_platform: str = ""
    change_pct: float = 0.0
    arbitrage_opportunity: bool = False
    source_platform: str = ""


class BaseMonitor(ABC):
    """Base class for all market monitors."""

    def __init__(self, config: dict):
        self.config = config
        self.last_check: Optional[datetime] = None

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def check(self) -> list[Alert]:
        pass

    @abstractmethod
    def is_market_open(self) -> bool:
        pass

    async def get_watchlist(self) -> list[dict]:
        """Return current prices for all watched assets. Override per monitor."""
        return []
