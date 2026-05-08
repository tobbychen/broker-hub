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
