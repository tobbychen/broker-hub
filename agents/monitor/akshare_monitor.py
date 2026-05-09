"""A-share monitor using Sina Finance API.

Sina Finance works on Windows where eastmoney push2 API fails due to
SSL renegotiation issues with curl+Schannel. We use curl subprocess
with --noproxy to bypass the WinHTTP system proxy.
"""
import asyncio
import json
import subprocess
from datetime import datetime, timedelta
from ..config import get_market_data_config
from .. import database as db
from .base import BaseMonitor, Alert


def _curl_get(url: str, timeout: int = 10) -> str | None:
    """Fetch text via curl subprocess, bypassing WinHTTP proxy on Windows."""
    cmd = [
        "curl", "-s", "--noproxy", "*", "--max-time", str(timeout),
        "-H", "Referer: https://finance.sina.com.cn",
        "-H", "User-Agent: Mozilla/5.0",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except Exception:
        pass
    return None


def _parse_sina_quote(raw: str) -> dict | None:
    """Parse a Sina Finance hq_str line into a dict.

    raw example: '贵州茅台,1371.660,1371.050,1372.990,1382.770,1370.000,
                 1372.600,1372.990,...,2026-05-08,15:00:01,00,'
    Fields: name, open, prev_close, current, high, low, ...
    """
    parts = raw.strip().strip('"').split(",")
    if len(parts) < 10:
        return None
    try:
        return {
            "name": parts[0],
            "open": float(parts[1]),
            "prev_close": float(parts[2]),
            "current": float(parts[3]),
            "high": float(parts[4]),
            "low": float(parts[5]),
            "date": parts[30] if len(parts) > 30 else "",
            "time": parts[31] if len(parts) > 31 else "",
        }
    except (ValueError, IndexError):
        return None


def _build_sina_url(symbols: list[str]) -> str:
    """Build a Sina batch quote URL for given symbols.

    symbols: list of 'sh600519', 'sz399001' etc.
    """
    prefix = ",".join(symbols)
    return f"https://hq.sinajs.cn/list={prefix}"


class AKShareMonitor(BaseMonitor):
    INDEX_SYMBOLS = [
        ("000001", "sh"),
        ("399001", "sz"),
        ("399006", "sz"),
    ]

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

    def _parse_quotes(self, text: str) -> dict[str, dict]:
        """Parse Sina multi-line response into {symbol: quote_dict}."""
        result = {}
        for line in text.splitlines():
            if "hq_str_" not in line or "=" not in line:
                continue
            try:
                sym_part = line.split("hq_str_")[1].split("=")[0].strip()
                raw = line.split('"', 1)[1].split('"', 1)[0]
                quote = _parse_sina_quote(raw)
                if quote:
                    result[sym_part] = quote
            except Exception:
                continue
        return result

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
            symbols = [f"{prefix}{code}" for code, prefix in self.INDEX_SYMBOLS]
            url = _build_sina_url(symbols)
            text = _curl_get(url, timeout=8)
            if not text:
                return alerts
            quotes = self._parse_quotes(text)
            for code, prefix in self.INDEX_SYMBOLS:
                sym = f"{prefix}{code}"
                if sym not in quotes:
                    continue
                q = quotes[sym]
                current = q["current"]
                prev = q["prev_close"]
                if prev <= 0:
                    continue
                change_pct = (current - prev) / prev * 100
                if abs(change_pct) > self.threshold * 100:
                    alerts.append(Alert(
                        source="akshare",
                        alert_type="price_spike",
                        symbol=code,
                        exchange="SSE/SZSE",
                        details={"name": q["name"], "current": current, "change_pct": round(change_pct, 2)},
                        timestamp=datetime.now(),
                        priority="high" if abs(change_pct) > 5 else "normal",
                    ))
        except Exception:
            pass
        return alerts

    async def _check_stocks(self) -> list[Alert]:
        alerts = []
        try:
            stocks = await db.get_watchlist_items("stock")
        except Exception:
            return alerts
        if not stocks:
            return alerts

        # Build Sina symbols (sh for SSE, sz for SZSE)
        sina_symbols = []
        for s in stocks:
            code = s.get("symbol", "")
            if code.startswith(("6",)):
                sina_symbols.append(f"sh{code}")
            elif code.startswith(("0", "3")):
                sina_symbols.append(f"sz{code}")

        if not sina_symbols:
            return alerts

        url = _build_sina_url(sina_symbols)
        text = _curl_get(url, timeout=8)
        if not text:
            return alerts

        quotes = self._parse_quotes(text)
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Map back to stock entries
        stock_map = {s.get("symbol"): s for s in stocks}

        for stock in stocks:
            code = stock.get("symbol", "")
            prefix = "sh" if code.startswith("6") else "sz"
            sym = f"{prefix}{code}"

            if sym not in quotes:
                continue

            q = quotes[sym]
            current = q["current"]
            prev = q["prev_close"]

            try:
                await db.set_market_cache(
                    symbol=code,
                    data_type="latest_price",
                    raw_data={
                        "price": current,
                        "prev_close": prev,
                        "open": q["open"],
                        "high": q["high"],
                        "low": q["low"],
                        "date": q["date"],
                        "time": q["time"],
                    },
                    exchange="SSE/SZSE",
                )
            except Exception:
                pass

            if prev > 0:
                change_pct = (current - prev) / prev * 100
                if abs(change_pct) > self.threshold * 100:
                    alerts.append(Alert(
                        source="akshare",
                        alert_type="price_spike",
                        symbol=code,
                        exchange="SSE/SZSE",
                        details={
                            "name": stock.get("notes", code),
                            "current": current,
                            "prev_close": prev,
                            "change_pct": round(change_pct, 2),
                        },
                        timestamp=datetime.now(),
                        priority="high" if abs(change_pct) > 5 else "normal",
                    ))
        return alerts

    async def get_watchlist(self) -> list[dict]:
        items = []
        try:
            stocks = await db.get_watchlist_items("stock")
        except Exception:
            return items
        if not stocks:
            return items

        sina_symbols = []
        for s in stocks:
            code = s.get("symbol", "")
            if code.startswith(("6",)):
                sina_symbols.append(f"sh{code}")
            elif code.startswith(("0", "3")):
                sina_symbols.append(f"sz{code}")

        if not sina_symbols:
            return items

        url = _build_sina_url(sina_symbols)
        text = _curl_get(url, timeout=8)
        if not text:
            return items

        quotes = self._parse_quotes(text)

        for stock in stocks:
            code = stock.get("symbol", "")
            name = stock.get("notes", code)
            prefix = "sh" if code.startswith("6") else "sz"
            sym = f"{prefix}{code}"

            if sym not in quotes:
                continue

            q = quotes[sym]
            current = q["current"]
            prev = q["prev_close"]
            change_pct = (current - prev) / prev * 100 if prev > 0 else 0.0

            items.append({
                "symbol": code,
                "name": name,
                "price": current,
                "prev_close": prev,
                "open": q["open"],
                "high": q["high"],
                "low": q["low"],
                "change_pct": round(change_pct, 2),
                "exchange": "SSE/SZSE",
            })
        return items