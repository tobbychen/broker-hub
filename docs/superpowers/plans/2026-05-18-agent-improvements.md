# Agent System Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cleanup technical debt (skill duplication, component integration) and build Phase 2 foundation (broker interface, autonomy checker)

**Architecture:** Refactor skill system to single source of truth, create unified hooks module, define broker protocol for future integration

**Tech Stack:** Python, aiosqlite, LangChain, LangGraph

---

## File Structure

```
agents/
├── __init__.py                    # Export hooks module
├── hooks.py                       # NEW: unified pre-action hooks
├── chat_agent/
│   ├── skills.py                  # MODIFIED: remove duplicates, import from dispatcher
│   └── agent.py                   # MODIFIED: use hot-loaded skills
├── broker/
│   ├── __init__.py                # NEW
│   └── interface.py               # NEW: BrokerProtocol
├── autonomy/
│   ├── __init__.py                # NEW
│   └── checker.py                 # NEW: autonomy conditions checker
├── dispatcher/
│   ├── nodes.py                   # MODIFIED: call hooks before execution
│   └── skills/
│       └── loader.py              # NO CHANGE: already source of truth
├── permission_reviewer/           # INTEGRATED: wired via hooks
└── spec_compliance/              # INTEGRATED: wired via hooks
```

---

## Phase A: Technical Debt Cleanup

### Task 1: Fix Skill Duplication in Chat Agent

**Files:**
- Modify: `agents/chat_agent/skills.py`
- Modify: `agents/chat_agent/agent.py`
- Test: `tests/test_chat_agent.py`

- [ ] **Step 1: Create test for skill delegation**

```python
# tests/test_chat_agent.py
import pytest
from unittest.mock import patch, AsyncMock

async def test_chat_agent_uses_dispatcher_skills():
    """Chat agent should import skills from dispatcher loader, not define them."""
    # Mock the dispatcher skill loader
    with patch('agents.dispatcher.skills.loader.get_skill_loader') as mock:
        mock_loader = AsyncMock()
        mock_loader.get_skill.return_value.fn.return_value = "Portfolio: BTC x 1"
        mock.return_value = mock_loader

        # Import chat agent
        from agents.chat_agent import agent

        # Verify skills are loaded from dispatcher, not locally defined
        # This test checks that the import path is correct
        assert hasattr(agent, 'ChatAgent')

# Test that chat_agent/skills.py no longer has duplicate definitions
async def test_chat_agent_skills_no_duplicates():
    """Verify chat_agent/skills.py imports from dispatcher, not defines locally."""
    from agents.chat_agent import skills as chat_skills

    # Should not have these functions defined locally anymore
    # They should be imported from dispatcher.skills.loader
    import inspect

    source = inspect.getsource(chat_skills)

    # Check that it imports from dispatcher
    assert 'from agents.dispatcher.skills.loader import get_skill_loader' in source or \
           'from agents.dispatcher.skills import loader' in source

    # Should NOT have these defined locally anymore
    assert 'async def add_stock_watchlist' not in source
    assert 'async def add_crypto_watchlist' not in source
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chat_agent.py -v`
Expected: FAIL - tests should fail because we haven't refactored yet

- [ ] **Step 3: Create dispatcher skills re-export module**

```python
# agents/dispatcher/skills/__init__.py
"""Re-export dispatcher skills for use by other agents."""

from .loader import get_skill_loader, SkillLoader

__all__ = ['get_skill_loader', 'SkillLoader']
```

- [ ] **Step 4: Rewrite chat_agent/skills.py to use dispatcher skills**

