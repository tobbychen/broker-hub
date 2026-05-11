---
name: lookup_portfolio
description: Look up the current portfolio positions across all asset classes.
category: portfolio
---

```python
async def skill_fn():
    """Return current portfolio positions as formatted string."""
    from dashboard.backend.database import get_all_positions

    positions = await get_all_positions()
    if not positions:
        return "投资组合为空，当前无持仓"

    lines = []
    for p in positions:
        val = p["quantity"] * p["avg_cost"]
        lines.append(
            f"- {p['asset_class']}: {p['symbol']} x {p['quantity']} "
            f"@ ¥{p['avg_cost']:.2f} = ¥{val:.2f}"
        )
    return "\n".join(lines)
```