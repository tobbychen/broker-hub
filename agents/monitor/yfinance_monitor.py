"""Yahoo Finance monitor for US stocks and ETFs."""
import asyncio
import yfinance as yf
from datetime import datetime
from ..config import get_market_data_config
from .base import BaseMonitor, Alert


class YFinanceMonitor(BaseMonitor):
    SYMBOLS = ["SPY", "QQQ", "BTC-USD", "ETH-USD"]

    @property
    def name(self) -> str:
        return "yfinance"

    def __init__(self):
        super().__init__(get_market_data_config().get("yfinance", {}))
        self.threshold = 0.02

    def is_market_open(self) -> bool:
        now = datetime.utcnow()
        if now.weekday() >= 5:
            return False
        total_minutes = now.hour * 60 + now.minute
        return (13 * 60 + 30) <= total_minutes <= (20 * 60)

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
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5m")
            if hist.empty or len(hist) < 2:
                return None
            latest = hist["Close"].iloc[-1]
            avg = hist["Close"].mean()
            change_pct = abs(latest - avg) / avg
            if change_pct > self.threshold:
                return Alert(
                    source="yfinance",
                    alert_type="price_anomaly",
                    symbol=symbol,
                    exchange="NASDAQ/NYSE",
                    details={
                        "current_price": round(latest, 4),
                        "avg_price": round(avg, 4),
                        "change_pct": round(change_pct * 100, 2),
                    },
                    timestamp=datetime.now(),
                    priority="normal",
                )
        except Exception:
            pass
        return None
