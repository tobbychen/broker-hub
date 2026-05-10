"""Portfolio tracking: positions, P&L, allocation snapshots."""
import json
import logging
from dataclasses import dataclass
from typing import Optional

from agents.config import get_agent_settings

logger = logging.getLogger(__name__)


@dataclass
class PositionPnL:
    symbol: str
    asset_class: str
    exchange: str
    quantity: float
    avg_cost: float
    current_price: float
    current_value: float
    cost_basis: float
    pnl: float
    pnl_pct: float


@dataclass
class PortfolioSummary:
    total_value: float
    total_cost_basis: float
    total_pnl: float
    total_pnl_pct: float
    positions: list[PositionPnL]
    allocation_by_class: dict[str, float]


async def update_portfolio() -> PortfolioSummary:
    """
    Read current positions from DB, compute P&L vs avg_cost,
    compute allocation by asset_class, store snapshot.
    """
    from dashboard.backend.database import (
        get_all_positions,
        get_market_cache,
        set_portfolio_snapshot,
    )

    positions = await get_all_positions()
    if not positions:
        return PortfolioSummary(
            total_value=0, total_cost_basis=0, total_pnl=0,
            total_pnl_pct=0, positions=[], allocation_by_class={},
        )

    # Build market cache lookup map
    cache = {}
    for pos in positions:
        key = (pos.get("symbol", ""), pos.get("exchange", ""))
        cached = await get_market_cache(key[0], key[1], "latest_price")
        if cached:
            raw = cached.get("raw_data", {})
            if isinstance(raw, dict):
                cache[key] = raw.get("price") or raw.get("last_price")
            elif isinstance(raw, (int, float)):
                cache[key] = raw

    pnl_positions = []
    class_values: dict[str, float] = {}
    total_value = 0.0
    total_cost_basis = 0.0

    for pos in positions:
        quantity = pos.get("quantity", 0)
        avg_cost = pos.get("avg_cost", 0)
        cost_basis = quantity * avg_cost

        key = (pos.get("symbol", ""), pos.get("exchange", ""))
        current_price = cache.get(key) or avg_cost  # fallback to avg_cost if no cache
        current_value = quantity * current_price
        pnl = current_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0

        pnl_pos = PositionPnL(
            symbol=pos.get("symbol", ""),
            asset_class=pos.get("asset_class", ""),
            exchange=pos.get("exchange", ""),
            quantity=quantity,
            avg_cost=avg_cost,
            current_price=current_price,
            current_value=current_value,
            cost_basis=cost_basis,
            pnl=pnl,
            pnl_pct=pnl_pct,
        )
        pnl_positions.append(pnl_pos)

        class_values[pos.get("asset_class", "other")] = (
            class_values.get(pos.get("asset_class", "other"), 0) + current_value
        )
        total_value += current_value
        total_cost_basis += cost_basis

    total_pnl = total_value - total_cost_basis
    total_pnl_pct = (total_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0

    allocation_by_class: dict[str, float] = {}
    if total_value > 0:
        for cls, val in class_values.items():
            allocation_by_class[cls] = val / total_value * 100

    summary = PortfolioSummary(
        total_value=total_value,
        total_cost_basis=total_cost_basis,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        positions=pnl_positions,
        allocation_by_class=allocation_by_class,
    )

    # Store snapshot
    positions_json = json.dumps([{
        "symbol": p.symbol,
        "asset_class": p.asset_class,
        "exchange": p.exchange,
        "quantity": p.quantity,
        "avg_cost": p.avg_cost,
        "current_price": p.current_price,
        "current_value": p.current_value,
        "pnl": p.pnl,
        "pnl_pct": p.pnl_pct,
    } for p in pnl_positions])

    allocation_json = json.dumps(allocation_by_class)

    try:
        await set_portfolio_snapshot(total_value, positions_json, allocation_json)
    except Exception as e:
        logger.warning(f"[portfolio_tracker] Failed to store snapshot: {e}")

    return summary


def format_portfolio_summary(summary: PortfolioSummary) -> str:
    """Format a portfolio summary as a readable string for LLM/prompts."""
    if not summary.positions:
        return "No positions in portfolio."

    lines = [
        f"总价值: ¥{summary.total_value:,.2f}  "
        f"(成本: ¥{summary.total_cost_basis:,.2f}, "
        f"P&L: ¥{summary.total_pnl:+,.2f} {summary.total_pnl_pct:+.2f}%)",
        "",
    ]

    for cls, pct in sorted(summary.allocation_by_class.items()):
        lines.append(f"  [{cls}] {pct:.1f}%")

    lines.append("")
    for p in summary.positions:
        arrow = "▲" if p.pnl >= 0 else "▼"
        lines.append(
            f"{arrow} {p.symbol} ({p.asset_class}) "
            f"x{p.quantity} @ ¥{p.avg_cost:.2f} → ¥{p.current_price:.2f} "
            f"P&L ¥{p.pnl:+,.2f} ({p.pnl_pct:+.2f}%)"
        )

    return "\n".join(lines)
