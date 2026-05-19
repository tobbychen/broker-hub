"""Unified pre-action hooks for permission review, spec compliance, and autonomy checks."""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of actions that can be hooked."""
    EXECUTE_TRADE = "execute_trade"
    AUTO_APPROVE = "auto_approve"
    SUBMIT_DECISION = "submit_decision"
    MODIFY_POSITION = "modify_position"
    READ_DATA = "read_data"


@dataclass
class HookResult:
    """Result of a hook check."""
    approved: bool
    action: str
    reason: str
    needs_review: bool = False
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


async def check_permission(
    action: str,
    target: dict,
    context: dict,
) -> HookResult:
    """Check permission using the permission reviewer agent."""
    try:
        from .permission_reviewer.agent import review_permission
        result = await review_permission(
            permission=action,
            tool_name=target.get("tool_name"),
            command=target.get("command"),
            target=target.get("target"),
            description=target.get("description"),
        )
        decision = result.get("decision", "review")
        return HookResult(
            approved=(decision == "allow"),
            action=action,
            reason=result.get("reason", ""),
            needs_review=(decision == "review"),
        )
    except Exception as e:
        return HookResult(
            approved=False,
            action=action,
            reason=f"Permission check error: {str(e)[:100]}",
            needs_review=True,
            warnings=["Permission review failed - defaulting to review"],
        )


async def check_spec_compliance(
    action: str,
    target: dict,
    context: dict,
) -> HookResult:
    """Check spec compliance using the spec compliance checker."""
    try:
        from .spec_compliance.checker import check_compliance
        result = check_compliance(
            action=action,
            target=target.get("file_path") or target.get("target"),
            command=target.get("command"),
        )
        return HookResult(
            approved=result.compliant,
            action=action,
            reason=result.reason,
            needs_review=not result.compliant,
            warnings=[result.suggestion] if result.suggestion else [],
        )
    except Exception as e:
        return HookResult(
            approved=True,
            action=action,
            reason=f"Spec check error (allowing): {str(e)[:100]}",
            needs_review=False,
            warnings=["Spec compliance check failed - action allowed with warning"],
        )


async def check_autonomy(
    action: str,
    target: dict,
    context: dict,
) -> HookResult:
    """Check if action qualifies for autonomous execution (Phase 2)."""
    try:
        from .autonomy import check_trade_autonomy

        # Get trade parameters from target
        symbol = target.get("symbol", "UNKNOWN")
        quantity = target.get("quantity", 0)
        price = target.get("price", 0)
        confidence = target.get("confidence", 0.5)
        risk_level = target.get("risk_level", "medium")
        asset_class = target.get("asset_class", "stock")
        exchange = target.get("exchange", "")

        # Check autonomy conditions
        result = check_trade_autonomy(
            symbol=symbol,
            quantity=quantity,
            price=price,
            confidence=confidence,
            risk_level=risk_level,
            asset_class=asset_class,
            exchange=exchange,
        )

        return HookResult(
            approved=result.can_auto_execute,
            action=action,
            reason=result.reason,
            needs_review=not result.can_auto_execute,
            warnings=list(result.conditions_failed.keys()) if result.conditions_failed else [],
        )
    except Exception as e:
        return HookResult(
            approved=False,
            action=action,
            reason=f"Autonomy check error: {str(e)[:100]}",
            needs_review=True,
        )


async def pre_action_check(
    action: str,
    action_type: ActionType,
    target: dict,
    context: dict,
) -> HookResult:
    """Unified pre-action hook combining all checks."""
    results = []
    warnings = []

    # Spec compliance check
    if action_type in (ActionType.SUBMIT_DECISION, ActionType.MODIFY_POSITION):
        spec_result = await check_spec_compliance(action, target, context)
        results.append(spec_result)
        warnings.extend(spec_result.warnings)

    # Permission review
    if action_type in (ActionType.EXECUTE_TRADE, ActionType.AUTO_APPROVE):
        perm_result = await check_permission(action, target, context)
        results.append(perm_result)
        warnings.extend(perm_result.warnings)

    # Autonomy check
    if action_type == ActionType.AUTO_APPROVE:
        auto_result = await check_autonomy(action, target, context)
        results.append(auto_result)
        warnings.extend(auto_result.warnings)

    # Combine results - all must approve
    all_approved = all(r.approved for r in results)
    needs_review = any(r.needs_review for r in results)
    reason = "; ".join(r.reason for r in results if r.reason)

    return HookResult(
        approved=all_approved,
        action=action,
        reason=reason or "No hooks configured",
        needs_review=needs_review,
        warnings=warnings,
    )