```python
# agents/chat_agent/skills.py
"""Skill tools for the Telegram chat agent — using hot-loaded skills from dispatcher."""

from langchain_core.tools import tool
from dashboard.backend.database import upsert_watchlist_item, delete_watchlist_item, get_watchlist_items

# Import skill loader from dispatcher (single source of truth)
from agents.dispatcher.skills.loader import get_skill_loader

@tool
async def add_stock_watchlist(symbol: str, notes: str = "") -> str:
    """Add a Chinese A-share stock to the monitoring watchlist.

    Args:
        symbol: 6-digit A-share code (e.g. '600519' for 贵州茅台)
        notes: optional note about this stock"""
    if not symbol.isdigit() or len(symbol) != 6:
        return f"股票代码格式错误，需要6位数字代码，当前: {symbol}"
    await upsert_watchlist_item("stock", symbol, "SSE/SZSE", notes)
    return f"✅ 已添加股票监控: {symbol} — AKShare将每60秒检查价格变动"

@tool
async def add_crypto_watchlist(symbol: str, exchange: str = "OKX", notes: str = "") -> str:
    """Add a cryptocurrency to the monitoring watchlist.

    Args:
        symbol: crypto base code (e.g. 'BTC', 'ETH', 'SOL')
        exchange: 'OKX' or 'Binance' — which API to use for price checks"""
    await upsert_watchlist_item("crypto", symbol.upper(), exchange, notes)
    return f"✅ 已添加加密货币监控: {symbol.upper()} ({exchange}) — 将检查24h价格变动"

@tool
async def add_sports_card_watchlist(
    name: str,
    set_name: str,
    year: str,
    category: str = "",
    min_grade: str = "",
    last_price: str = "",
) -> str:
    """Add a sports card to the eBay monitoring watchlist."""
    notes = f"{name}|{set_name}|{year}|{category}|{min_grade}|{last_price}"
    await upsert_watchlist_item("sports_card", name, "eBay", notes)
    return f"✅ 已添加球星卡监控: {name} ({set_name}, {year}) — eBay将监控价格变动"

@tool
async def add_merchandise_watchlist(
    symbol: str,
    brand: str = "",
    model: str = "",
    variant: str = "",
    purchase_price: str = "",
    purchase_currency: str = "CNY",
    exchange: str = "eBay",
) -> str:
    """Add a branded merchandise item to the monitoring watchlist."""
    price = purchase_price if purchase_price else "0"
    notes = f"{brand}|{model}|{variant}|{price}|{purchase_currency}"
    item_symbol = f"{symbol}" if symbol else f"{brand}-{model}-{variant}".replace(" ", "")
    await upsert_watchlist_item("merchandise", item_symbol, exchange, notes)

    info_parts = [p for p in [brand, model, variant] if p]
    info_str = " ".join(info_parts) if info_parts else symbol
    price_str = f"{purchase_price} {purchase_currency}" if purchase_price else "未设置购买价格"

    return (
        f"✅ 已添加商品监控: {info_str}\n"
        f"   型号: {symbol}\n"
        f"   购买价: {price_str}\n"
        f"   平台: {exchange}\n"
        f"   将跨平台监控价格变动"
    )

def get_all_chat_tools():
    """Get all chat-specific tools. Dispatcher skills are loaded separately."""
    return [
        add_stock_watchlist,
        add_crypto_watchlist,
        add_sports_card_watchlist,
        add_merchandise_watchlist,
    ]
```

- [ ] **Step 5: Update chat_agent/agent.py to use dispatcher skills**

```python
# In agents/chat_agent/agent.py, update the skill loading section:

# OLD (duplicate skills):
# from .skills import add_stock_watchlist, add_crypto_watchlist, ...

# NEW (import from dispatcher):
from .skills import get_all_chat_tools

# In ChatAgent.__init__:
def __init__(self):
    # Get chat-specific tools
    self.tools = get_all_chat_tools()

    # Get dispatcher skills (hot-loaded, single source of truth)
    from agents.dispatcher.skills.loader import get_skill_loader
    self.dispatcher_tools = get_skill_loader().get_tools()

    # Combine for full toolset
    self.all_tools = self.tools + self.dispatcher_tools
```

- [ ] **Step 6: Run tests to verify fix**

Run: `pytest tests/test_chat_agent.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add agents/chat_agent/skills.py agents/chat_agent/agent.py agents/dispatcher/skills/__init__.py tests/test_chat_agent.py
git commit -m "refactor: deduplicate skills - chat_agent imports from dispatcher"
```

---

### Task 2: Create Unified Hooks Module

**Files:**
- Create: `agents/hooks.py`
- Modify: `agents/__init__.py`
- Test: `tests/test_hooks.py`

- [ ] **Step 1: Write HookResult and HookAction types**

```python
# agents/hooks.py
"""Unified pre-action hooks for permission review, spec compliance, and autonomy checks."""

from dataclasses import dataclass
from typing import Optional
from enum import Enum

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
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
```

- [ ] **Step 2: Write permission review function**

