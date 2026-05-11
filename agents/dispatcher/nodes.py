"""LangGraph nodes for the Dispatcher orchestrator."""
import json
import re
import logging
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from .prompts import DISPATCHER_SYSTEM, format_alert_for_dispatcher
from .skills.loader import get_skill_loader
from ..research_analyst.agent import research_opportunity
from ..trade_executor.agent import draft_order
from ..risk_manager.rules import check_risk
from ..portfolio_tracker.tracker import update_portfolio, format_portfolio_summary
from ..llm import get_single_llm

logger = logging.getLogger(__name__)


def _bind_tools(llm):
    """Bind all skills (hot-loaded from markdown) to the LLM."""
    loader = get_skill_loader()
    tools = loader.get_tools()
    return llm.bind_tools(tools)


def _source_to_asset_class(source: str) -> str:
    mapping = {
        "akshare": "stock",
        "okx": "crypto",
        "binance": "crypto",
        "ebay": "sports_card",
        "yfinance": "stock",
    }
    return mapping.get(source.lower(), "stock")


# ---- Portfolio Tracker Node ----

async def portfolio_tracker_node(state: dict, llm) -> dict:
    """
    Update portfolio positions and P&L from market cache.
    This runs before research to ensure the portfolio context is fresh.
    """
    try:
        summary = await update_portfolio()
        state["portfolio_summary"] = format_portfolio_summary(summary)
        logger.info("[portfolio_tracker] Portfolio updated")
    except Exception as e:
        logger.error(f"[portfolio_tracker] Error: {e}")
        state["portfolio_summary"] = "Portfolio update failed"
    return state


# ---- Monitor Handler Node ----

async def monitor_handler(state: dict, llm) -> dict:
    """Handle incoming market alerts — determine if any are investment-relevant."""
    alerts = state.get("alerts", [])
    if not alerts:
        return {"alerts": [], "decisions": state.get("decisions", [])}

    bound_llm = _bind_tools(llm)
    alert_summaries = [format_alert_for_dispatcher(a) for a in alerts]
    portfolio_str = await get_skill_loader().get_skill("lookup_portfolio").fn()

    prompt = f"""以下市场警报已触发：

{chr(10).join(alert_summaries)}

当前投资组合：
{portfolio_str}

分析这些警报是否与投资相关。如相关，请用中文解释原因并给出判断：相关/不相关。
仅输出你的分析结论。"""

    response = await bound_llm.ainvoke([HumanMessage(content=prompt)])
    content = response.content.strip()

    decisions = state.get("decisions", [])
    relevant_kw = ["相关", "关注", "投资", "买入", "值得", "值得关注"]
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
            "status": "pending",
        })

    return {"alerts": [], "decisions": decisions}


# ---- Research Router Node ----

async def research_router(state: dict, llm) -> dict:
    """
    Run deep research on each relevant decision.
    Calls research_opportunity() from research_analyst/agent.py (was previously unused).
    """
    decisions = state.get("decisions", [])
    if not decisions:
        return state

    loader = get_skill_loader()
    portfolio_str = state.get("portfolio_summary", "") or await loader.get_skill("lookup_portfolio").fn()

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

        # Get live price from hot-loaded skill
        price_result = await loader.get_skill("get_live_price").fn(
            symbol=symbol,
            asset_class=asset_class,
        )
        d["live_price"] = price_result

        # Run deep research using the Research Analyst agent
        research_result = await research_opportunity(alert, portfolio_str)
        d["research_result"] = research_result
        d["research_done"] = True

        # Parse structured output from research and submit to DB
        submit_result = await loader.get_skill("parse_research_and_submit").fn(
            research_result=research_result,
            symbol=symbol,
            asset_class=asset_class,
            source=source,
        )
        d["submitted"] = True
        d["submit_result"] = submit_result

        # Extract confidence from the research result for routing
        confidence = _extract_confidence(research_result)
        d["confidence"] = confidence

    return {"decisions": decisions}


