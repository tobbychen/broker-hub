"""Trade Executor agent — drafts orders, does not execute without approval."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..config import get_llm_config
from .prompts import EXECUTION_SYSTEM, format_order_draft_prompt


async def draft_order(research_result: str, decision_id: int = None) -> str:
    """
    Draft a trade order based on research. Does NOT execute.

    Args:
        research_result: JSON-formatted research analysis from Research Analyst
        decision_id: Optional decision ID for tracking

    Returns:
        Drafted order with approval requirements
    """
    cfg = get_llm_config()
    primary = cfg.get("primary", {})
    llm = ChatOpenAI(
        api_key=primary.get("api_key", ""),
        model=primary.get("model", "auto"),
        base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
        temperature=0.2,
    )

    prompt = format_order_draft_prompt(research_result)

    response = await llm.ainvoke([
        SystemMessage(content=EXECUTION_SYSTEM),
        HumanMessage(content=prompt),
    ])

    # Add decision ID tracking if provided
    result = response.content
    if decision_id:
        result += f"\n\n[Decision ID: {decision_id}]"

    return result