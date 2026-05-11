---
name: lookup_pending_decisions
description: Look up all pending decisions awaiting human approval.
category: decision
---

```python
async def skill_fn() -> str:
    """Return list of pending decisions as formatted string."""
    from dashboard.backend.database import get_pending_decisions

    decisions = await get_pending_decisions()
    if not decisions:
        return "暂无待审批决策"

    lines = [f"共 {len(decisions)} 条待审批:"]
    for d in decisions:
        lines.append(
            f"- [{d['id']}] {d['decision_type'].upper()} {d['symbol']} "
            f"@ {d.get('action_price', '市价')} "
            f"(置信度: {d['confidence']:.0%}, 风险: {d['risk_level']})"
        )
    return "\n".join(lines)
```