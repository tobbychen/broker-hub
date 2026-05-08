"""Binance crypto price monitor."""
import asyncio
import os
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
from ..config import get_market_data_config
from .. import database as db
from .base import BaseMonitor, Alert

# Default symbols when watchlist is empty in SQLite
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]


class BinanceMonitor(BaseMonitor):
    @property
    def name(self) -> str:
        return "binance"

    def __init__(self):
        super().__init__(get_market_data_config().get("binance", {}))
        self._client: Client | None = None
        self._proxies = self._detect_proxy()

    def _detect_proxy(self) -> dict | None:
        """Read HTTP_PROXY / HTTPS_PROXY from environment."""
        for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
            val = os.environ.get(var)
            if val:
                return {"http": val, "https": val}
        return None

    def _get_client(self) -> Client:
        if self._client is None:
            self._client = Client(
                api_key=self.config.get("api_key") or "",
                api_secret=self.config.get("secret") or "",
                requests_params={"proxies": self._proxies} if self._proxies else {},
            )
        return self._client

    def is_market_open(self) -> bool:
        return True  # Binance 24/7

    async def _get_symbols(self) -> list[str]:
        """Get symbols from SQLite watchlist, fallback to defaults."""
        try:
            items = await db.get_watchlist_items("crypto")
            if items:
                return [item["symbol"] + "USDT" for item in items]
        except Exception:
            pass
        return DEFAULT_SYMBOLS

    async def check(self) -> list[Alert]:
        if not self.config.get("enabled", True):
            return []

        alerts = []
        symbols = await self._get_symbols()
        for symbol in symbols:
            try:
                alert = await self._check_symbol(symbol)
                if alert:
                    alerts.append(alert)
            except Exception:
                continue
        self.last_check = datetime.now()
        return alerts

    async def _check_symbol(self, symbol: str) -> Alert | None:
        threshold = self.config.get("arbitrage_threshold", 0.005)
        try:
            client = self._get_client()
            ticker = client.get_symbol_ticker(symbol=symbol)
            price = float(ticker["price"])
            klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_5MINUTE, limit=10)
        except BinanceAPIException:
            return None

        if len(klines) < 2:
            return None

        prices = [float(k[4]) for k in klines]
        avg_price = sum(prices) / len(prices)
        change_pct = abs(price - avg_price) / avg_price

        # Write price to market_cache
        base_symbol = symbol.replace("USDT", "")
        try:
            await db.set_market_cache(
                symbol=base_symbol,
                data_type="latest_price",
                raw_data={"price": price, "avg_5min": avg_price},
                exchange="Binance",
            )
        except Exception:
            pass

        if change_pct > threshold:
            return Alert(
                source="binance",
                alert_type="arbitrage",
                symbol=base_symbol,
                exchange="Binance",
                details={
                    "current_price": price,
                    "avg_5min": avg_price,
                    "change_pct": round(change_pct * 100, 3),
                    "direction": "up" if price > avg_price else "down",
                },
                timestamp=datetime.now(),
                priority="high" if change_pct > 0.01 else "normal",
            )
        return None

    async def get_watchlist(self) -> list[dict]:
        """Return current prices for all tracked symbols."""
        items = []
        symbols = await self._get_symbols()
        for symbol in symbols:
            try:
                client = self._get_client()
                ticker = client.get_symbol_ticker(symbol=symbol)
                price = float(ticker["price"])
                klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=2)
                change_1h = 0.0
                if len(klines) >= 2:
                    change_1h = (price - float(klines[-2][4])) / float(klines[-2][4]) * 100
                items.append({
                    "symbol": symbol.replace("USDT", ""),
                    "price": price,
                    "change_1h_pct": round(change_1h, 2),
                    "exchange": "Binance",
                })
            except Exception:
                continue
        return items
