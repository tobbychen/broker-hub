import pytest
from agents.autonomy import AutonomyChecker, check_trade_autonomy, AutonomyResult

def test_autonomy_checker_enabled():
    """Phase 2: autonomy should be enabled."""
    checker = AutonomyChecker()
    assert checker.is_enabled is True

def test_autonomy_check_conditions():
    """Phase 2: trades meeting conditions should be approved."""
    result = check_trade_autonomy(
        symbol="BTC",
        quantity=0.01,
        price=80000,
        confidence=0.9,
        risk_level="low",
        asset_class="crypto",
        exchange="Binance",
    )
    assert result.can_auto_execute is True
    assert "All conditions met" in result.reason

def test_autonomy_large_position_rejected():
    """Large positions should be rejected."""
    result = check_trade_autonomy(
        symbol="BTC",
        quantity=0.5,  # 0.5 * 80000 = 40000 > 10000 limit
        price=80000,
        confidence=0.95,
        risk_level="low",
        asset_class="crypto",
        exchange="Binance",
    )
    assert result.can_auto_execute is False
    assert "max_position_value" in result.conditions_failed

def test_autonomy_low_confidence_rejected():
    """Low confidence trades should be rejected."""
    result = check_trade_autonomy(
        symbol="ETH",
        quantity=0.1,
        price=2000,
        confidence=0.5,  # Below 85% threshold
        risk_level="low",
        asset_class="crypto",
        exchange="Binance",
    )
    assert result.can_auto_execute is False
    assert "min_confidence" in result.conditions_failed

def test_autonomy_high_risk_rejected():
    """High risk trades should be rejected."""
    result = check_trade_autonomy(
        symbol="SOL",
        quantity=0.1,
        price=2000,
        confidence=0.9,
        risk_level="high",  # Exceeds max_risk=low
        asset_class="crypto",
        exchange="Binance",
    )
    assert result.can_auto_execute is False
    assert "risk_level" in result.conditions_failed

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

def test_autonomy_log_message_approved():
    """Test audit log message generation for approved trades."""
    checker = AutonomyChecker()
    result = checker.check_trade(
        symbol="BTC",
        quantity=0.01,
        price=80000,
        confidence=0.9,
        risk_level="low",
        asset_class="crypto",
        exchange="Binance",
    )
    log = checker.get_log_message(result, "BTC")
    assert "APPROVED" in log

def test_autonomy_log_message_rejected():
    """Test audit log message generation for rejected trades."""
    checker = AutonomyChecker()
    result = checker.check_trade(
        symbol="ETH",
        quantity=6.0,  # 6.0 * 2000 = ¥12000 > ¥10000 limit
        price=2000,
        confidence=0.9,
        risk_level="low",
        asset_class="crypto",
        exchange="Binance",
    )
    log = checker.get_log_message(result, "ETH")
    assert "REJECTED" in log
    assert "max_position_value" in log