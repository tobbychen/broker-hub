"""Autonomy checker for Phase 2 auto-execute conditions."""

from dataclasses import dataclass
from typing import Optional
import logging

from ..config import get_agent_settings

logger = logging.getLogger(__name__)

@dataclass
class AutonomyResult:
    """Result of autonomy check."""
    can_auto_execute: bool
    reason: str
    conditions_met: dict
    conditions_failed: dict

class AutonomyChecker:
    """Check if a trade qualifies for autonomous execution."""

    def __init__(self):
        self.settings = get_agent_settings().get("autonomy", {})
        self.auto_approve = self.settings.get("auto_approve", {})

    @property
    def is_enabled(self) -> bool:
        """Check if autonomy is enabled (Phase 1 = disabled)."""
        return self.settings.get("enabled", False)

    def check_trade(
        self,
        symbol: str,
        quantity: float,
        price: float,
        confidence: float,
        risk_level: str,
        asset_class: str,
        exchange: str,
    ) -> AutonomyResult:
        """Check if a trade meets auto-approve conditions."""
        conditions_met = {}
        conditions_failed = {}

        # Check 1: Is autonomy enabled?
        if not self.is_enabled:
            return AutonomyResult(
                can_auto_execute=False,
                reason="Autonomous execution is disabled (Phase 1)",
                conditions_met={"enabled": False},
                conditions_failed={},
            )

        # Calculate position value
        position_value = quantity * price

        # Check 2: Position size limit
        max_value = self.auto_approve.get("max_position_value", 10000)
        size_ok = position_value <= max_value
        conditions_met["max_position_value"] = size_ok
        if not size_ok:
            conditions_failed["max_position_value"] = f"¥{position_value:.0f} > ¥{max_value:,}"

        # Check 3: Confidence threshold
        min_conf = self.auto_approve.get("min_confidence", 0.85)
        conf_ok = confidence >= min_conf
        conditions_met["min_confidence"] = conf_ok
        if not conf_ok:
            conditions_failed["min_confidence"] = f"{confidence:.0%} < {min_conf:.0%}"

        # Check 4: Risk level
        max_risk = self.auto_approve.get("max_risk", "low")
        risk_order = {"low": 0, "medium": 1, "high": 2}
        risk_ok = risk_order.get(risk_level.lower(), 2) <= risk_order.get(max_risk, 0)
        conditions_met["risk_level"] = risk_ok
        if not risk_ok:
            conditions_failed["risk_level"] = f"{risk_level} > {max_risk}"

        # Check 5: Asset class
        allowed_classes = self.auto_approve.get("allowed_asset_class", [])
        class_ok = asset_class.lower() in [c.lower() for c in allowed_classes]
        conditions_met["asset_class"] = class_ok
        if not class_ok:
            conditions_failed["asset_class"] = f"{asset_class} not in {allowed_classes}"

        # Check 6: Exchange
        allowed_exchanges = self.auto_approve.get("allowed_exchanges", [])
        exchange_ok = not allowed_exchanges or exchange in allowed_exchanges
        conditions_met["exchange"] = exchange_ok
        if not exchange_ok:
            conditions_failed["exchange"] = f"{exchange} not in {allowed_exchanges}"

        # Overall decision
        all_passed = all([size_ok, conf_ok, risk_ok, class_ok, exchange_ok])

        reasons = []
        if all_passed:
            reasons.append(f"All conditions met for {symbol}")
        else:
            reasons.append("Conditions not met:")
            reasons.extend(f"  - {v}" for v in conditions_failed.values())

        return AutonomyResult(
            can_auto_execute=all_passed,
            reason="; ".join(reasons),
            conditions_met=conditions_met,
            conditions_failed=conditions_failed,
        )

    def get_log_message(self, result: AutonomyResult, symbol: str) -> str:
        """Generate audit log message for autonomy decision."""
        status = "APPROVED" if result.can_auto_execute else "REJECTED"
        msg = f"[Autonomy] {status} auto-execute for {symbol}: {result.reason}"
        if result.conditions_failed:
            msg += f"\n  Failed: {result.conditions_failed}"
        return msg

_checker: Optional[AutonomyChecker] = None

def get_autonomy_checker() -> AutonomyChecker:
    global _checker
    if _checker is None:
        _checker = AutonomyChecker()
    return _checker

def check_trade_autonomy(
    symbol: str,
    quantity: float,
    price: float,
    confidence: float,
    risk_level: str,
    asset_class: str,
    exchange: str,
) -> AutonomyResult:
    """Quick check if trade can auto-execute."""
    checker = get_autonomy_checker()
    return checker.check_trade(
        symbol=symbol, quantity=quantity, price=price,
        confidence=confidence, risk_level=risk_level,
        asset_class=asset_class, exchange=exchange,
    )