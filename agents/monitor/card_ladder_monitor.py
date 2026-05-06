"""Card Ladder API monitor for sports card prices."""
import asyncio
import httpx
from datetime import datetime
from ..config import get_market_data_config
from .base import BaseMonitor, Alert


class CardLadderMonitor(BaseMonitor):
    BASE_URL = "https://api.cardladder.com/v1"

    @property
    def name(self) -> str:
        return "card_ladder"

    def __init__(self):
        super().__init__(get_market_data_config().get("card_ladder", {}))
        self.threshold = 0.05

    def is_market_open(self) -> bool:
        return True

    async def check(self) -> list[Alert]:
        if not self.config.get("enabled", True):
            return []
        return []

    async def _fetch_price(self, card_id: str) -> float | None:
        api_key = self.config.get("api_key")
        if not api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/cards/{card_id}/price",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    return resp.json().get("price")
        except Exception:
            pass
        return None
