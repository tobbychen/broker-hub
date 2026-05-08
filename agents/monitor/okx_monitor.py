"""OKX exchange monitor for crypto prices.

Uses OKX public API v5 — no API key needed.
Proxies through HTTP proxy if configured (via HTTP_PROXY env var).
"""
import asyncio
import logging
import os
import httpx
from datetime import datetime
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

    def _detect_proxy(self) -> str | None:
        """Read HTTP_PROXY from environment. Returns proxy URL string."""
        for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
            val = os.environ.get(var)
            if val:
                return val
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

    async def check(self) -> list[Alert]:
        if not self.config.get("enabled", True):
            return []

        alerts = []
        symbols = await self._get_symbols()
        for sym in symbols:
            try:
                alert = await self._check_symbol(sym)
                if alert:
                    alerts.append(alert)
            except Exception:
                continue

        self.last_check = datetime.now()
        return alerts

    async def _check_symbol(self, symbol: str) -> Alert | None:
        """Fetch ticker and alert on large deviation from 24h open."""
        base = symbol.replace("-USDT", "")
        try:
            async with httpx.AsyncClient(proxy=self._proxies, timeout=15) as client:
                r = await client.get(self.BASE_URL, params={"instId": symbol})
                if r.status_code != 200:
                    return None
                data = r.json()
                items = data.get("data", [])
                if not items:
                    return None
                t = items[0]
                last = float(t["last"])
                open_24h = float(t["open24h"])
                change_pct = (last - open_24h) / open_24h * 100
        except Exception:
            return None

        # Write to market_cache
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
            return Alert(
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
            )
        return None

    async def get_watchlist(self) -> list[dict]:
        """Return current prices for all OKX-tracked symbols."""
        items = []
        symbols = await self._get_symbols()
        for sym in symbols:
            base = sym.replace("-USDT", "")
            try:
                async with httpx.AsyncClient(proxy=self._proxies, timeout=15) as client:
                    r = await client.get(self.BASE_URL, params={"instId": sym})
                    if r.status_code != 200:
                        continue
                    data = r.json()
                    t = data.get("data", [{}])[0]
                    last = float(t.get("last", 0))
                    open_24h = float(t.get("open24h", 0))
                    change = 0.0
                    if open_24h:
                        change = (last - open_24h) / open_24h * 100
                    items.append({
                        "symbol": base,
                        "price": last,
                        "change_pct": round(change, 2),
                        "exchange": "OKX",
                    })
            except Exception:
                continue
        return items
