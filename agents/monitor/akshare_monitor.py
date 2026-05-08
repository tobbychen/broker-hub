"""AKShare-based monitor for A-shares and China futures."""
import asyncio
import akshare as ak
from datetime import datetime
from ..config import get_market_data_config
from .base import BaseMonitor, Alert


class AKShareMonitor(BaseMonitor):
    # Index codes to track
    INDEX_SYMBOLS = ["000001", "399001", "399006"]

    @property
    def name(self) -> str:
        return "akshare"

    def __init__(self):
        super().__init__(get_market_data_config().get("akshare", {}))
        self.threshold = 0.03
        # Individual stocks to monitor — configured in api_providers.yaml
        self.stocks = self.config.get("stocks", [])

    def is_market_open(self) -> bool:
        now = datetime.now()
        if now.weekday() >= 5:
            return False
        total_minutes = now.hour * 60 + now.minute
        return (9 * 60 + 30) <= total_minutes <= (15 * 60)

    async def check(self) -> list[Alert]:
        if not self.config.get("enabled", True):
            return []
        if not self.is_market_open():
            return []

        alerts = []
        try:
            index_alerts = await self._check_indices()
            alerts.extend(index_alerts)
        except Exception:
            pass

        try:
            stock_alerts = await self._check_stocks()
            alerts.extend(stock_alerts)
        except Exception:
            pass

        self.last_check = datetime.now()
        return alerts

    async def _check_indices(self) -> list[Alert]:
        alerts = []
        try:
            df = ak.stock_zh_index_spot_em()
            for _, row in df.iterrows():
                code = str(row.get("代码", ""))
                if code not in self.INDEX_SYMBOLS:
                    continue
                change_pct = float(row.get("涨跌幅", 0))
                if abs(change_pct) > self.threshold * 100:
                    alerts.append(Alert(
                        source="akshare",
                        alert_type="price_spike",
                        symbol=code,
                        exchange="SSE/SZSE",
                        details={
                            "name": row.get("名称", ""),
                            "current": float(row.get("最新价", 0)),
                            "change_pct": change_pct,
                        },
                        timestamp=datetime.now(),
                        priority="high" if abs(change_pct) > 5 else "normal",
                    ))
        except Exception:
            pass
        return alerts

    async def _check_stocks(self) -> list[Alert]:
        """Check individual stocks for price anomalies."""
        alerts = []
        stocks = self.stocks or []

        if not stocks:
            return alerts

        try:
            # Fetch all A-share spot data (one API call for all stocks)
            df = ak.stock_zh_a_spot_em()
            symbol_map = {str(row["代码"]): row for _, row in df.iterrows()}
        except Exception:
            return alerts

        for stock in stocks:
            code = stock.get("code")
            last_price = stock.get("last_price")
            threshold = stock.get("threshold", self.threshold)

            if not code:
                continue

            try:
                row = symbol_map.get(code)
                if row is None:
                    continue

                current_price = float(row.get("最新价", 0))
                change_pct = float(row.get("涨跌幅", 0))

                # Alert on large % move
                if abs(change_pct) > threshold * 100:
                    alerts.append(Alert(
                        source="akshare",
                        alert_type="price_spike",
                        symbol=code,
                        exchange=row.get("交易所", "SSE/SZSE"),
                        details={
                            "name": row.get("名称", code),
                            "current": current_price,
                            "change_pct": change_pct,
                        },
                        timestamp=datetime.now(),
                        priority="high" if abs(change_pct) > 5 else "normal",
                    ))

                # Alert on absolute price change from last recorded
                if last_price and current_price != last_price:
                    change_pct_abs = abs(current_price - last_price) / last_price
                    if change_pct_abs > threshold:
                        alerts.append(Alert(
                            source="akshare",
                            alert_type="price_move",
                            symbol=code,
                            exchange=row.get("交易所", "SSE/SZSE"),
                            details={
                                "name": row.get("名称", code),
                                "current_price": current_price,
                                "previous_price": last_price,
                                "change_pct": round(change_pct_abs * 100, 2),
                            },
                            timestamp=datetime.now(),
                            priority="normal",
                        ))

            except (ValueError, TypeError, KeyError):
                continue

        return alerts
