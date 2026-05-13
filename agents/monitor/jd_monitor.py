"""JD (Jingdong) Open Platform monitor for merchandise prices.

Uses JD Open Platform API for product search and pricing.
"""
import hashlib
import json
import logging
import os
import time
import requests
from datetime import datetime
from ..config import get_market_data_config
from .base import BaseMonitor, MerchandiseAlert

logger = logging.getLogger(__name__)


class JDMonitor(BaseMonitor):
    """Monitor branded merchandise prices via JD Open Platform."""

    BASE_URL = "https://router.jd.com/api"

    @property
    def name(self) -> str:
        return "jd"

    def __init__(self):
        config = get_market_data_config().get("jd", {})
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

    def _generate_sign(self, params: dict, app_secret: str) -> str:
        """Generate JD API sign using MD5."""
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        sign_str = app_secret + "".join(f"{k}{v}" for k, v in sorted_params) + app_secret
        return hashlib.md5(sign_str.encode()).hexdigest().upper()

    def _parse_notes(self, notes: str) -> dict:
        """Parse pipe-separated merchandise metadata.

        Format: Brand|Model|Variant|PurchasePrice|PurchaseCurrency
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
        if not self.config.get("enabled", True):
            return []

        app_key = self.config.get("app_key")
        app_secret = self.config.get("app_secret")

        if not app_key or not app_secret:
            logger.warning("[jd] Missing credentials")
            return []

        alerts = []
        from .. import database as db
        try:
            watched = await db.get_watchlist_items("merchandise")
        except Exception as e:
            logger.error(f"[jd] Failed to read watchlist: {e}")
            return alerts

        for item in watched:
            try:
                alert = await self._check_item(app_key, app_secret, item)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"[jd] Error checking {item.get('symbol')}: {e}")

        self.last_check = datetime.now()
        return alerts

    async def _check_item(self, app_key: str, app_secret: str, item: dict) -> MerchandiseAlert | None:
        meta = self._parse_notes(item.get("notes", ""))
        search_term = f"{meta.get('brand', '')} {meta.get('model', '')}".strip()
        if not search_term:
            return None

        current_price = await self._fetch_price(app_key, app_secret, search_term)
        if current_price is None:
            return None

        purchase_price = meta.get("purchase_price")
        symbol = item.get("symbol", search_term)

        if purchase_price:
            change_pct = (current_price - purchase_price) / purchase_price
            if change_pct < -self.threshold:
                return MerchandiseAlert(
                    source="jd",
                    alert_type="owned_price_drop",
                    symbol=symbol,
                    exchange="JD",
                    brand=meta.get("brand", ""),
                    model=meta.get("model", ""),
                    variant=meta.get("variant", ""),
                    platforms={"JD": current_price},
                    purchase_price=purchase_price,
                    purchase_currency=meta.get("purchase_currency", "CNY"),
                    current_price=current_price,
                    current_platform="JD",
                    change_pct=change_pct,
                    details={"search_term": search_term},
                    priority="high" if change_pct < -0.10 else "normal",
                )

        return None

    async def _fetch_price(self, app_key: str, app_secret: str, search_term: str) -> float | None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        params = {
            "app_key": app_key,
            "v": "1.0",
            "method": "jd.union.open.goods.query",
            "timestamp": timestamp,
            "format": "json",
            "sign_method": "md5",
            "360buy_param_json": json.dumps({
                "goodsReq": {
                    "keyword": search_term,
                    "page_size": 10,
                }
            }),
        }

        params["sign"] = self._generate_sign(params, app_secret)

        try:
            resp = requests.get(
                self.BASE_URL,
                params=params,
                proxies=self._proxies,
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"[jd] API {resp.status_code}")
                return None

            data = resp.json()
            if data.get("jd_union_open_goods_query_response", {}).get("code") != "0":
                logger.warning(f"[jd] API error: {data}")
                return None

            goods_list = data.get("jd_union_open_goods_query_response", {}).get("goodsList", [])
            if not goods_list:
                return None

            prices = []
            for item in goods_list:
                price_info = item.get("priceInfo", {})
                lowest_price = price_info.get("lowestPrice")
                if lowest_price:
                    try:
                        prices.append(float(lowest_price))
                    except (ValueError, TypeError):
                        pass

            if not prices:
                return None

            return min(prices)
        except Exception as e:
            logger.error(f"[jd] Request error: {e}")
            return None

    async def get_watchlist(self) -> list[dict]:
        """Return JD merchandise watchlist items."""
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
                "exchange": "JD",
            })
        return items