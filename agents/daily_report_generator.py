"""Daily report generation — combines market data into morning brief."""
import asyncio
from datetime import date, datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dashboard.backend.database import save_daily_report
from agents.monitor.binance_monitor import BinanceMonitor
from agents.monitor.akshare_monitor import AKShareMonitor
from agents.monitor.yfinance_monitor import YFinanceMonitor
from agents.config import get_llm_config

DAILY_REPORT_PROMPT = """你是一个投资早间简报生成器。请根据以下市场数据，生成一份简洁的中文早间简报：

今日日期: {date}
中国市场行情: {china_data}
加密市场行情: {crypto_data}
美国市场: {us_data}

请按以下格式生成简报：

## 隔夜行情
- 简要列出各市场涨跌

## 重要事件
- 列出可能影响今日市场的宏观/政策/行业事件

## 投资窗口
- 基于当前数据分析可能的机会（保守，语气谨慎）

要求：
- 简洁，每节不超过5条
- 用中文
- 投资窗口给出理由，不给出具体买卖价格
"""


async def fetch_overnight_data() -> dict:
    """Fetch current market data from all monitors."""
    bnb = BinanceMonitor()
    aks = AKShareMonitor()
    yfc = YFinanceMonitor()

    data = {"crypto": [], "china": [], "us": []}

    try:
        alerts = await bnb.check()
        data["crypto"] = [f"{a.symbol}: ${a.details.get('current_price', 0):.0f}" for a in alerts[:3]]
    except Exception:
        pass

    try:
        alerts = await aks.check()
        data["china"] = [f"{a.details.get('name', a.symbol)}: {a.details.get('change_pct', 0):+.2f}%" for a in alerts[:3]]
    except Exception:
        pass

    try:
        alerts = await yfc.check()
        data["us"] = [f"{a.symbol}: {a.details.get('change_pct', 0):+.2f}%" for a in alerts[:3]]
    except Exception:
        pass

    return data


async def generate_daily_report() -> dict:
    """Generate and save today's daily report."""
    cfg = get_llm_config()
    primary = cfg.get("primary", {})

    market_data = await fetch_overnight_data()
    report_date = date.today()

    crypto_str = ", ".join(market_data["crypto"][:3]) or "无明显波动"
    china_str = ", ".join(market_data["china"][:3]) or "无明显波动"
    us_str = ", ".join(market_data["us"][:3]) or "市场数据获取失败"

    prompt = DAILY_REPORT_PROMPT.format(
        date=report_date.isoformat(),
        china_data=china_str,
        crypto_data=crypto_str,
        us_data=us_str,
    )

    try:
        llm = ChatOpenAI(
            api_key=primary.get("api_key", ""),
            model=primary.get("model", "auto"),
            base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
            temperature=0.3,
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        report_text = response.content
    except Exception as e:
        report_text = f"简报生成失败: {e}"

    sections = {"overnight_summary": "", "critical_events": "", "investment_windows": ""}
    current = "overnight_summary"
    for line in report_text.split("\n"):
        stripped = line.strip()
        if "重要事件" in line or "⚠️" in line:
            current = "critical_events"
        elif "投资窗口" in line or "🎯" in line:
            current = "investment_windows"
        elif stripped.startswith("##"):
            continue
        elif stripped:
            sections[current] += stripped + "\n"

    await save_daily_report(
        report_date=report_date,
        overnight_summary=sections["overnight_summary"].strip(),
        critical_events=sections["critical_events"].strip(),
        investment_windows=sections["investment_windows"].strip(),
    )

    return sections


async def scheduled_daily_report():
    """Run daily at 08:00 Shanghai time."""
    import time as time_module
    while True:
        now = datetime.now()
        target = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if now >= target:
            target = target.replace(day=now.day + 1)
        delay = (target - now).total_seconds()
        await asyncio.sleep(delay)
        try:
            await generate_daily_report()
        except Exception as e:
            import logging
            logging.error(f"Daily report generation failed: {e}")


if __name__ == "__main__":
    asyncio.run(generate_daily_report())