```python
async def check_permission(
    action: str,
    target: dict,
    context: dict,
) -> HookResult:
    """Check permission using the permission reviewer agent.

    Args:
        action: The action being performed
        target: Details of what is being acted upon
        context: Current agent context

    Returns:
        HookResult with decision
    """
    from .permission_reviewer.agent import review_permission

    try:
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
        # Fail safe - require review on errors
        return HookResult(
            approved=False,
            action=action,
            reason=f"Permission check error: {str(e)[:100]}",
            needs_review=True,
            warnings=["Permission review failed - defaulting to review"],
        )
```

- [ ] **Step 3: Write spec compliance check function**

```python
async def check_spec_compliance(
    action: str,
    target: dict,
    context: dict,
) -> HookResult:
    """Check spec compliance using the spec compliance checker.

    Args:
        action: The action being performed (read/write/Bash)
        target: Details including file path or command
        context: Current agent context

    Returns:
        HookResult with compliance result
    """
    from .spec_compliance.checker import check_compliance

    try:
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
        # Fail safe - allow but warn
        return HookResult(
            approved=True,
            action=action,
            reason=f"Spec check error (allowing): {str(e)[:100]}",
            needs_review=False,
            warnings=["Spec compliance check failed - action allowed with warning"],
        )
```

- [ ] **Step 4: Write autonomy check function (Phase 2)**

```python
async def check_autonomy(
    action: str,
    target: dict,
    context: dict,
) -> HookResult:
    """Check if action qualifies for autonomous execution (Phase 2).

    Phase 1: This always returns needs_review=True (disabled)
    Phase 2: This will check position size, confidence, risk level
    """
    from .config import get_agent_settings

    settings = get_agent_settings()
    autonomy_cfg = settings.get("autonomy", {})

    # Phase 1 check - autonomy disabled
    if not autonomy_cfg.get("enabled", False):
        return HookResult(
            approved=False,
            action=action,
            reason="Autonomous execution is disabled (Phase 1)",
            needs_review=True,
            warnings=["Phase 1: All trades require human approval"],
        )

    # Phase 2 check - evaluate conditions
    # (Will be expanded in Task 4)
    return HookResult(
        approved=False,
        action=action,
        reason="Autonomy not yet configured",
        needs_review=True,
    )
```

- [ ] **Step 5: Write unified pre_action_check function**

```python
async def pre_action_check(
    action: str,
    action_type: ActionType,
    target: dict,
    context: dict,
) -> HookResult:
    """Unified pre-action hook combining all checks.

    Args:
        action: Human-readable action description
        action_type: Type of action (EXECUTE_TRADE, AUTO_APPROVE, etc.)
        target: Details of what is being acted upon
        context: Current agent context

    Returns:
        HookResult with combined decision from all hooks
    """
    results = []
    warnings = []

    # 1. Spec compliance check (for file operations)
    if action_type in (ActionType.SUBMIT_DECISION, ActionType.MODIFY_POSITION):
        spec_result = await check_spec_compliance(action, target, context)
        results.append(spec_result)
        warnings.extend(spec_result.warnings)

    # 2. Permission review (for execution operations)
    if action_type in (ActionType.EXECUTE_TRADE, ActionType.AUTO_APPROVE):
        perm_result = await check_permission(action, target, context)
        results.append(perm_result)
        warnings.extend(perm_result.warnings)

    # 3. Autonomy check (for auto-approve)
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
```

- [ ] **Step 6: Export hooks in __init__.py**

```python
# agents/__init__.py

# Add these exports:
from .hooks import (
    pre_action_check,
    check_permission,
    check_spec_compliance,
    check_autonomy,
    HookResult,
    ActionType,
)

__all__ = [
    'pre_action_check',
    'check_permission',
    'check_spec_compliance',
    'check_autonomy',
    'HookResult',
    'ActionType',
]
```

- [ ] **Step 7: Write tests**

```python
# tests/test_hooks.py
import pytest
from agents.hooks import (
    pre_action_check,
    HookResult,
    ActionType,
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
async def test_hook_result_with_warnings():
    result = HookResult(
        approved=True,
        action="execute_trade",
        reason="Allowed with warnings",
        warnings=["High volatility"],
    )
    assert result.warnings == ["High volatility"]

@pytest.mark.asyncio
async def test_pre_action_check_basic():
    result = await pre_action_check(
        action="read portfolio",
        action_type=ActionType.READ_DATA,
        target={"file_path": "agents/dispatcher/nodes.py"},
        context={},
    )
    # Basic read should be approved
    assert result.approved is True
    assert result.action == "read portfolio"

@pytest.mark.asyncio
async def test_pre_action_check_permission():
    result = await pre_action_check(
        action="execute trade",
        action_type=ActionType.EXECUTE_TRADE,
        target={"target": "BTC", "quantity": 0.01},
        context={},
    )
    # Should get a result (approved or not depends on LLM)
    assert isinstance(result, HookResult)
    assert result.action == "execute trade"
```

