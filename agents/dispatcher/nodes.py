"""LangGraph nodes for the Dispatcher agent."""
import json
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from .prompts import DISPATCHER_SYSTEM, format_alert_for_dispatcher
from .tools import lookup_portfolio, submit_decision, lookup_pending_decisions


def _make_llm(llm):
    """Bind tools to the LLM."""
    return llm.bind_tools([lookup_portfolio, submit_decision, lookup_pending_decisions])


async def monitor_handler(state: dict, llm) -> dict:
    """Handle incoming market alerts — route to research or discard."""
    alerts = state.get("alerts", [])
    if not alerts:
        return {"alerts": [], "decisions": state.get("decisions", [])}

    portfolio_str = await lookup_portfolio.ainvoke({})

    alert_summaries = [format_alert_for_dispatcher(a) for a in alerts]
    prompt = f"""以下市场警报已触发，请判断是否值得关注：

{chr(10).join(alert_summaries)}

当前投资组合：
{portfolio_str}

对于每个警报，判断是否相关。如相关，输出 JSON：
{{"relevant": true, "reason": "...", "symbol": "...", "exchange": "..."}}

如不相关，输出：
{{"relevant": false, "reason": "..."}}

仅输出 JSON，不要其他内容。"""

    bound_llm = _make_llm(llm)
    response = await bound_llm.ainvoke([HumanMessage(content=prompt)])
    content = response.content.strip()

    decisions = state.get("decisions", [])
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        parsed = json.loads(content.strip())
        if isinstance(parsed, dict) and parsed.get("relevant"):
            decisions.append({"source": "monitor", "relevant": parsed, "alerts": alerts})
    except (json.JSONDecodeError, AttributeError):
        pass

    return {"alerts": [], "decisions": decisions}


async def research_router(state: dict, llm) -> dict:
    """Route relevant alerts to research analyst."""
    decisions = state.get("decisions", [])
    if not decisions:
        return state
    for d in decisions:
        if d.get("source") == "monitor" and not d.get("researched"):
            d["researched"] = True
            break
    return {"decisions": decisions}


async def approval_router(state: dict, llm) -> dict:
    """Format decision for human approval and submit to database."""
    decisions = state.get("decisions", [])
    if not decisions:
        return {"pending_approval": None}

    current = decisions[0]
    alert = current.get("alerts", [{}])[0]

    recommendation = {
        "decision_type": "buy" if current.get("relevant", {}).get("direction") == "up" else "hold",
        "asset_class": alert.get("source", "unknown"),
        "symbol": current.get("relevant", {}).get("symbol", alert.get("symbol", "")),
        "exchange": current.get("relevant", {}).get("exchange", alert.get("exchange", "")),
        "quantity": None,
        "action_price": alert.get("details", {}).get("current_price"),
        "confidence": 0.75,
        "reasoning": f"监控警报: {alert.get('alert_type')}, 详情: {alert.get('details')}",
        "risk_level": "medium",
    }

    return {"pending_approval": recommendation}
