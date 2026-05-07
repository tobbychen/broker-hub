"""eBay Browse API monitor for sports card prices."""
import asyncio
import httpx
import logging
from datetime import datetime
from ..config import get_market_data_config
from .base import BaseMonitor, Alert

logger = logging.getLogger(__name__)


class EbayMonitor(BaseMonitor):
    """Monitor sports card prices via eBay Browse API."""

    BASE_URL = "https://api.ebay.com/buy/browse/v1"

    # Sports card categories on eBay
    CARD_CATEGORIES = {
        "pokemon": "26104",    # Pokemon
        "basketball": "212",    # NBA Basketball
        "baseball": "213",      # MLB Baseball
        "football": "4851",     # NFL Football
        "soccer": "20808",     # Soccer
    }

    @property
    def name(self) -> str:
        return "ebay"

    def __init__(self):
        super().__init__(get_market_data_config().get("ebay", {}))
        self.threshold = self.config.get("price_change_threshold", 0.05)

    def is_market_open(self) -> bool:
        return True

    async def check(self) -> list[Alert]:
        """Check all watched cards for price changes."""
        if not self.config.get("enabled", True):
            return []

        api_key = self.config.get("api_key")
        if not api_key:
            logger.warning("[ebay] No API key configured, skipping check")
            return []

        alerts = []
        watched_cards = self.config.get("watched_cards", [])

        for card in watched_cards:
            try:
                alert = await self._check_card(api_key, card)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"[ebay] Error checking card {card.get('name')}: {e}")

        self.last_check = datetime.now()
        return alerts

    async def _check_card(self, api_key: str, card: dict) -> Alert | None:
        """Check a single card's price against recent sold listings."""
        search_term = self._build_search_term(card)
        recent_price = await self._get_recent_sold_price(api_key, search_term, card.get("min_grade"))

        if recent_price is None:
            return None

        stored_price = card.get("last_price")
        if stored_price and recent_price != stored_price:
            change_pct = (recent_price - stored_price) / stored_price
            if abs(change_pct) > self.threshold:
                return Alert(
                    source="ebay",
                    alert_type="price_spike",
                    symbol=card.get("name", search_term),
                    exchange="eBay",
                    details={
                        "current_price": recent_price,
                        "previous_price": stored_price,
                        "change_pct": round(change_pct * 100, 2),
                        "card_id": card.get("id"),
                        "category": card.get("category"),
                        "grade": card.get("min_grade"),
                    },
                    timestamp=datetime.now(),
                    priority="high" if abs(change_pct) > 0.10 else "normal",
                )

        return None

    def _build_search_term(self, card: dict) -> str:
        """Build eBay search term from card info."""
        parts = [card.get("name", "")]
        if card.get("set_name"):
            parts.append(card["set_name"])
        if card.get("year"):
            parts.insert(0, str(card["year"]))
        return " ".join(parts)

    async def _get_recent_sold_price(
        self, api_key: str, search_term: str, min_grade: str | None = None
    ) -> float | None:
        """Query eBay sold listings and return median price."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            "Content-Type": "application/json",
        }

        params = {
            "q": search_term,
            "filter": "buyingOptions:FIXED_PRICE,condition:GRADED",
            "sort": "endDate:asc",
            "limit": "10",
        }

        if min_grade:
            params["filter"] += f",grade:{min_grade}"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/item_summary/search",
                    headers=headers,
                    params=params,
                )
                if resp.status_code != 200:
                    logger.warning(f"[ebay] API returned {resp.status_code}: {resp.text[:200]}")
                    return None

                data = resp.json()
                items = data.get("itemSummaries", [])
                if not items:
                    return None

                prices = [
                    float(item.get("price", {}).get("value", 0))
                    for item in items
                    if item.get("price", {}).get("value")
                ]

                if not prices:
                    return None

                return sorted(prices)[len(prices) // 2]

        except httpx.RequestError as e:
            logger.error(f"[ebay] Request error: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"[ebay] Parse error: {e}")
            return None

    async def _fetch_price(self, search_term: str, min_grade: str | None = None) -> float | None:
        """Public method for ad-hoc price lookup."""
        api_key = self.config.get("api_key")
        if not api_key:
            return None
        return await self._get_recent_sold_price(api_key, search_term, min_grade)