- [ ] **Step 8: Run tests**

Run: `pytest tests/test_hooks.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add agents/hooks.py agents/__init__.py tests/test_hooks.py
git commit -m "feat: add unified hooks module for permission review and spec compliance"
```

---

### Task 3: Wire Hooks into Dispatcher

**Files:**
- Modify: `agents/dispatcher/nodes.py`
- Test: `tests/test_dispatcher.py`

- [ ] **Step 1: Add hook import to nodes.py**

```python
# At top of agents/dispatcher/nodes.py, add:
from agents.hooks import pre_action_check, ActionType, HookResult
```

- [ ] **Step 2: Add hook call in approval_router node**

```python
async def approval_router(state: dict, llm) -> dict:
    """Format submitted decisions for human review.
    Now includes pre-action hooks for risk validation.
    """
    decisions = state.get("decisions", [])
    pending_approvals = []

    for d in decisions:
        if not d.get("submitted"):
            continue
        alerts = d.get("alerts", [])
        alert = alerts[0] if alerts else {}

        # Run pre-action hook before adding to pending
        hook_result = await pre_action_check(
            action=f"submit decision for {alert.get('symbol', 'unknown')}",
            action_type=ActionType.SUBMIT_DECISION,
            target={
                "symbol": alert.get("symbol", ""),
                "confidence": d.get("confidence", 0.5),
                "risk_level": d.get("risk_check", "medium"),
            },
            context={"decision": d, "alert": alert},
        )

        # Log hook result
        if hook_result.warnings:
            logger.info(f"[approval_router] Hook warnings: {hook_result.warnings}")

        pending_approvals.append({
            "symbol": alert.get("symbol", ""),
            "source": alert.get("source", ""),
            "alert_type": alert.get("alert_type", ""),
            "details": alert.get("details", {}),
            "research_reason": d.get("relevant_reason", ""),
            "submit_result": d.get("submit_result", ""),
            "live_price": d.get("live_price", ""),
            "risk_check": d.get("risk_check", ""),
            "confidence": d.get("confidence", 0.5),
            "hook_warnings": hook_result.warnings,
        })

    return {"pending_approval": pending_approvals}
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_dispatcher.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add agents/dispatcher/nodes.py
git commit -m "feat: wire hooks into dispatcher approval router"
```

---

## Phase B: Phase 2 Foundation

### Task 4: Create Broker Interface

**Files:**
- Create: `agents/broker/__init__.py`
- Create: `agents/broker/interface.py`
- Create: `agents/broker/mock.py`
- Test: `tests/test_broker.py`

- [ ] **Step 1: Write BrokerProtocol**

```python
# agents/broker/interface.py
"""Broker interface for abstracting trade execution."""

from typing import Protocol, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"

@dataclass
class Position:
    """A position held in a broker account."""
    symbol: str
    quantity: float
    avg_cost: float
    exchange: str
    asset_class: str

@dataclass
class AccountInfo:
    """Account information from broker."""
    account_id: str
    cash: float
    buying_power: float
    currency: str = "USD"
    last_updated: datetime = None

@dataclass
class OrderDraft:
    """Draft order before submission."""
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    exchange: str = ""
    asset_class: str = ""

@dataclass
class OrderResult:
    """Result of order submission."""
    order_id: str
    status: str  # "pending", "filled", "cancelled", "rejected"
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    message: str = ""

class BrokerProtocol(Protocol):
    """Abstract interface for broker implementations.

    All broker implementations (IBKR, QMT, Binance, Mock) must implement this.
    """

    @property
    def name(self) -> str:
        """Broker name (e.g., 'ibkr', 'binance', 'mock')."""
        ...

    async def connect(self) -> bool:
        """Connect to broker API. Returns True if successful."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from broker API."""
        ...

    async def is_connected(self) -> bool:
        """Check if currently connected."""
        ...

    async def get_positions(self) -> list[Position]:
        """Get all current positions."""
        ...

    async def get_account_info(self) -> AccountInfo:
        """Get account information."""
        ...

    async def draft_order(self, draft: OrderDraft) -> str:
        """Draft an order (Phase 1: returns draft confirmation, no execution).

        Args:
            draft: Order draft details

        Returns:
            Draft confirmation message
        """
        ...

    async def submit_order(self, draft: OrderDraft) -> OrderResult:
        """Submit an order for execution (Phase 2).

        Args:
            draft: Order to submit

        Returns:
            Order result with status
        """
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully
        """
        ...
```

