import pytest
from agents.hooks import (
    pre_action_check,
    HookResult,
    ActionType,
    check_autonomy,
)


@pytest.mark.asyncio
async def test_hook_result_dataclass():
    result = HookResult(
        approved=True,
        action="read",
        reason="Allowed",
    )
    assert result.approved is True
    assert result.needs_review is False
    assert result.warnings == []


@pytest.mark.asyncio
async def test_check_autonomy_approved():
    """Phase 2: small crypto trade should be approved."""
    result = await check_autonomy(
        action="auto approve trade",
        target={
            "symbol": "BTC",
            "quantity": 0.01,
            "price": 80000,  # 0.01 * 80000 = 800 < 10000 limit
            "confidence": 0.9,
            "risk_level": "low",
            "asset_class": "crypto",
            "exchange": "Binance",
        },
        context={},
    )
    assert result.approved is True
    assert "All conditions met" in result.reason


@pytest.mark.asyncio
async def test_check_autonomy_rejected_large_position():
    """Large positions should be rejected."""
    result = await check_autonomy(
        action="auto approve trade",
        target={
            "symbol": "BTC",
            "quantity": 0.5,  # 0.5 * 80000 = 40000 > 10000 limit
            "price": 80000,
            "confidence": 0.9,
            "risk_level": "low",
            "asset_class": "crypto",
            "exchange": "Binance",
        },
        context={},
    )
    assert result.approved is False
    assert "max_position_value" in result.warnings


@pytest.mark.asyncio
async def test_pre_action_check_read_data():
    result = await pre_action_check(
        action="read portfolio",
        action_type=ActionType.READ_DATA,
        target={"file_path": "agents/dispatcher/nodes.py"},
        context={},
    )
    assert isinstance(result, HookResult)
    assert result.action == "read portfolio"


@pytest.mark.asyncio
async def test_pre_action_check_submit_decision():
    result = await pre_action_check(
        action="submit decision",
        action_type=ActionType.SUBMIT_DECISION,
        target={"symbol": "BTC"},
        context={},
    )
    assert isinstance(result, HookResult)