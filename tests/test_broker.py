import pytest
from agents.broker import (
    MockBroker, OrderDraft, OrderSide, OrderType,
    get_broker, get_all_brokers,
)

@pytest.mark.asyncio
async def test_mock_broker_connect():
    broker = MockBroker()
    assert await broker.is_connected() is False
    result = await broker.connect()
    assert result is True
    assert await broker.is_connected() is True

@pytest.mark.asyncio
async def test_mock_broker_disconnect():
    broker = MockBroker()
    await broker.connect()
    await broker.disconnect()
    assert await broker.is_connected() is False

@pytest.mark.asyncio
async def test_mock_broker_account():
    broker = MockBroker()
    await broker.connect()
    account = await broker.get_account_info()
    assert account.account_id == "mock-001"
    assert account.cash == 100000.0

@pytest.mark.asyncio
async def test_mock_broker_draft_order():
    broker = MockBroker()
    await broker.connect()
    draft = OrderDraft(
        symbol="BTC", side=OrderSide.BUY, quantity=0.01,
        order_type=OrderType.LIMIT, limit_price=80000.0,
    )
    result = await broker.draft_order(draft)
    assert "BTC" in result
    assert "80000" in result

@pytest.mark.asyncio
async def test_mock_broker_submit():
    broker = MockBroker()
    await broker.connect()
    draft = OrderDraft(symbol="ETH", side=OrderSide.BUY, quantity=1.0, order_type=OrderType.MARKET)
    result = await broker.submit_order(draft)
    assert result.status == "pending"
    assert result.order_id.startswith("mock-order-")

@pytest.mark.asyncio
async def test_mock_broker_cancel():
    broker = MockBroker()
    await broker.connect()
    draft = OrderDraft(symbol="SOL", side=OrderSide.BUY, quantity=10.0, order_type=OrderType.MARKET)
    result = await broker.submit_order(draft)
    cancelled = await broker.cancel_order(result.order_id)
    assert cancelled is True

@pytest.mark.asyncio
async def test_broker_registry():
    brokers = get_all_brokers()
    assert "mock" in brokers
    mock = get_broker("mock")
    assert mock is not None
    assert mock.name == "mock"