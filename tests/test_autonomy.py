import pytest
from agents.autonomy import AutonomyChecker, check_trade_autonomy, AutonomyResult

def test_autonomy_checker_disabled_by_default():
    """Phase 1: autonomy should be disabled by default."""
    checker = AutonomyChecker()
    assert checker.is_enabled is False

def test_autonomy_check_phase1():
    """Phase 1: all trades should be rejected."""
    result = check_trade_autonomy(
        symbol="BTC",
        quantity=0.01,
        price=80000,
        confidence=0.9,
        risk_level="low",
        asset_class="crypto",
        exchange="Binance",
    )
    assert result.can_auto_execute is False
    assert "disabled" in result.reason.lower() or "Phase 1" in result.reason

def test_autonomy_result_dataclass():
    """Test AutonomyResult structure."""
    result = AutonomyResult(
        can_auto_execute=True,
        reason="All conditions met",
        conditions_met={"max_position_value": True, "min_confidence": True},
        conditions_failed={},
    )
    assert result.can_auto_execute is True
    assert len(result.conditions_met) == 2
    assert len(result.conditions_failed) == 0

def test_autonomy_log_message():
    """Test audit log message generation."""
    checker = AutonomyChecker()
    result = checker.check_trade(
        symbol="ETH",
        quantity=1.0,
        price=2000,
        confidence=0.9,
        risk_level="low",
        asset_class="crypto",
        exchange="Binance",
    )
    log = checker.get_log_message(result, "ETH")
    assert "REJECTED" in log