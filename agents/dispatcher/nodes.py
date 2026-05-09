"""LangGraph nodes for the Dispatcher agent."""
import json
import re
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from .prompts import DISPATCHER_SYSTEM, format_alert_for_dispatcher
from .tools import (
    lookup_portfolio,
    submit_decision,
    lookup_pending_decisions,
    get_live_price,
    research_asset,
    parse_research_and_submit,
)


def _bind_tools(llm):
    """Bind all dispatcher skills to the LLM."""
    return llm.bind_tools([
        lookup_portfolio,
        lookup_pending_decisions,
        get_live_price,
        research_asset,
        parse_research_and_submit,
        submit_decision,
    ])


async def monitor_handler(state: dict, llm) -> dict:
    """Handle incoming market alerts — determine if any are investment-relevant."""
    alerts = state.get("alerts", [])
    if not alerts:
        return {"alerts": [], "decisions": state.get("decisions", [])}

    bound_llm = _bind_tools(llm)

    # Ask LLM to assess each alert using its tools
    alert_summaries = [format_alert_for_dispatcher(a) for a in alerts]
    portfolio_str = await lookup_portfolio.ainvoke({})

    prompt = f"""以下市场警报已触发：

{chr(10).join(alert_summaries)}

当前投资组合：
{portfolio_str}

分析这些警报是否与投资相关。如相关，请用中文解释原因并给出判断：相关/不相关。

仅输出你的分析结论。"""

    response = await bound_llm.ainvoke([HumanMessage(content=prompt)])
    content = response.content.strip()

    decisions = state.get("decisions", [])
    # Keyword heuristic for relevance
    relevant_kw = ["相关", "关注", "投资", "买入", "值得", "值得关注", "值得关注"]
    not_relevant_kw = ["不相关", "无关", "丢弃", "忽略", "观察即可", "继续观察"]
    is_relevant = any(k in content for k in relevant_kw) and not any(
        k in content for k in not_relevant_kw
    )

    if is_relevant and alerts:
        decisions.append({
            "source": "monitor",
            "relevant_reason": content[:300],
            "alerts": alerts,
            "research_done": False,
            "submitted": False,
        })

    return {"alerts": [], "decisions": decisions}


async def research_router(state: dict, llm) -> dict:
    """Run deep research on each relevant alert using the skill chain:
    get_live_price → research_asset → parse_research_and_submit.
    """
    decisions = state.get("decisions", [])
    if not decisions:
        return state

    bound_llm = _bind_tools(llm)

    for d in decisions:
        if d.get("research_done") or d.get("submitted"):
            continue

        alerts = d.get("alerts", [])
        if not alerts:
            continue

        alert = alerts[0]
        symbol = alert.get("symbol", "")
        source = alert.get("source", "unknown")
        asset_class = _source_to_asset_class(source)
        details_str = str(alert.get("details", {}))

        # Step 1: get live price (tool call)
        price_result = await get_live_price.ainvoke({
            "symbol": symbol,
            "asset_class": asset_class,
        })
        d["live_price"] = price_result

        # Step 2: run research with live price context
        research_result = await research_asset.ainvoke({
            "symbol": symbol,
            "source": source,
            "asset_class": asset_class,
            "details": details_str + f"\n实时价格: {price_result}",
        })
        d["research_result"] = research_result

        # Step 3: parse research and submit to DB
        submit_result = await parse_research_and_submit.ainvoke({
            "research_result": research_result,
            "symbol": symbol,
            "asset_class": asset_class,
            "source": source,
        })
        d["submitted"] = True
        d["submit_result"] = submit_result
        d["research_done"] = True

    return {"decisions": decisions}


async def approval_router(state: dict, llm) -> dict:
    """Read submitted decisions and format for the dashboard / Telegram notification."""
    decisions = state.get("decisions", [])
    pending_approvals = []

    for d in decisions:
        if not d.get("submitted"):
            continue
        alerts = d.get("alerts", [])
        alert = alerts[0] if alerts else {}
        pending_approvals.append({
            "symbol": alert.get("symbol", ""),
            "source": alert.get("source", ""),
            "alert_type": alert.get("alert_type", ""),
            "details": alert.get("details", {}),
            "research_reason": d.get("relevant_reason", ""),
            "submit_result": d.get("submit_result", ""),
            "live_price": d.get("live_price", ""),
        })

    return {"pending_approval": pending_approvals}


def _source_to_asset_class(source: str) -> str:
    """Map monitor source name to watchlist asset_class."""
    mapping = {
        "akshare": "stock",
        "okx": "crypto",
        "binance": "crypto",
        "ebay": "sports_card",
        "yfinance": "stock",
    }
    return mapping.get(source.lower(), "stock")