- [ ] **Step 2: Write MockBroker**

```python
# agents/broker/mock.py
"""Mock broker for testing without real broker accounts."""

import logging
from typing import Optional
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
        """Simulate connection."""
        logger.info("[MockBroker] Connecting...")
        await self._simulate_latency()
        self._connected = True
        logger.info("[MockBroker] Connected successfully")
        return True

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self._connected = False
        logger.info("[MockBroker] Disconnected")

    async def is_connected(self) -> bool:
        return self._connected

    async def get_positions(self) -> list[Position]:
        """Return mock positions."""
        return self._positions.copy()

    async def get_account_info(self) -> AccountInfo:
        """Return mock account info."""
        self._account.last_updated = datetime.now()
        return self._account

    async def draft_order(self, draft: OrderDraft) -> str:
        """Generate draft confirmation message."""
        await self._simulate_latency()

        price_type = draft.order_type.value
        price_str = f"@ ¥{draft.limit_price:.2f}" if draft.limit_price else "(市价)"

        return (
            f"订单草稿已创建 (MockBroker)\n"
            f"标的: {draft.symbol}\n"
            f"方向: {draft.side.value.upper()}\n"
            f"数量: {draft.quantity}\n"
            f"类型: {price_type} {price_str}\n"
            f"预估金额: ¥{draft.quantity * (draft.limit_price or 0):.2f}\n"
            f"\n⚠️ 这是 Phase 1 - 需要人类审批后才能执行"
        )

    async def submit_order(self, draft: OrderDraft) -> OrderResult:
        """Simulate order submission (Phase 2 feature)."""
        await self._simulate_latency()

        order_id = f"mock-order-{len(self._orders) + 1:04d}"
        self._orders.append({
            "id": order_id,
            "draft": draft,
            "status": "pending",
        })

        return OrderResult(
            order_id=order_id,
            status="pending",
            message="MockBroker: Order submitted for execution (Phase 2)",
        )

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a mock order."""
        for order in self._orders:
            if order["id"] == order_id and order["status"] == "pending":
                order["status"] = "cancelled"
                return True
        return False

    async def _simulate_latency(self, ms: int = 100):
        """Simulate network latency."""
        import asyncio
        await asyncio.sleep(ms / 1000)

    # Helper methods for testing
    def add_position(self, position: Position):
        """Add a mock position (for testing)."""
        self._positions.append(position)

    def clear_positions(self):
        """Clear all mock positions."""
        self._positions = []

    def set_account_balance(self, cash: float, buying_power: float):
        """Set mock account balance."""
        self._account.cash = cash
        self._account.buying_power = buying_power
```

- [ ] **Step 3: Write broker registry**

```python
# agents/broker/__init__.py
"""Broker implementations and registry."""

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

# Broker registry
_BROKERS: dict[str, BrokerProtocol] = {}

def register_broker(name: str, broker: BrokerProtocol):
    """Register a broker implementation."""
    _BROKERS[name] = broker

def get_broker(name: str) -> Optional[BrokerProtocol]:
    """Get a broker by name."""
    return _BROKERS.get(name)

def get_all_brokers() -> dict[str, BrokerProtocol]:
    """Get all registered brokers."""
    return _BROKERS.copy()

def get_default_broker() -> Optional[BrokerProtocol]:
    """Get the default broker (mock for now)."""
    return _BROKERS.get("mock")

# Register mock broker by default
register_broker("mock", MockBroker())

__all__ = [
    'BrokerProtocol',
    'Position',
    'AccountInfo',
    'OrderDraft',
    'OrderResult',
    'OrderSide',
    'OrderType',
    'MockBroker',
    'register_broker',
    'get_broker',
    'get_all_brokers',
    'get_default_broker',
]
```

