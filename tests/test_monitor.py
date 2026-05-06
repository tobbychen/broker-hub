"""Tests for monitor modules."""
import pytest
from unittest.mock import patch, MagicMock
from agents.monitor.binance_monitor import BinanceMonitor
from agents.monitor.akshare_monitor import AKShareMonitor


def test_binance_monitor_name():
    m = BinanceMonitor()
    assert m.name == "binance"


def test_binance_monitor_market_open():
    m = BinanceMonitor()
    assert m.is_market_open() is True


@pytest.mark.asyncio
async def test_binance_monitor_disabled():
    m = BinanceMonitor()
    m.config["enabled"] = False
    alerts = await m.check()
    assert alerts == []
