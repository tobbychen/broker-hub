"""Broker implementations and registry."""

from typing import Optional

from .interface import (
    BrokerProtocol,
    Position,
    AccountInfo,
    OrderDraft,
    OrderResult,
    OrderSide,
    OrderType,
)
from .mock import MockBroker

_BROKERS = {}

def register_broker(name: str, broker: BrokerProtocol):
    _BROKERS[name] = broker

def get_broker(name: str) -> Optional[BrokerProtocol]:
    return _BROKERS.get(name)

def get_all_brokers() -> dict:
    return _BROKERS.copy()

def get_default_broker() -> Optional[BrokerProtocol]:
    return _BROKERS.get("mock")

# Register mock broker by default
register_broker("mock", MockBroker())

__all__ = [
    'BrokerProtocol', 'Position', 'AccountInfo', 'OrderDraft', 'OrderResult',
    'OrderSide', 'OrderType', 'MockBroker', 'register_broker', 'get_broker',
    'get_all_brokers', 'get_default_broker',
]