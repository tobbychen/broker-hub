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
async def test_check_autonomy_disabled():
    """Phase 1: autonomy should be disabled."""
    result = await check_autonomy(
        action="auto approve trade",
        target={},
        context={},
    )
    assert result.approved is False
    assert "disabled" in result.reason.lower() or "Phase 1" in result.reason


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