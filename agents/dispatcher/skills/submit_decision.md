---
name: submit_decision
description: Submit a new trading decision for human approval.
category: decision
---

```python
import json
import re

async def skill_fn(
    decision_type: str,
    asset_class: str,
    symbol: str,
    exchange: str = "",
    quantity: float = None,
    action_price: float = None,
    confidence: float = 0.5,
    reasoning: str = "",
    risk_level: str = "medium"
) -> str:
    """Submit a decision to the database for human review."""
    from dashboard.backend.database import create_decision

    decision_id = await create_decision(
        decision_type=decision_type,
        asset_class=asset_class,
        symbol=symbol,
        quantity=quantity,
        action_price=action_price,
        confidence=confidence,
        reasoning=reasoning,
        risk_level=risk_level,
        timeout_minutes=30,
    )
    return f"决策已提交 (ID: {decision_id})，等待人类审批"
```