def _extract_confidence(text: str) -> float:
    """Extract confidence score from research result text."""
    # Try JSON first
    content = text.strip()
    if "```json" in content:
        json_str = content.split("```json")[1].split("```")[0]
        try:
            parsed = json.loads(json_str.strip())
            if "置信度" in parsed:
                return float(parsed["置信度"])
        except (json.JSONDecodeError, ValueError):
            pass

    # Try regex for number patterns
    patterns = [
        r"置信度[:：]\s*([0-9.]+)",
        r"confidence[:：]\s*([0-9.]+)",
        r"([0-9.]+)\s*%",
    ]
    for pat in patterns:
        m = re.search(pat, content, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if val <= 1:
                val *= 100
            return val / 100 if val > 1 else val

    return 0.5  # default


# ---- Risk Manager Node ----

async def risk_manager_node(state: dict, llm) -> dict:
    """
    Run pre-trade risk checks using the rule engine.
    No LLM needed — pure rule-based checks from agent_settings.yaml.
    """
    from dashboard.backend.database import get_all_positions, get_market_cache

    decisions = state.get("decisions", [])
    if not decisions:
        return state

    risk_checks = {}

    for d in decisions:
        if not d.get("submitted"):
            continue

        alerts = d.get("alerts", [])
        if not alerts:
            continue

        alert = alerts[0]
        symbol = alert.get("symbol", "")
        asset_class = _source_to_asset_class(alert.get("source", ""))

        # Get proposed trade info from the alert details
        details = alert.get("details", {})
        quantity = details.get("quantity") or details.get("volume") or 1.0
        price = details.get("price") or 0.0

        # Get current positions for total portfolio value
        positions = await get_all_positions()
        total_value = sum(p.get("quantity", 0) * p.get("avg_cost", 0) for p in positions)

        # Get current market price if we don't have one yet
        if not price:
            cache = await get_market_cache(symbol, "", "latest_price")
            if cache:
                raw = cache.get("raw_data", "{}")
                if isinstance(raw, str):
                    try:
                        raw = json.loads(raw)
                    except Exception:
                        pass
                price = raw.get("price", 0) if isinstance(raw, dict) else 0

        proposed_trade = {
            "symbol": symbol,
            "asset_class": asset_class,
            "quantity": float(quantity),
            "price": float(price) if price else 0.0,
            "action": d.get("submit_result", ""),
        }

        result = await check_risk(proposed_trade, positions, total_value)
        risk_checks[symbol] = {
            "passed": result.passed,
            "reason": result.reason,
            "auto_approve": result.auto_approve,
            "human_required": result.human_required,
        }

        d["risk_check"] = result.reason
        d["risk_passed"] = result.passed

    return {"risk_checks": risk_checks, "decisions": decisions}


# ---- Approval Router Node ----

async def approval_router(state: dict, llm) -> dict:
    """
    Format submitted decisions for human review.
    Sends to dashboard + Telegram for approval.
    """
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
            "risk_check": d.get("risk_check", ""),
            "confidence": d.get("confidence", 0.5),
        })

    return {"pending_approval": pending_approvals}


# ---- Trade Executor Node ----

async def trade_executor_node(state: dict, llm) -> dict:
    """
    Draft an order based on approved research.
    Calls draft_order() from trade_executor/agent.py (was previously unused).
    Phase 1: drafts only, no auto-execution.
    """
    decisions = state.get("decisions", [])
    draft_orders = {}

    for d in decisions:
        if d.get("status") != "approved":
            continue

        research_result = d.get("research_result", "")
        if not research_result:
            continue

        try:
            order_draft = await draft_order(research_result)
            draft_orders[d.get("alerts", [{}])[0].get("symbol", "")] = order_draft
            d["order_draft"] = order_draft
        except Exception as e:
            logger.error(f"[trade_executor] Error drafting order: {e}")
            draft_orders[d.get("alerts", [{}])[0].get("symbol", "")] = f"Draft failed: {e}"

    return {"draft_orders": draft_orders}


# ---- Log and Discard Node ----

async def log_and_discard_node(state: dict) -> dict:
    """Log and discard decisions that fail checks or are rejected."""
    decisions = state.get("decisions", [])
    for d in decisions:
        reason = "low_confidence"
        if d.get("risk_passed") is False:
            reason = "risk_check_failed"
        elif d.get("status") == "rejected":
            reason = "human_rejected"
        logger.info(f"[dispatcher] Discarding decision: {d.get('alerts', [{}])[0].get('symbol', '?')} ({reason})")
    return state
