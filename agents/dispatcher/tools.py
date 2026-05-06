"""Tools available to the Dispatcher agent."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.tools import tool
from dashboard.backend.database import (
    get_all_positions,
    create_decision,
    get_pending_decisions,
)


@tool
async def lookup_portfolio() -> str:
    """Look up the current portfolio positions across all asset classes."""
    positions = await get_all_positions()
    if not positions:
        return "投资组合为空"
    lines = []
    for p in positions:
        val = p["quantity"] * p["avg_cost"]
        lines.append(f"- {p['asset_class']}: {p['symbol']} x {p['quantity']} @ ¥{p['avg_cost']:.2f} = ¥{val:.2f}")
    return "\n".join(lines)


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
    return f"决策已提交(ID: {decision_id})，等待人类审批"


@tool
async def lookup_pending_decisions() -> str:
    """Look up all pending decisions awaiting human approval."""
    decisions = await get_pending_decisions()
    if not decisions:
        return "暂无待审批决策"
    lines = [f"共 {len(decisions)} 条待审批:"]
    for d in decisions:
        lines.append(f"- [{d['id']}] {d['decision_type'].upper()} {d['symbol']} @ {d.get('action_price', '市价')} (置信度: {d['confidence']:.0%})")
    return "\n".join(lines)
