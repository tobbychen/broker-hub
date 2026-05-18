# Agent System Improvements Plan
**Date:** 2026-05-18
**Version:** 1.0

---

## 1. Overview

Two-part improvement plan based on user priorities:
- **Part A: Technical Debt Cleanup** — Integrate unused components, fix skill duplication
- **Part B: Phase 2 Foundation** — Prepare groundwork for IBKR integration and autonomous execution

---

## 2. Part A: Technical Debt Cleanup

### 2.1 Component Integration Status

| Component | Status | Notes |
|-----------|--------|-------|
| `permission_reviewer/` | Not integrated | Full agent exists but not wired into dispatcher hooks |
| `spec_compliance/` | Not integrated | Checker exists but not used in decision flow |
| `chat_agent/skills.py` | Duplicating | Duplicates dispatcher skills |
| `dispatcher/skills/` | Main | Should be the single source of truth |

### 2.2 Issues to Fix

#### Issue 1: Skill System Duplication
**Problem:** `agents/chat_agent/skills.py` has skills that duplicate `agents/dispatcher/skills/`

**Solution:**
- Make `chat_agent/skills.py` import from `dispatcher/skills/loader.py`
- Remove duplicate skill definitions
- Use single `get_skill_loader()` as the source of truth

#### Issue 2: Permission Reviewer Not Integrated
**Problem:** `permission_reviewer/agent.py` exists but is not called anywhere

**Solution:**
- Add a permission review hook in `agents/__init__.py` or create a unified hooks module
- Wire it into the dispatcher workflow for high-risk operations
- Use during: trade execution, large position changes, autonomous decisions

#### Issue 3: Spec Compliance Checker Not Integrated
**Problem:** `spec_compliance/checker.py` exists but not used in action validation

**Solution:**
- Add spec check before high-risk actions
- Auto-activate relevant specs based on current task
- Integrate with permission reviewer

### 2.3 Implementation Steps

```
Step 1: Refactor chat_agent/skills.py
   - Remove duplicate skill functions
   - Import from dispatcher.skills.loader
   - Update chat_agent to use hot-loaded skills

Step 2: Create unified hooks module
   - agents/hooks.py
   - Combines: permission review + spec compliance
   - Provides: pre_action_check() function

Step 3: Wire hooks into dispatcher
   - Add hook call before trade execution
   - Add hook call before autonomous decisions
   - Log all hook decisions

Step 4: Update CLAUDE.md
   - Document new hooks module
   - Update integration notes
```

---

## 3. Part B: Phase 2 Foundation

### 3.1 Phase 2 Features from Design Doc

| Feature | Priority | Complexity |
|---------|----------|------------|
| IBKR integration (stocks, options, forex) | High | High |
| Small-position autonomous execution (< ¥10K) | High | Medium |
| QMT/XTP domestic broker (A-shares) | Medium | High |
| Interactive chat on dashboard | Medium | Medium |
| Sports card price alerting | Medium | Low |

### 3.2 IBKR Integration Foundation

**Current state:** No broker integration exists

**What to build:**
1. **Broker abstract interface** — Define how agents interact with brokers
2. **Mock broker implementation** — For testing without real IBKR account
3. **Position sync mechanism** — How broker positions sync to SQLite
4. **Order drafting format** — Standard order format all brokers accept

### 3.3 Autonomous Execution Foundation

**Current state:** All trades require human approval (Phase 1)

**What to build:**
1. **Confidence threshold config** — In `agent_settings.yaml`
2. **Position size limits** — Rule-based autonomy
3. **Auto-approve conditions** — When agent can execute without asking
4. **Audit logging** — Track all autonomous decisions

### 3.4 Architecture for Phase 2

```
┌─────────────────────────────────────────────────────────────┐
│                      DISPATCHER (LangGraph)                 │
├─────────────────────────────────────────────────────────────┤
│  monitor_handler → research_router → risk_manager          │
│                                    ↓                        │
│                            approval_router                  │
│                                    ↓                        │
│                      ┌─────────────────────────────────┐   │
│                      │     AUTONOMY CHECK              │   │
│                      │  - Position size < ¥10K?        │   │
│                      │  - Confidence >= 85%?           │   │
│                      │  - Risk level == low?           │   │
│                      └─────────────────────────────────┘   │
│                         ↓              ↓                    │
│               [Human Approval]    [Auto Execute]           │
└─────────────────────────────────────────────────────────────┘
                                    ↓
                      ┌─────────────────────────────────┐
                      │      BROKER ABSTRACT LAYER     │
                      ├──────────┬──────────┬──────────┤
                      │ IBKR     │ QMT/XTP  │ Binance  │
                      └──────────┴──────────┴──────────┘
```

### 3.5 Implementation Steps

