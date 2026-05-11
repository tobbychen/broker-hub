# Skill File Format

A skill is defined in a Markdown file with the following structure:

```markdown
---
name: lookup_portfolio
description: Look up the current portfolio positions across all asset classes.
category: portfolio
---

\`\`\`python
async def skill_fn():
    """Function implementation."""
    # your async code here
    return result
\`\`\`
```

## Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique skill identifier (snake_case) |
| `description` | Yes | Tool description for LLM |
| `category` | No | Category for organization (portfolio, market, decision, etc.) |

## Implementation

- The code block must contain an `async def skill_fn(...)` function
- The function can accept parameters (matched to LLM tool call args)
- Imports are allowed at the top of the code block
- The function must return a string

## Example

```markdown
---
name: get_stock_quote
description: Get current price and daily change for a stock symbol.
category: market
---

```python
import json

async def skill_fn(symbol: str):
    from dashboard.backend.database import get_market_cache

    cache = await get_market_cache(symbol, "", "latest_price")
    if not cache:
        return f"No data for {symbol}"

    raw = cache.get("raw_data", "{}")
    if isinstance(raw, str):
        raw = json.loads(raw)

    price = raw.get("price", 0)
    prev = raw.get("prev_close", 0)
    change = ((price - prev) / prev * 100) if prev else 0

    return f"{symbol}: ¥{price:.2f} ({change:+.2f}%)"
```
```