"""Skill tools for the Telegram chat agent — add/remove/list watchlist items."""
import re
from typing import Literal
from langchain_core.tools import tool
from dashboard.backend.database import upsert_watchlist_item, delete_watchlist_item, get_watchlist_items

# Lazy import to avoid circular issues
_agents_path = None


@tool
async def add_stock_watchlist(symbol: str, notes: str = "") -> str:
    """Add a Chinese A-share stock to the monitoring watchlist.

    Args:
        symbol: 6-digit A-share code (e.g. '600519' for 贵州茅台)
        notes: optional note about this stock"""
    if not symbol.isdigit() or len(symbol) != 6:
        return f"股票代码格式错误，需要6位数字代码，当前: {symbol}"
    await upsert_watchlist_item("stock", symbol, "SSE/SZSE", notes)
    return f"✅ 已添加股票监控: {symbol} — AKShare将每60秒检查价格变动"


@tool
async def add_crypto_watchlist(symbol: str, exchange: Literal["OKX", "Binance"] = "OKX", notes: str = "") -> str:
    """Add a cryptocurrency to the monitoring watchlist.

    Args:
        symbol: crypto base code (e.g. 'BTC', 'ETH', 'SOL')
        exchange: 'OKX' or 'Binance' — which API to use for price checks"""
    await upsert_watchlist_item("crypto", symbol.upper(), exchange, notes)
    return f"✅ 已添加加密货币监控: {symbol.upper()} ({exchange}) — 将检查24h价格变动"


@tool
async def add_sports_card_watchlist(
    name: str,
    set_name: str,
    year: str,
    category: str = "",
    min_grade: str = "",
    last_price: str = "",
) -> str:
    """Add a sports card to the eBay monitoring watchlist.

    Args:
        name: card name (e.g. 'Charizard', 'Black Lotus')
        set_name: set name (e.g. 'Base Set', 'Unlimited')
        year: card year (e.g. '1999')
        category: card category (e.g. 'pokemon', 'magic', 'basketball')
        min_grade: minimum grade filter (e.g. 'PSA 9', 'BGS 10')
        last_price: last known sold price (e.g. '5000')"""
    notes = f"{name}|{set_name}|{year}|{category}|{min_grade}|{last_price}"
    await upsert_watchlist_item("sports_card", name, "eBay", notes)
    return f"✅ 已添加球星卡监控: {name} ({set_name}, {year}) — eBay将监控价格变动"


@tool
async def search_and_add_stock(name: str) -> str:
    """Search for a Chinese A-share stock by company name and add it to monitoring.

    Args:
        name: company name in Chinese (e.g. '贵州茅台', '平安银行', '阿里巴巴')
    Returns:
        confirmation with stock code if found, or notice that company is not listed"""
    import akshare as ak
    try:
        df = ak.stock_info_a_code_name()
    except Exception as e:
        return f"查询失败: {e}"

    # Normalize search term
    name_clean = name.strip().replace(" ", "").replace("（", "(").replace("）", ")")
    # Case-insensitive partial match
    matches = df[df["name"].str.replace(" ", "").str.contains(name_clean, na=False, case=False)]

    if matches.empty:
        return f"未找到「{name}」相关上市股票，该公司可能未上市或不在A股范围内"

    # Return top 3 matches for user to pick if multiple
    if len(matches) > 3:
        top = matches.head(3)
        names = "、".join([f"{r['name']}({r['code']})" for _, r in top.iterrows()])
        return f"找到多只相关股票：{names}，请提供完整名称或直接说「添加 {top.iloc[0]['code']}」"

    # Single match — add to watchlist
    row = matches.iloc[0]
    code = str(row["code"])
    full_name = row["name"]
    await upsert_watchlist_item("stock", code, "SSE/SZSE", full_name)
    return f"✅ 已添加 {full_name}({code}) 到A股监控 — AKShare将每60秒检查价格变动"


@tool
async def remove_from_watchlist(symbol: str, asset_class: Literal["stock", "crypto", "sports_card"]) -> str:
    """Remove an asset from the monitoring watchlist.

    Args:
        symbol: the symbol to remove (e.g. '600519', 'BTC')
        asset_class: 'stock', 'crypto', or 'sports_card'"""
    items = await get_watchlist_items(asset_class)
    item = next((i for i in items if i["symbol"] == symbol), None)
    if not item:
        return f"未找到 {symbol} 在 {asset_class} 监控列表中"
    await delete_watchlist_item(item["id"])
    return f"✅ 已移除监控: {symbol} ({asset_class})"


@tool
async def analyze_watchlist_asset(symbol: str, asset_class: Literal["stock", "crypto", "sports_card"]) -> str:
    """Analyze a specific asset from the watchlist using the Research Analyst agent.

    Args:
        symbol: the asset symbol to analyze (e.g. '600519', 'BTC', 'Charizard')
        asset_class: 'stock', 'crypto', or 'sports_card'"""
    items = await get_watchlist_items(asset_class)
    item = next((i for i in items if i["symbol"] == symbol), None)
    if not item:
        return f"未找到 {symbol} 在 {asset_class} 监控列表中"

    # Build alert-like dict for research agent
    exchange = item.get("exchange", "")
    alert = {
        "source": exchange,
        "alert_type": asset_class,
        "symbol": symbol,
        "exchange": exchange,
        "details": item.get("notes", ""),
    }

    # Import research agent lazily
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from agents.research_analyst.agent import research_opportunity

    # Get portfolio context
    from agents.dispatcher.tools import lookup_portfolio
    try:
        portfolio_str = await lookup_portfolio.ainvoke({})
    except Exception:
        portfolio_str = "无法获取投资组合信息"

    result = await research_opportunity(alert, portfolio_str)
    return result


@tool
async def list_my_watchlist() -> str:
    """List all assets currently being monitored, grouped by asset class."""
    items = await get_watchlist_items()
    if not items:
        return "📋 监控列表为空。告诉我添加要监控的资产，例如：\n- 监控股票 600519\n- 跟踪 BTC\n- 添加 Charizard 球星卡"

    groups: dict[str, list] = {}
    for it in items:
        groups.setdefault(it["asset_class"], []).append(it)

    lines = ["📋 当前监控列表:"]
    for cls, vals in sorted(groups.items()):
        label = {"stock": "A股", "crypto": "加密货币", "sports_card": "球星卡"}.get(cls, cls)
        lines.append(f"\n【{label}】")
        for v in vals:
            note = f" — {v['notes']}" if v.get("notes") else ""
            lines.append(f"  • {v['symbol']}{note}")
    return "\n".join(lines)