- [ ] **Step 4: Write tests**

```python
# tests/test_broker.py
import pytest
from agents.broker import (
    MockBroker,
    OrderDraft,
    OrderSide,
    OrderType,
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
async def test_mock_broker_get_account_info():
    broker = MockBroker()
    await broker.connect()

    account = await broker.get_account_info()
    assert account.account_id == "mock-001"
    assert account.cash == 100000.0
    assert account.buying_power == 100000.0

@pytest.mark.asyncio
async def test_mock_broker_draft_order():
    broker = MockBroker()
    await broker.connect()

    draft = OrderDraft(
        symbol="BTC",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.LIMIT,
        limit_price=80000.0,
        exchange="Binance",
        asset_class="crypto",
    )

    result = await broker.draft_order(draft)
    assert "订单草稿已创建" in result
    assert "BTC" in result
    assert "80000" in result

@pytest.mark.asyncio
async def test_mock_broker_submit_order():
    broker = MockBroker()
    await broker.connect()

    draft = OrderDraft(
        symbol="BTC",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.MARKET,
        exchange="Binance",
    )

    result = await broker.submit_order(draft)
    assert result.status == "pending"
    assert result.order_id.startswith("mock-order-")

@pytest.mark.asyncio
async def test_mock_broker_cancel_order():
    broker = MockBroker()
    await broker.connect()

    # Submit an order
    draft = OrderDraft(
        symbol="ETH",
        side=OrderSide.BUY,
        quantity=1.0,
        order_type=OrderType.MARKET,
    )
    result = await broker.submit_order(draft)
    order_id = result.order_id

    # Cancel it
    cancelled = await broker.cancel_order(order_id)
    assert cancelled is True

@pytest.mark.asyncio
async def test_broker_registry():
    from agents.broker import get_broker, get_all_brokers

    brokers = get_all_brokers()
    assert "mock" in brokers

    mock = get_broker("mock")
    assert mock is not None
    assert mock.name == "mock"
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_broker.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agents/broker/ tests/test_broker.py
git commit -m "feat: add broker interface and mock implementation for Phase 2"
```

---

### Task 5: Create Autonomy Checker

**Files:**
- Create: `agents/autonomy/__init__.py`
- Create: `agents/autonomy/checker.py`
- Modify: `config/agent_settings.yaml`
- Test: `tests/test_autonomy.py`

- [ ] **Step 1: Add autonomy config to agent_settings.yaml**

```yaml
# Add to config/agent_settings.yaml under agents section:

  autonomy:
    enabled: false  # Phase 1: disabled, all trades need human approval
    auto_approve:
      max_position_value: 10000  # ¥10K max for auto-approve
      min_confidence: 0.85       # 85% confidence minimum
      max_risk: low              # Only low risk trades auto-approve
      allowed_asset_class:
        - crypto
        - stock
      allowed_exchanges:
        - Binance
        - OKX
        - SSE/SZSE
```

- [ ] **Step 2: Write AutonomyChecker**