```
Step 1: Create broker interface
   - agents/broker/interface.py
   - Define BrokerProtocol with: connect, get_positions, draft_order, execute
   - All broker implementations implement this interface

Step 2: Create mock broker for testing
   - agents/broker/mock.py
   - Simulates broker operations without real account
   - Used for development and testing

Step 3: Add autonomy configuration
   - config/agent_settings.yaml
   - autonomy:
     auto_approve:
       enabled: false  # Phase 1: disabled
       max_position_value: 10000  # ¥10K
       min_confidence: 0.85
       allowed_risk: ["low"]
       allowed_asset_class: ["crypto", "stock"]

Step 4: Create autonomy checker
   - agents/autonomy/checker.py
   - Check if trade meets auto-approve conditions
   - Log all decisions

Step 5: Wire autonomy into dispatcher
   - In approval_router node
   - If auto_approve conditions met → execute
   - If not → wait for human
```

---

## 4. File Structure After Changes

```
agents/
├── __init__.py                  # Exports hooks module
├── hooks.py                      # NEW: unified pre-action hooks
├── broker/
│   ├── __init__.py
│   ├── interface.py               # NEW: BrokerProtocol
│   └── mock.py                   # NEW: MockBroker for testing
├── autonomy/
│   ├── __init__.py
│   └── checker.py                # NEW: autonomy conditions checker
├── chat_agent/
│   ├── agent.py                  # Uses hot-loaded skills from dispatcher
│   ├── skills.py                 # MODIFIED: remove duplicates, import from dispatcher
│   └── ...
├── dispatcher/
│   ├── nodes.py                  # MODIFIED: call hooks before execution
│   └── skills/
│       └── loader.py             # Single source of truth for skills
├── permission_reviewer/          # INTEGRATED: wired via hooks
├── spec_compliance/              # INTEGRATED: wired via hooks
└── ...

config/
└── agent_settings.yaml           # MODIFIED: add autonomy config
```

---

## 5. Integration Points

### 5.1 Hooks Module API

```python
# agents/hooks.py

async def pre_action_check(
    action: str,           # "execute_trade", "auto_approve", "submit_decision"
    target: dict,          # Trade details or decision details
    context: dict,          # Current agent context
) -> HookResult:
    """
    Unified pre-action hook combining:
    - Permission review (LLM-based)
    - Spec compliance check
    - Autonomy conditions (Phase 2)

    Returns:
        HookResult with: approved, reason, needs_review
    """
```

### 5.2 Broker Interface API

```python
# agents/broker/interface.py

class BrokerProtocol(Protocol):
    async def connect(self) -> bool: ...
    async def get_positions(self) -> list[Position]: ...
    async def get_account_info(self) -> AccountInfo: ...
    async def draft_order(self, order: OrderDraft) -> str: ...
    async def submit_order(self, order_id: str) -> OrderResult: ...
    async def cancel_order(self, order_id: str) -> bool: ...
```

---

## 6. Backward Compatibility

- All existing code continues to work
- Hooks are additive — existing dispatcher flow unchanged unless hook returns "deny"
- Skill loading unchanged — only deduplication in chat_agent

---

## 7. Testing Strategy

| Component | Test |
|-----------|------|
| hooks.py | Test permission review, spec compliance, autonomy |
| broker/interface.py | Test protocol conformance |
| broker/mock.py | Test mock responses |
| autonomy/checker.py | Test all condition combinations |
| chat_agent/skills.py | Test skill delegation |

---

## 8. Rollout Plan

**Phase A-1:** Technical debt cleanup (Week 1)
- Day 1-2: Fix skill duplication in chat_agent
- Day 3-4: Create hooks module
- Day 5: Wire hooks into dispatcher

**Phase A-2:** Integration (Week 2)
- Day 1-2: Permission reviewer integration
- Day 3-4: Spec compliance integration
- Day 5: Testing and bug fixes

**Phase B-1:** Phase 2 foundation (Week 3-4)
- Day 1-2: Broker interface
- Day 3-4: Mock broker
- Day 5: Autonomy checker

**Phase B-2:** Integration (Week 5)
- Day 1-2: Wire autonomy into dispatcher
- Day 3-4: Configuration
- Day 5: Full testing

---

## 9. Success Criteria

### Part A (Technical Debt)
- [ ] No duplicate skill definitions
- [ ] Permission reviewer called on high-risk actions
- [ ] Spec compliance checked before spec-relevant actions
- [ ] All hooks logged for audit

### Part B (Phase 2 Foundation)
- [ ] BrokerProtocol defined and tested
- [ ] MockBroker implemented and used in tests
- [ ] Autonomy checker with all condition logic
- [ ] Configuration in agent_settings.yaml
- [ ] Autonomy wired into dispatcher (disabled by default for Phase 1)