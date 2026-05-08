"""AKShare-based monitor for A-shares and China futures."""
import asyncio
import akshare as ak
from datetime import datetime
from ..config import get_market_data_config
from .. import database as db
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
        """Check individual stocks from SQLite watchlist.

        Reads from watchlist table (asset_class='stock'), fetches daily bars,
        alerts on % move vs yesterday close, writes prices to market_cache.
        """
        alerts = []

        try:
            stocks = await db.get_watchlist_items("stock")
        except Exception:
            return alerts

        if not stocks:
            return alerts

        today = datetime.now().strftime("%Y%m%d")
        yesterday_ts = datetime.now().timestamp() - 86400
        yesterday_str = datetime.fromtimestamp(yesterday_ts).strftime("%Y%m%d")

        for stock in stocks:
            code = stock.get("symbol")
            name = stock.get("notes", code)  # notes stores the company name
            if not code:
                continue

            try:
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    adjust="qfq",
                    start_date=yesterday_str,
                    end_date=today,
                )
                if df is None or df.empty:
                    continue

                today_bar = df.iloc[-1]
                prev_bar = df.iloc[-2] if len(df) >= 2 else None

                current_price = float(today_bar["收盘"])
                prev_close = float(prev_bar["收盘"]) if prev_bar is not None else None

                # Write price to market_cache
                try:
                    await db.set_market_cache(
                        symbol=code,
                        data_type="latest_price",
                        raw_data={"price": current_price, "prev_close": prev_close},
                        exchange="SSE/SZSE",
                    )
                except Exception:
                    pass

                # Alert on % move vs yesterday close
                if prev_close and prev_close > 0:
                    change_pct = (current_price - prev_close) / prev_close * 100
                    if abs(change_pct) > self.threshold * 100:
                        alerts.append(Alert(
                            source="akshare",
                            alert_type="price_spike",
                            symbol=code,
                            exchange="SSE/SZSE",
                            details={
                                "name": name,
                                "current": current_price,
                                "prev_close": prev_close,
                                "change_pct": round(change_pct, 2),
                            },
                            timestamp=datetime.now(),
                            priority="high" if abs(change_pct) > 5 else "normal",
                        ))

            except Exception:
                continue

        return alerts

    async def get_watchlist(self) -> list[dict]:
        """Return current prices for all stocks in SQLite watchlist."""
        items = []
        try:
            stocks = await db.get_watchlist_items("stock")
        except Exception:
            return items

        if not stocks:
            return items

        today = datetime.now().strftime("%Y%m%d")
        yesterday_ts = datetime.now().timestamp() - 86400
        yesterday_str = datetime.fromtimestamp(yesterday_ts).strftime("%Y%m%d")

        for stock in stocks:
            code = stock.get("symbol")
            name = stock.get("notes", code)
            if not code:
                continue
            try:
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    adjust="qfq",
                    start_date=yesterday_str,
                    end_date=today,
                )
                if df is None or df.empty:
                    continue
                today_bar = df.iloc[-1]
                prev_bar = df.iloc[-2] if len(df) >= 2 else None
                current_price = float(today_bar["收盘"])
                prev_close = float(prev_bar["收盘"]) if prev_bar is not None else None
                change_pct = 0.0
                if prev_close and prev_close > 0:
                    change_pct = (current_price - prev_close) / prev_close * 100
                items.append({
                    "symbol": code,
                    "name": name,
                    "price": current_price,
                    "prev_close": prev_close,
                    "change_pct": round(change_pct, 2),
                    "exchange": "SSE/SZSE",
                })
            except Exception:
                continue
        return items
