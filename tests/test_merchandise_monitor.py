"""Tests for merchandise monitor modules."""
import pytest
from unittest.mock import patch, MagicMock
from agents.monitor.base import Alert, MerchandiseAlert


def test_merchandise_alert_fields():
    """Test MerchandiseAlert has all required fields."""
    alert = MerchandiseAlert(
        source="ebay",
        alert_type="price_drop",
        symbol="RW-875-10D",
        exchange="eBay",
        brand="Red Wing",
        model="875",
        variant="Size 10D",
        platforms={"eBay": 150.00, "Amazon": 145.00},
        purchase_price=149.99,
        purchase_currency="USD",
        current_price=145.00,
        current_platform="eBay",
        change_pct=-0.033,
        arbitrage_opportunity=True,
        source_platform="Amazon",
    )
    assert alert.brand == "Red Wing"
    assert alert.model == "875"
    assert alert.variant == "Size 10D"
    assert alert.arbitrage_opportunity is True
    assert alert.source_platform == "Amazon"
    assert alert.platforms["Amazon"] == 145.00


def test_merchandise_alert_default_values():
    """Test MerchandiseAlert has sensible defaults."""
    alert = MerchandiseAlert(
        source="amazon",
        alert_type="price_spike",
        symbol="TEST-001",
        exchange="Amazon",
    )
    assert alert.brand == ""
    assert alert.model == ""
    assert alert.variant == ""
    assert alert.platforms == {}
    assert alert.purchase_price == 0.0
    assert alert.purchase_currency == "CNY"
    assert alert.arbitrage_opportunity is False


def test_merchandise_alert_extends_alert():
    """Test MerchandiseAlert inherits from Alert."""
    alert = MerchandiseAlert(
        source="jd",
        alert_type="owned_price_drop",
        symbol="JD-ITEM-001",
        exchange="JD",
        priority="high",
    )
    assert isinstance(alert, Alert)
    assert alert.priority == "high"
    assert alert.timestamp is not None


def test_ebay_merchandise_monitor_name():
    """Test EbayMerchandiseMonitor name property."""
    from agents.monitor.ebay_merchandise_monitor import EbayMerchandiseMonitor
    m = EbayMerchandiseMonitor()
    assert m.name == "ebay_merchandise"


def test_amazon_monitor_name():
    """Test AmazonMonitor name property."""
    from agents.monitor.amazon_monitor import AmazonMonitor
    m = AmazonMonitor()
    assert m.name == "amazon"


def test_jd_monitor_name():
    """Test JDMonitor name property."""
    from agents.monitor.jd_monitor import JDMonitor
    m = JDMonitor()
    assert m.name == "jd"


def test_arbitrage_detector_basic():
    """Test ArbitrageDetector finds opportunity."""
    from agents.monitor.arbitrage import ArbitrageDetector
    detector = ArbitrageDetector(threshold=0.05)
    prices = {"eBay": 150.0, "Amazon": 135.0, "JD": 140.0}
    opp = detector.find_opportunity("Test Item", prices)
    assert opp is not None
    assert opp["source_platform"] == "Amazon"
    assert opp["margin_pct"] == pytest.approx(0.10, rel=0.01)


def test_arbitrage_detector_no_opportunity():
    """Test ArbitrageDetector returns None when no opportunity."""
    from agents.monitor.arbitrage import ArbitrageDetector
    detector = ArbitrageDetector(threshold=0.15)
    prices = {"eBay": 150.0, "Amazon": 145.0}
    opp = detector.find_opportunity("Test Item", prices)
    assert opp is None


def test_arbitrage_detector_single_platform():
    """Test ArbitrageDetector returns None with single platform."""
    from agents.monitor.arbitrage import ArbitrageDetector
    detector = ArbitrageDetector(threshold=0.05)
    prices = {"eBay": 150.0}
    opp = detector.find_opportunity("Test Item", prices)
    assert opp is None
