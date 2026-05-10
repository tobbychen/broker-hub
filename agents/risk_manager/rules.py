"""Rule engine for pre-trade risk checks."""
import logging
from dataclasses import dataclass
from typing import Optional

from agents.config import get_agent_settings

logger = logging.getLogger(__name__)


@dataclass
class RiskCheckResult:
    passed: bool
    reason: str
    auto_approve: bool = False
    human_required: bool = True


async def check_risk(
    proposed_trade: dict,
    positions: list[dict],
    total_portfolio_value: float,
) -> RiskCheckResult:
    """
    Run pre-trade risk checks against agent_settings.yaml rules.

    proposed_trade: {symbol, asset_class, quantity, price, action}
    positions: list of {asset_class, quantity, avg_cost} from DB
    total_portfolio_value: total portfolio value for % calculations
    """
    settings = get_agent_settings()
    risk_cfg = settings.get("risk", {})

    max_position_pct = risk_cfg.get("max_position_pct", 0.20)
    max_sector_pct = risk_cfg.get("max_sector_pct", 0.40)
    autonomy_cfg = settings.get("autonomy", {})
    small_position_limit = autonomy_cfg.get("small_position_limit", 10000)
    require_human_approval = autonomy_cfg.get("require_human_approval", True)

    symbol = proposed_trade.get("symbol", "")
    asset_class = proposed_trade.get("asset_class", "")
    quantity = proposed_trade.get("quantity", 0)
    price = proposed_trade.get("price", 0)

    proposed_value = quantity * price

    # Rule 1: Single position size limit
    proposed_pct = proposed_value / total_portfolio_value if total_portfolio_value > 0 else 0
    if proposed_pct > max_position_pct:
        return RiskCheckResult(
            passed=False,
            reason=f"Position size {proposed_pct:.1%} exceeds limit {max_position_pct:.1%} "
                   f"(¥{proposed_value:,.0f} / ¥{total_portfolio_value:,.0f})",
        )

    # Rule 2: Sector (asset_class) allocation limit
    sector_value = sum(
        p.get("quantity", 0) * p.get("avg_cost", 0)
        for p in positions
        if p.get("asset_class") == asset_class
    )
    sector_pct = sector_value / total_portfolio_value if total_portfolio_value > 0 else 0

    # Check if adding proposed trade would exceed sector limit
    new_sector_value = sector_value + proposed_value
    new_sector_pct = new_sector_value / total_portfolio_value if total_portfolio_value > 0 else 0
    if new_sector_pct > max_sector_pct:
        return RiskCheckResult(
            passed=False,
            reason=f"Sector {asset_class} allocation {new_sector_pct:.1%} "
                   f"exceeds limit {max_sector_pct:.1%}",
        )

    # Rule 3: Autonomy — small positions may auto-approve
    auto_approve = (
        proposed_value < small_position_limit
        and not require_human_approval
    )

    if auto_approve:
        return RiskCheckResult(
            passed=True,
            reason=f"Small position (¥{proposed_value:,.0f} < ¥{small_position_limit:,}), "
                   f"auto-approved",
            auto_approve=True,
            human_required=False,
        )

    return RiskCheckResult(
        passed=True,
        reason="All risk checks passed",
        auto_approve=False,
        human_required=True,
    )
