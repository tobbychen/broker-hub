"""Tools (skills) available to the Dispatcher agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import re
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from dashboard.backend.database import (
    get_all_positions,
    create_decision,
    get_pending_decisions,
)
from ..llm import get_single_llm


RESEARCH_SYSTEM = """你是一个专业的投资研究分析师。给定一个资产警报，你需要：
1. 深度分析是否构成真实的投资机会
2. 给出置信度评估和风险评级
3. 用清晰的中文解释分析逻辑

重要：必须输出结构化的JSON：
{"置信度": 0.75, "风险等级": "medium", "建议行动": "buy", "分析理由": "...", "建议数量": null}"""


# ---- Portfolio skills ----

@tool
async def lookup_portfolio() -> str:
    """Look up the current portfolio positions across all asset classes."""
    positions = await get_all_positions()
    if not positions:
        return "投资组合为空，当前无持仓"
    lines = []
    for p in positions:
        val = p["quantity"] * p["avg_cost"]
        lines.append(
            f"- {p['asset_class']}: {p['symbol']} x {p['quantity']} "
            f"@ ¥{p['avg_cost']:.2f} = ¥{val:.2f}"
        )
    return "\n".join(lines)


# ---- Market data skills ----

@tool
async def get_live_price(symbol: str, asset_class: str = "") -> str:
    """Fetch the current market price for a symbol from the market cache."""
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


# ---- Decision submission skill ----

@tool
async def parse_research_and_submit(research_result: str, symbol: str, asset_class: str, source: str) -> str:
    """Parse the research analyst's output and submit a decision to the database."""
    content = research_result.strip()
    parsed = None

    # Try JSON block extraction
    if "```json" in content:
        json_str = content.split("```json")[1].split("```")[0]
        try:
            parsed = json.loads(json_str.strip())
        except json.JSONDecodeError:
            pass

    if parsed is None:
        # Try regex brace matching
        brace_match = re.search(
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
            content,
            re.DOTALL,
        )
        if brace_match:
            try:
                parsed = json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass

    if parsed is None:
        # Keyword fallback
        confidence = 0.5
        risk_level = "medium"
        action = "hold"
        reason = content[:500]

        confidence_map = {"高": 0.85, "中": 0.65, "低": 0.45, "很高": 0.95, "很低": 0.35}
        for kw, val in confidence_map.items():
            if kw in content:
                confidence = val
                break

        if any(k in content for k in ["建议行动", "buy", "买入", "做多"]):
            action = "buy"
        elif any(k in content for k in ["sell", "卖出", "做空", "减持"]):
            action = "sell"

        if any(k in content for k in ["风险等级", "风险:"]):
            for rl in ["高", "中", "低"]:
                if rl in content:
                    risk_level = {"高": "high", "中": "medium", "低": "low"}.get(rl, "medium")
                    break

        parsed = {
            "置信度": confidence,
            "风险等级": risk_level,
            "建议行动": action,
            "分析理由": reason,
            "建议数量": None,
        }

    decision_id = await create_decision(
        decision_type=parsed.get("建议行动", "hold"),
        asset_class=asset_class,
        symbol=symbol,
        quantity=parsed.get("建议数量"),
        action_price=None,
        confidence=float(parsed.get("置信度", 0.5)),
        reasoning=parsed.get("分析理由", content[:500]),
        risk_level=parsed.get("风险等级", "medium"),
        timeout_minutes=30,
    )

    return f"决策已提交 (ID: {decision_id})，等待人类审批。置信度: {parsed.get('置信度')}, 风险: {parsed.get('风险等级')}"


# ---- Legacy / router tools ----

@tool
async def submit_decision(
    decision_type: str,
    asset_class: str,
    symbol: str,
    exchange: str,
    quantity: float | None,
    action_price: float | None,
    confidence: float,
    reasoning: str,
    risk_level: str,
) -> str:
    """Submit a new trading decision for human approval."""
    decision_id = await create_decision(
        decision_type=decision_type,
        asset_class=asset_class,
        symbol=symbol,
        quantity=quantity,
        action_price=action_price,
        confidence=confidence,
        reasoning=reasoning,
        risk_level=risk_level,
        timeout_minutes=30,
    )
    return f"决策已提交 (ID: {decision_id})，等待人类审批"


@tool
async def lookup_pending_decisions() -> str:
    """Look up all pending decisions awaiting human approval."""
    decisions = await get_pending_decisions()
    if not decisions:
        return "暂无待审批决策"
    lines = [f"共 {len(decisions)} 条待审批:"]
    for d in decisions:
        lines.append(
            f"- [{d['id']}] {d['decision_type'].upper()} {d['symbol']} "
            f"@ {d.get('action_price', '市价')} "
            f"(置信度: {d['confidence']:.0%}, 风险: {d['risk_level']})"
        )
    return "\n".join(lines)