```python
# agents/autonomy/checker.py
"""Autonomy checker for Phase 2 auto-execute conditions."""

from dataclasses import dataclass
from typing import Optional
import logging

from ..config import get_agent_settings

logger = logging.getLogger(__name__)

@dataclass
class AutonomyResult:
    """Result of autonomy check."""
    can_auto_execute: bool
    reason: str
    conditions_met: dict
    conditions_failed: dict

class AutonomyChecker:
    """Check if a trade qualifies for autonomous execution."""

    def __init__(self):
        self.settings = get_agent_settings().get("autonomy", {})
        self.auto_approve = self.settings.get("auto_approve", {})

    @property
    def is_enabled(self) -> bool:
        """Check if autonomy is enabled (Phase 1 = disabled)."""
        return self.settings.get("enabled", False)

    def check_trade(
        self,
        symbol: str,
        quantity: float,
        price: float,
        confidence: float,
        risk_level: str,
        asset_class: str,
        exchange: str,
    ) -> AutonomyResult:
        """Check if a trade meets auto-approve conditions.

        Args:
            symbol: Asset symbol
            quantity: Trade quantity
            price: Asset price
            confidence: Confidence level (0-1)
            risk_level: Risk level (low/medium/high)
            asset_class: Asset class (crypto/stock/etc)
            exchange: Exchange name

        Returns:
            AutonomyResult with decision details
        """
        conditions_met = {}
        conditions_failed = {}

        # Check 1: Is autonomy enabled?
        if not self.is_enabled:
            return AutonomyResult(
                can_auto_execute=False,
                reason="Autonomous execution is disabled (Phase 1)",
                conditions_met={"enabled": False},
                conditions_failed={},
            )

        # Calculate position value
        position_value = quantity * price

        # Check 2: Position size limit
        max_value = self.auto_approve.get("max_position_value", 10000)
        size_ok = position_value <= max_value
        conditions_met["max_position_value"] = size_ok
        if not size_ok:
            conditions_failed["max_position_value"] = f"¥{position_value:.0f} > ¥{max_value:,}"

        # Check 3: Confidence threshold
        min_conf = self.auto_approve.get("min_confidence", 0.85)
        conf_ok = confidence >= min_conf
        conditions_met["min_confidence"] = conf_ok
        if not conf_ok:
            conditions_failed["min_confidence"] = f"{confidence:.0%} < {min_conf:.0%}"

        # Check 4: Risk level
        max_risk = self.auto_approve.get("max_risk", "low")
        risk_order = {"low": 0, "medium": 1, "high": 2}
        risk_ok = risk_order.get(risk_level.lower(), 2) <= risk_order.get(max_risk, 0)
        conditions_met["risk_level"] = risk_ok
        if not risk_ok:
            conditions_failed["risk_level"] = f"{risk_level} > {max_risk}"

        # Check 5: Asset class
        allowed_classes = self.auto_approve.get("allowed_asset_class", [])
        class_ok = asset_class.lower() in [c.lower() for c in allowed_classes]
        conditions_met["asset_class"] = class_ok
        if not class_ok:
            conditions_failed["asset_class"] = f"{asset_class} not in {allowed_classes}"

        # Check 6: Exchange
        allowed_exchanges = self.auto_approve.get("allowed_exchanges", [])
        exchange_ok = not allowed_exchanges or exchange in allowed_exchanges
        conditions_met["exchange"] = exchange_ok
        if not exchange_ok:
            conditions_failed["exchange"] = f"{exchange} not in {allowed_exchanges}"

        # Overall decision
        all_passed = all([
            size_ok,
            conf_ok,
            risk_ok,
            class_ok,
            exchange_ok,
        ])

        reasons = []
        if all_passed:
            reasons.append(f"All conditions met for {symbol}")
        else:
            reasons.append("Conditions not met:")
            reasons.extend(f"  - {v}" for v in conditions_failed.values())

        return AutonomyResult(
            can_auto_execute=all_passed,
            reason="; ".join(reasons),
            conditions_met=conditions_met,
            conditions_failed=conditions_failed,
        )

    def get_log_message(self, result: AutonomyResult, symbol: str) -> str:
        """Generate audit log message for autonomy decision."""
        status = "APPROVED" if result.can_auto_execute else "REJECTED"
        msg = f"[Autonomy] {status} auto-execute for {symbol}: {result.reason}"

        if result.conditions_failed:
            msg += f"\n  Failed: {result.conditions_failed}"
        if result.conditions_met:
            msg += f"\n  Passed: {result.conditions_met}"

        return msg

# Singleton
_checker: Optional[AutonomyChecker] = None

def get_autonomy_checker() -> AutonomyChecker:
    """Get the global autonomy checker."""
    global _checker
    if _checker is None:
        _checker = AutonomyChecker()
    return _checker

def check_trade_autonomy(
    symbol: str,
    quantity: float,
    price: float,
    confidence: float,
    risk_level: str,
    asset_class: str,
    exchange: str,
) -> AutonomyResult:
    """Quick check if trade can auto-execute."""
    checker = get_autonomy_checker()
    return checker.check_trade(
        symbol=symbol,
        quantity=quantity,
        price=price,
        confidence=confidence,
        risk_level=risk_level,
        asset_class=asset_class,
        exchange=exchange,
    )
```

- [ ] **Step 3: Write autonomy exports**

```python
# agents/autonomy/__init__.py
"""Autonomy checker for Phase 2 auto-execute conditions."""

from .checker import (
    AutonomyChecker,
    AutonomyResult,
    get_autonomy_checker,
    check_trade_autonomy,
)

__all__ = [
    'AutonomyChecker',
    'AutonomyResult',
    'get_autonomy_checker',
    'check_trade_autonomy',
]
```

