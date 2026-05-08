"""eBay Browse API monitor for sports card prices."""
import asyncio
import httpx
import logging
from datetime import datetime
from ..config import get_market_data_config
from .. import database as db
from .base import BaseMonitor, Alert

logger = logging.getLogger(__name__)


class EbayMonitor(BaseMonitor):
    """Monitor sports card prices via eBay Browse API."""

    BASE_URL = "https://api.ebay.com/buy/browse/v1"

    CARD_CATEGORIES = {
        "pokemon": "26104",
        "basketball": "212",
        "baseball": "213",
        "football": "4851",
        "soccer": "20808",
    }

    @property
    def name(self) -> str:
        return "ebay"

    def __init__(self):
        super().__init__(get_market_data_config().get("ebay", {}))
        self.threshold = self.config.get("price_change_threshold", 0.05)

    def is_market_open(self) -> bool:
        return True

    def _parse_notes(self, notes: str) -> dict:
        """Parse pipe-separated card metadata from watchlist notes field.

        Format: card_name|set_name|year|category|min_grade|last_price
        Example: Charizard|Base Set|1999|pokemon|PSA 10|5000
        """
        parts = notes.split("|")
        return {
            "name": parts[0] if len(parts) > 0 else "",
            "set_name": parts[1] if len(parts) > 1 else "",
            "year": parts[2] if len(parts) > 2 else "",
            "category": parts[3] if len(parts) > 3 else "",
            "min_grade": parts[4] if len(parts) > 4 else "",
            "last_price": float(parts[5]) if len(parts) > 5 and parts[5] else None,
        }

    async def check(self) -> list[Alert]:
        """Check all watched cards from SQLite for price changes."""
        if not self.config.get("enabled", True):
            return []

        api_key = self.config.get("api_key")
        if not api_key:
            logger.warning("[ebay] No API key configured, skipping check")
            return []

        alerts = []
        try:
            watched_cards = await db.get_watchlist_items("sports_card")
        except Exception as e:
            logger.error(f"[ebay] Failed to read watchlist from SQLite: {e}")
            return alerts

        for card in watched_cards:
            try:
                alert = await self._check_card(api_key, card)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"[ebay] Error checking card {card.get('symbol')}: {e}")

        self.last_check = datetime.now()
        return alerts

    async def _check_card(self, api_key: str, card: dict) -> Alert | None:
        """Check a single card's price against recent sold listings."""
        meta = self._parse_notes(card.get("notes", ""))
        search_term = self._build_search_term(meta)
        recent_price = await self._get_recent_sold_price(api_key, search_term, meta.get("min_grade"))

        if recent_price is None:
            return None

        stored_price = meta.get("last_price")
        symbol = card.get("symbol", search_term)

        # Write price to market_cache
        try:
            await db.set_market_cache(
                symbol=symbol,
                data_type="latest_price",
                raw_data={"price": recent_price, "last_recorded": stored_price},
                exchange="eBay",
            )
        except Exception:
            pass

        if stored_price and recent_price != stored_price:
            change_pct = (recent_price - stored_price) / stored_price
            if abs(change_pct) > self.threshold:
                return Alert(
                    source="ebay",
                    alert_type="price_spike",
                    symbol=symbol,
                    exchange="eBay",
                    details={
                        "current_price": recent_price,
                        "previous_price": stored_price,
                        "change_pct": round(change_pct * 100, 2),
                        "card_id": card.get("id"),
                        "category": meta.get("category"),
                        "grade": meta.get("min_grade"),
                    },
                    timestamp=datetime.now(),
                    priority="high" if abs(change_pct) > 0.10 else "normal",
                )

        return None

    def _build_search_term(self, card: dict) -> str:
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
            "X-EBAY-C-MARKETETPLACE-ID": "EBAY_US",
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

    async def get_watchlist(self) -> list[dict]:
        """Return eBay card watchlist items from SQLite."""
        items = []
        try:
            cards = await db.get_watchlist_items("sports_card")
        except Exception:
            return items

        for card in cards:
            meta = self._parse_notes(card.get("notes", ""))
            items.append({
                "symbol": card.get("symbol", ""),
                "name": meta.get("name", ""),
                "set_name": meta.get("set_name", ""),
                "category": meta.get("category", ""),
                "exchange": "eBay",
            })
        return items
