---
name: get_live_price
description: Fetch the current market price for a symbol from the market cache.
category: market
---

```python
import json

async def skill_fn(symbol: str, asset_class: str = "") -> str:
    """Return current price and daily change for a symbol."""
    from dashboard.backend.database import get_market_cache

    cache = await get_market_cache(symbol, "", "latest_price")
    if not cache:
        return f"未找到 {symbol} 的价格数据"

    raw_data = cache.get("raw_data", "{}")
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except Exception:
            pass

    if isinstance(raw_data, dict):
        price = raw_data.get("price")
        prev_close = raw_data.get("prev_close")
        fetched = cache.get("fetched_at")
        if price is None:
            return f"{symbol} 价格数据不完整"

        change_pct = ""
        if prev_close and prev_close > 0:
            chg = (price - prev_close) / prev_close * 100
            change_pct = f" ({chg:+.2f}%)"

        prev_close_str = f"{prev_close:.2f}" if prev_close else "N/A"
        return (
            f"{symbol}: {price:.2f}{change_pct} "
            f"(昨收: {prev_close_str}) "
            f"数据时间: {fetched}"
        )

    return f"{symbol} 价格数据格式错误"
```