---
name: parse_research_and_submit
description: Parse the research analyst output and submit a decision to the database.
category: decision
---

```python
import json
import re

async def skill_fn(research_result: str, symbol: str, asset_class: str, source: str) -> str:
    from dashboard.backend.database import create_decision

    content = research_result.strip()
    parsed = None

    if "```json" in content:
        json_str = content.split("```json")[1].split("```")[0]
        try:
            parsed = json.loads(json_str.strip())
        except json.JSONDecodeError:
            pass

    if parsed is None:
        brace_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
        if brace_match:
            try:
                parsed = json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass

    if parsed is None:
        confidence = 0.5
        risk_level = "medium"
        action = "hold"
        reason = content[:500]

        confidence_map = {"high": 0.85, "medium": 0.65, "low": 0.45}
        for kw, val in confidence_map.items():
            if kw.lower() in content.lower():
                confidence = val
                break

        if any(k in content for k in ["buy", "买入", "做多", "建议行动"]):
            action = "buy"
        elif any(k in content for k in ["sell", "卖出", "做空", "减持"]):
            action = "sell"

        if "high" in content.lower() or "高" in content:
            risk_level = "high"
        elif "low" in content.lower() or "低" in content:
            risk_level = "low"

        parsed = {
            "confidence": confidence,
            "risk_level": risk_level,
            "action": action,
            "reason": reason,
            "quantity": None,
        }

    decision_id = await create_decision(
        decision_type=parsed.get("action", "hold"),
        asset_class=asset_class,
        symbol=symbol,
        quantity=parsed.get("quantity"),
        action_price=None,
        confidence=float(parsed.get("confidence", 0.5)),
        reasoning=parsed.get("reason", content[:500]),
        risk_level=parsed.get("risk_level", "medium"),
        timeout_minutes=30,
    )

    conf = parsed.get("confidence", 0.5)
    rl = parsed.get("risk_level", "medium")
    return f"Decision submitted (ID: {decision_id}), awaiting human approval. Confidence: {conf}, Risk: {rl}"
```