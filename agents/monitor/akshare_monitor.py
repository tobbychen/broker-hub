"""AKShare-based monitor for A-shares and China futures."""
import asyncio
import akshare as ak
from datetime import datetime
from ..config import get_market_data_config
from .base import BaseMonitor, Alert


class AKShareMonitor(BaseMonitor):
    SYMBOLS = ["000001", "399001", "399006"]

    @property
    def name(self) -> str:
        return "akshare"

    def __init__(self):
        super().__init__(get_market_data_config().get("akshare", {}))
        self.threshold = 0.03

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

        try:
            alerts = await self._check_indices()
            self.last_check = datetime.now()
            return alerts
        except Exception:
            return []

    async def _check_indices(self) -> list[Alert]:
        alerts = []
        try:
            df = ak.stock_zh_index_spot_em()
            for _, row in df.iterrows():
                code = str(row.get("代码", ""))
                if code not in self.SYMBOLS:
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