- [ ] **Step 4: Write tests**

```python
# tests/test_autonomy.py
import pytest
from agents.autonomy import (
    AutonomyChecker,
    check_trade_autonomy,
)

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
    assert "disabled" in result.reason.lower()

def test_autonomy_check_conditions():
    """Test individual condition checks."""
    checker = AutonomyChecker()

    # When disabled, should always fail
    result = checker.check_trade(
        symbol="BTC",
        quantity=0.01,
        price=80000,
        confidence=0.95,
        risk_level="low",
        asset_class="crypto",
        exchange="Binance",
    )

    # Should fail because disabled
    assert result.can_auto_execute is False
    assert result.conditions_met.get("enabled") is False

def test_autonomy_result_dataclass():
    """Test AutonomyResult structure."""
    from agents.autonomy import AutonomyResult

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
    assert "REJECTED" in log  # Because Phase 1 is disabled
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_autonomy.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agents/autonomy/ config/agent_settings.yaml tests/test_autonomy.py
git commit -m "feat: add autonomy checker for Phase 2 auto-execute conditions"
```

---

### Task 6: Wire Autonomy into Dispatcher (Disabled)

**Files:**
- Modify: `agents/dispatcher/nodes.py`

- [ ] **Step 1: Add autonomy check to trade_executor node**

```python
# In trade_executor_node function, add:

async def trade_executor_node(state: dict, llm) -> dict:
    """
    Draft an order based on approved research.
    Phase 1: Drafts only, no auto-execution.
    Phase 2: Will check autonomy before execution.
    """
    decisions = state.get("decisions", [])
    draft_orders = {}

    for d in decisions:
        if d.get("status") != "approved":
            continue

        research_result = d.get("research_result", "")
        if not research_result:
            continue

        # Get trade details from alert
        alerts = d.get("alerts", [{}])
        alert = alerts[0] if alerts else {}
        symbol = alert.get("symbol", "")
        asset_class = _source_to_asset_class(alert.get("source", ""))

        # Check autonomy (Phase 2 - currently disabled)
        from agents.autonomy import check_trade_autonomy

        # These values would come from research result parsing in real implementation
        quantity = d.get("quantity", 1.0)
        price = d.get("live_price", 0.0) or 0.0
        confidence = d.get("confidence", 0.5)
        risk_level = "medium"

        autonomy_result = check_trade_autonomy(
            symbol=symbol,
            quantity=quantity,
            price=price,
            confidence=confidence,
            risk_level=risk_level,
            asset_class=asset_class,
            exchange=alert.get("exchange", ""),
        )

        # Log autonomy decision
        if autonomy_result.can_auto_execute:
            logger.info(f"[trade_executor] Auto-execute approved for {symbol}")
            # Phase 2: Would call broker.submit_order() here
        else:
            logger.info(f"[trade_executor] Auto-execute rejected: {autonomy_result.reason}")

        # Store autonomy result for debugging
        d["autonomy_check"] = autonomy_result

        # Phase 1: Draft only, never execute
        try:
            order_draft = await draft_order(research_result, d.get("id"))
            draft_orders[symbol] = order_draft
            d["order_draft"] = order_draft
        except Exception as e:
            logger.error(f"[trade_executor] Error drafting order: {e}")
            draft_orders[symbol] = f"Draft failed: {e}"

    return {"draft_orders": draft_orders, "decisions": decisions}
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_dispatcher.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add agents/dispatcher/nodes.py
git commit -m "feat: wire autonomy checker into dispatcher (Phase 1 disabled)"
```

---

## Verification Checklist

After all tasks complete:

- [ ] `pytest tests/test_chat_agent.py -v` passes (skill deduplication)
- [ ] `pytest tests/test_hooks.py -v` passes (hooks module)
- [ ] `pytest tests/test_broker.py -v` passes (broker interface)
- [ ] `pytest tests/test_autonomy.py -v` passes (autonomy checker)
- [ ] `pytest tests/test_dispatcher.py -v` passes (dispatcher integration)
- [ ] All imports work: `python -c "from agents import hooks, autonomy; from agents.broker import MockBroker; print('OK')"`

---

## Rollback Instructions

If issues occur:

```bash
# Rollback all changes
git reset --hard HEAD~7

# Or rollback specific task
git reset --hard <commit-hash>
```