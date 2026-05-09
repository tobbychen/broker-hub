"""eBay Browse API monitor for sports card prices.

Uses OAuth2 client credentials flow to obtain access tokens.
Tokens are cached and auto-refreshed on expiry.
Uses 'requests' for HTTP proxy compatibility on Windows.
"""
import asyncio
import json
import logging
import os
import requests
import aiosqlite
from datetime import datetime, timedelta
from pathlib import Path
from ..config import get_market_data_config
from .. import database as db
from .base import BaseMonitor, Alert

logger = logging.getLogger(__name__)


class EbayMonitor(BaseMonitor):
    """Monitor sports card prices via eBay Browse API."""

    BASE_URL = "https://api.ebay.com/buy/browse/v1"
    TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

    @property
    def name(self) -> str:
        return "ebay"

    def __init__(self):
        super().__init__(get_market_data_config().get("ebay", {}))
        self.threshold = self.config.get("price_change_threshold", 0.05)
        self._proxies = self._detect_proxy()

    def _detect_proxy(self) -> dict | None:
        for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
            val = os.environ.get(var)
            if val:
                return {"http": val, "https": val}
        return None

    def is_market_open(self) -> bool:
        return True

    async def _get_token(self) -> str | None:
        """Fetch a fresh OAuth2 access token from eBay (no caching — called per schedule run)."""
        client_id = self.config.get("client_id")
        client_secret = self.config.get("client_secret")
        if not client_id or not client_secret:
            logger.warning("[ebay] No client_id/client_secret configured")
            return None

        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        }

        try:
            resp = requests.post(
                self.TOKEN_URL,
                data=data,
                auth=(client_id, client_secret),
                proxies=self._proxies,
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"[ebay] Token request failed: {resp.status_code} {resp.text[:200]}")
                return None
            token_data = resp.json()
            logger.info(f"[ebay] Got access token, expires in {token_data.get('expires_in', '?')}s")
            return token_data["access_token"]
        except requests.RequestException as e:
            logger.error(f"[ebay] Token request error: {e}")
            return None

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

        token = await self._get_token()
        if not token:
            return []

        alerts = []
        try:
            watched_cards = await db.get_watchlist_items("sports_card")
        except Exception as e:
            logger.error(f"[ebay] Failed to read watchlist from SQLite: {e}")
            return alerts

        for card in watched_cards:
            try:
                alert = await self._check_card(token, card)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"[ebay] Error checking card {card.get('symbol')}: {e}")

        self.last_check = datetime.now()
        return alerts

    async def _check_card(self, token: str, card: dict) -> Alert | None:
        """Check a single card's price against recent sold listings."""
        meta = self._parse_notes(card.get("notes", ""))
        search_term = self._build_search_term(meta)
        recent_price = await self._fetch_price(token, search_term, meta.get("min_grade"))

        if recent_price is None:
            return None

        stored_price = meta.get("last_price")
        symbol = card.get("symbol", search_term)

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
            parts.insert(0, str(card.get("year")))
        return " ".join(parts)

    async def _fetch_price(self, token: str, search_term: str, min_grade: str | None = None) -> float | None:
        """Query eBay sold listings and return median price."""
        headers = {
            "Authorization": f"Bearer {token}",
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
            resp = requests.get(
                f"{self.BASE_URL}/item_summary/search",
                headers=headers,
                params=params,
                proxies=self._proxies,
                timeout=15,
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

        except requests.RequestException as e:
            logger.error(f"[ebay] Request error: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"[ebay] Parse error: {e}")
            return None

    async def get_watchlist(self) -> list[dict]:
        """Return eBay card watchlist items with current prices from SQLite market_cache."""
        items = []
        try:
            cards = await db.get_watchlist_items("sports_card")
        except Exception:
            return items

        DB_PATH = Path(__file__).parent.parent.parent / "data" / "broker_agents.db"
        for card in cards:
            meta = self._parse_notes(card.get("notes", ""))
            symbol = card.get("symbol", "")

            # Look up cached price
            price = None
            try:
                async with aiosqlite.connect(str(DB_PATH)) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute(
                        "SELECT raw_data FROM market_cache WHERE symbol=? AND data_type='latest_price' LIMIT 1",
                        (symbol,),
                    )
                    row = await cursor.fetchone()
                    if row:
                        rd = json.loads(row["raw_data"])
                        price = rd.get("price")
            except Exception:
                pass

            items.append({
                "symbol": symbol,
                "name": meta.get("name", ""),
                "set_name": meta.get("set_name", ""),
                "category": meta.get("category", ""),
                "exchange": "eBay",
                "price": price,
                "last_recorded": meta.get("last_price"),
            })
        return items