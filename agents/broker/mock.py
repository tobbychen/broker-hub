"""Mock broker for testing without real broker accounts."""

import logging
from datetime import datetime
from .interface import (
    BrokerProtocol,
    Position,
    AccountInfo,
    OrderDraft,
    OrderResult,
    OrderSide,
    OrderType,
)

logger = logging.getLogger(__name__)

class MockBroker:
    """Mock broker that simulates broker operations for testing."""

    def __init__(self):
        self._connected = False
        self._positions = []
        self._orders = []
        self._account = AccountInfo(
            account_id="mock-001",
            cash=100000.0,
            buying_power=100000.0,
            currency="USD",
            last_updated=datetime.now(),
        )

    @property
    def name(self) -> str:
        return "mock"

    async def connect(self) -> bool:
        logger.info("[MockBroker] Connecting...")
        import asyncio
        await asyncio.sleep(0.1)
        self._connected = True
        logger.info("[MockBroker] Connected successfully")
        return True

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("[MockBroker] Disconnected")

    async def is_connected(self) -> bool:
        return self._connected

    async def get_positions(self) -> list[Position]:
        return self._positions.copy()

    async def get_account_info(self) -> AccountInfo:
        self._account.last_updated = datetime.now()
        return self._account

    async def draft_order(self, draft: OrderDraft) -> str:
        price_type = draft.order_type.value
        price_str = f"@ ¥{draft.limit_price:.2f}" if draft.limit_price else "(市价)"
        return (
            f"订单草稿已创建 (MockBroker)\n"
            f"标的: {draft.symbol}\n"
            f"方向: {draft.side.value.upper()}\n"
            f"数量: {draft.quantity}\n"
            f"类型: {price_type} {price_str}\n"
            f"\nPhase 1 - 需要人类审批后才能执行"
        )

    async def submit_order(self, draft: OrderDraft) -> OrderResult:
        order_id = f"mock-order-{len(self._orders) + 1:04d}"
        self._orders.append({"id": order_id, "draft": draft, "status": "pending"})
        return OrderResult(
            order_id=order_id,
            status="pending",
            message="MockBroker: Order submitted (Phase 2)",
        )

    async def cancel_order(self, order_id: str) -> bool:
        for order in self._orders:
            if order["id"] == order_id and order["status"] == "pending":
                order["status"] = "cancelled"
                return True
        return False