"""Binance crypto price monitor."""
import asyncio
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
from ..config import get_market_data_config
from .base import BaseMonitor, Alert


class BinanceMonitor(BaseMonitor):
    SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]

    @property
    def name(self) -> str:
        return "binance"

    def __init__(self):
        super().__init__(get_market_data_config().get("binance", {}))
        self._client: Client | None = None

    def _get_client(self) -> Client:
        if self._client is None:
            self._client = Client(
                api_key=self.config.get("api_key") or "",
                api_secret=self.config.get("secret") or "",
            )
        return self._client

    def is_market_open(self) -> bool:
        return True  # Binance 24/7

    async def check(self) -> list[Alert]:
        if not self.config.get("enabled", True):
            return []

        alerts = []
        for symbol in self.SYMBOLS:
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

        if change_pct > threshold:
            return Alert(
                source="binance",
                alert_type="arbitrage",
                symbol=symbol.replace("USDT", ""),
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
        for symbol in self.SYMBOLS:
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
