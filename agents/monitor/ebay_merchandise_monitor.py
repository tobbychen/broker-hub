"""eBay merchandise monitor for branded products.

Searches eBay by brand + model to track prices of owned merchandise.
"""
import asyncio
import json
import logging
import os
import requests
from datetime import datetime
from ..config import get_market_data_config
from .base import BaseMonitor, MerchandiseAlert

logger = logging.getLogger(__name__)


class EbayMerchandiseMonitor(BaseMonitor):
    """Monitor branded merchandise prices via eBay Browse API."""

    BASE_URL = "https://api.ebay.com/buy/browse/v1"
    TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

    @property
    def name(self) -> str:
        return "ebay_merchandise"

    def __init__(self):
        config = get_market_data_config().get("ebay", {})
        config["enabled"] = config.get("enabled", True)
        super().__init__(config)
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
        client_id = self.config.get("client_id")
        client_secret = self.config.get("client_secret")
        if not client_id or not client_secret:
            logger.warning("[ebay_merchandise] No credentials configured")
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
                logger.warning(f"[ebay_merchandise] Token failed: {resp.status_code}")
                return None
            return resp.json()["access_token"]
        except Exception as e:
            logger.error(f"[ebay_merchandise] Token error: {e}")
            return None

    def _parse_notes(self, notes: str) -> dict:
        """Parse pipe-separated merchandise metadata.

        Format: Brand|Model|Variant|PurchasePrice|PurchaseCurrency
        Example: Red Wing|875|Size 10D|149.99|USD
        """
        parts = notes.split("|")
        return {
            "brand": parts[0] if len(parts) > 0 else "",
            "model": parts[1] if len(parts) > 1 else "",
            "variant": parts[2] if len(parts) > 2 else "",
            "purchase_price": float(parts[3]) if len(parts) > 3 and parts[3] else None,
            "purchase_currency": parts[4] if len(parts) > 4 else "CNY",
        }

    async def check(self) -> list[MerchandiseAlert]:
        """Check all watched merchandise from SQLite for price changes."""
        if not self.config.get("enabled", True):
            return []

        token = await self._get_token()
        if not token:
            return []

        alerts = []
        from .. import database as db
        try:
            watched = await db.get_watchlist_items("merchandise")
        except Exception as e:
            logger.error(f"[ebay_merchandise] Failed to read watchlist: {e}")
            return alerts

        for item in watched:
            try:
                alert = await self._check_item(token, item)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"[ebay_merchandise] Error checking {item.get('symbol')}: {e}")

        self.last_check = datetime.now()
        return alerts

    async def _check_item(self, token: str, item: dict) -> MerchandiseAlert | None:
        meta = self._parse_notes(item.get("notes", ""))
        search_term = f"{meta.get('brand', '')} {meta.get('model', '')}".strip()
        # Fallback to symbol if brand/model empty
        if not search_term:
            search_term = item.get("symbol", "")
        if not search_term:
            return None

        current_price = await self._fetch_price(token, search_term, meta.get("variant"))
        if current_price is None:
            return None

        purchase_price = meta.get("purchase_price")
        symbol = item.get("symbol", search_term)

        # Store in cache
        try:
            from .. import database as db
            await db.set_market_cache(
                symbol=symbol,
                data_type="merchandise_price",
                raw_data={"price": current_price, "purchase_price": purchase_price},
                exchange="eBay",
            )
        except Exception:
            pass

        if purchase_price:
            # Check for price drop from purchase
            change_pct = (current_price - purchase_price) / purchase_price
            if change_pct < -self.threshold:
                return MerchandiseAlert(
                    source="ebay_merchandise",
                    alert_type="owned_price_drop",
                    symbol=symbol,
                    exchange="eBay",
                    brand=meta.get("brand", ""),
                    model=meta.get("model", ""),
                    variant=meta.get("variant", ""),
                    platforms={"eBay": current_price},
                    purchase_price=purchase_price,
                    purchase_currency=meta.get("purchase_currency", "CNY"),
                    current_price=current_price,
                    current_platform="eBay",
                    change_pct=change_pct,
                    details={"search_term": search_term},
                    priority="high" if change_pct < -0.10 else "normal",
                )

        return None

    def _extract_size_from_title(self, title: str) -> str | None:
        """Extract size from eBay item title. Returns normalized size or None."""
        import re
        title_lower = title.lower()

        # Common size patterns in eBay titles
        # "Size 10 D", "Size 10D", "Size 10", "10 D", "10D", "US 10"
        patterns = [
            r'size\s*(\d+(?:\.\d+)?\s*[a-z]?)',  # Size 10D, Size 10 D
            r'\b(\d+(?:\.\d+)?)\s*[a-z]\b',  # 10D, 9.5B
            r'\bus\s*(\d+(?:\.\d+)?)\b',  # US 10
        ]

        for pattern in patterns:
            match = re.search(pattern, title_lower)
            if match:
                return match.group(1).strip().upper()

        return None

    def _size_matches(self, title: str, target_variant: str) -> bool:
        """Check if item title matches target size/variant."""
        if not target_variant:
            return True  # No variant specified, accept all

        # Normalize variant (e.g., "7.5D" -> "7.5", "10D" -> "10")
        import re
        variant_clean = re.sub(r'[a-zA-Z]', '', target_variant).strip()
        variant_letter = re.sub(r'[\d.\s]', '', target_variant).strip().upper()

        title_size = self._extract_size_from_title(title)
        if not title_size:
            return False  # Can't determine size

        # Check if numbers match (allow some fuzzy matching)
        title_num = re.sub(r'[a-zA-Z]', '', title_size).strip()
        if variant_clean and title_num:
            try:
                if abs(float(title_num) - float(variant_clean)) < 0.5:
                    # Numbers match, check letter if present
                    if variant_letter:
                        title_letter = re.sub(r'[\d.\s]', '', title_size).strip().upper()
                        return variant_letter == title_letter or not title_letter
                    return True
            except ValueError:
                pass

        return False

    async def _fetch_price(self, token: str, search_term: str, variant: str = "") -> float | None:
        """Query eBay for items and return median price, filtering by size if variant specified."""
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            "Content-Type": "application/json",
        }

        params = {
            "q": search_term,
            "filter": "buyingOptions:FIXED_PRICE",
            "sort": "endDate:asc",
            "limit": "20",  # Get more results to filter
        }

        try:
            resp = requests.get(
                f"{self.BASE_URL}/item_summary/search",
                headers=headers,
                params=params,
                proxies=self._proxies,
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"[ebay_merchandise] API {resp.status_code}")
                return None

            items = resp.json().get("itemSummaries", [])
            if not items:
                return None

            # Filter by size if variant specified
            if variant:
                filtered_items = [
                    i for i in items
                    if self._size_matches(i.get("title", ""), variant)
                ]
                if filtered_items:
                    items = filtered_items
                    logger.info(f"[ebay_merchandise] Filtered to {len(items)} items matching size {variant}")

            prices = [float(i.get("price", {}).get("value", 0)) for i in items if i.get("price", {}).get("value")]
            if not prices:
                return None

            return sorted(prices)[len(prices) // 2]
        except Exception as e:
            logger.error(f"[ebay_merchandise] Request error: {e}")
            return None

    async def get_watchlist(self) -> list[dict]:
        """Return eBay merchandise watchlist items with current prices."""
        items = []
        from .. import database as db
        try:
            watched = await db.get_watchlist_items("merchandise")
        except Exception:
            return items

        for item in watched:
            meta = self._parse_notes(item.get("notes", ""))
            items.append({
                "symbol": item.get("symbol", ""),
                "brand": meta.get("brand", ""),
                "model": meta.get("model", ""),
                "variant": meta.get("variant", ""),
                "purchase_price": meta.get("purchase_price"),
                "purchase_currency": meta.get("purchase_currency", "CNY"),
                "exchange": "eBay",
            })
        return items