"""OKX exchange monitor for crypto prices.

Uses OKX public API v5 — no API key needed.
Uses 'requests' for HTTP since httpx proxy support is unreliable on Windows.
Proxies through HTTP proxy if configured (via HTTP_PROXY env var).
"""
import asyncio
import logging
import os
import requests
from datetime import datetime
from ..config import get_market_data_config
from .. import database as db
from .base import BaseMonitor, Alert

logger = logging.getLogger(__name__)


class OKXMonitor(BaseMonitor):
    """Monitor crypto prices via OKX public API."""

    BASE_URL = "https://www.okx.com/api/v5/market/ticker"

    @property
    def name(self) -> str:
        return "okx"

    def __init__(self):
        from ..config import get_market_data_config
        cfg = get_market_data_config().get("okx", {})
        super().__init__(cfg)
        self.threshold = 0.03
        self._proxies = self._detect_proxy()

    def _detect_proxy(self) -> dict | None:
        for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
            val = os.environ.get(var)
            if val:
                return {"http": val, "https": val}
        return None

    def is_market_open(self) -> bool:
        return True  # OKX 24/7

    async def _get_symbols(self) -> list[str]:
        """Get symbols from SQLite watchlist (asset_class='crypto')."""
        try:
            items = await db.get_watchlist_items("crypto")
            if items:
                return [item["symbol"].upper() + "-USDT" for item in items]
        except Exception:
            pass
        return ["BTC-USDT", "ETH-USDT", "SOL-USDT", "BNB-USDT"]

    def _fetch_sync(self, symbol: str) -> dict | None:
        """Synchronous fetch using requests (runs in thread pool)."""
        try:
            r = requests.get(
                self.BASE_URL,
                params={"instId": symbol},
                proxies=self._proxies,
                timeout=15,
            )
            if r.status_code != 200:
                return None
            data = r.json()
            items = data.get("data", [])
            if not items:
                return None
            t = items[0]
            return {
                "last": float(t["last"]),
                "open_24h": float(t["open24h"]),
            }
        except Exception:
            return None

    async def check(self) -> list[Alert]:
        if not self.config.get("enabled", True):
            return []

        alerts = []
        symbols = await self._get_symbols()
        for sym in symbols:
            data = await asyncio.get_event_loop().run_in_executor(None, self._fetch_sync, sym)
            if not data:
                continue
            base = sym.replace("-USDT", "")
            last = data["last"]
            open_24h = data["open_24h"]
            change_pct = (last - open_24h) / open_24h * 100 if open_24h else 0

            try:
                await db.set_market_cache(
                    symbol=base,
                    data_type="latest_price",
                    raw_data={"price": last, "open24h": open_24h},
                    exchange="OKX",
                )
            except Exception:
                pass

            if abs(change_pct) > self.threshold * 100:
                alerts.append(Alert(
                    source="okx",
                    alert_type="price_spike",
                    symbol=base,
                    exchange="OKX",
                    details={
                        "current": last,
                        "open24h": open_24h,
                        "change_pct": round(change_pct, 2),
                    },
                    timestamp=datetime.now(),
                    priority="high" if abs(change_pct) > 5 else "normal",
                ))

        self.last_check = datetime.now()
        return alerts

    async def get_watchlist(self) -> list[dict]:
        """Return current prices for all OKX-tracked symbols."""
        items = []
        symbols = await self._get_symbols()
        for sym in symbols:
            data = await asyncio.get_event_loop().run_in_executor(None, self._fetch_sync, sym)
            if not data:
                continue
            base = sym.replace("-USDT", "")
            last = data["last"]
            open_24h = data["open_24h"]
            change = (last - open_24h) / open_24h * 100 if open_24h else 0
            items.append({
                "symbol": base,
                "price": last,
                "change_pct": round(change, 2),
                "exchange": "OKX",
            })
        return items
