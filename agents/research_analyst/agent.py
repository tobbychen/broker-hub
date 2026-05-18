"""Research Analyst LLM agent — enhanced with asset-class specialization."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..config import get_llm_config
from .prompts import RESEARCH_SYSTEM, format_research_prompt, format_asset_class_hint


async def research_opportunity(
    alert: dict,
    portfolio_context: str = "",
    asset_class: str = None
) -> str:
    """
    Run research analysis on an alert opportunity.

    Args:
        alert: Alert dictionary with source, symbol, details, etc.
        portfolio_context: Current portfolio state as string
        asset_class: Override asset class detection (optional)

    Returns:
        JSON-formatted research analysis with confidence and recommendation
    """
    cfg = get_llm_config()
    primary = cfg.get("primary", {})
    llm = ChatOpenAI(
        api_key=primary.get("api_key", ""),
        model=primary.get("model", "auto"),
        base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
        temperature=0.3,
    )

    # Detect asset class from alert source if not provided
    if not asset_class:
        source = alert.get("source", "").lower()
        if "akshare" in source or "yfinance" in source:
            asset_class = "stock"
        elif "binance" in source or "okx" in source or "crypto" in source:
            asset_class = "crypto"
        elif "sports_card" in source or "ebay" in source:
            asset_class = "sports_card"
        elif "merchandise" in source:
            asset_class = "merchandise"
        else:
            asset_class = "stock"

    # Add asset class hints to prompt
    asset_hint = format_asset_class_hint(asset_class)

    # Build the research prompt
    prompt = format_research_prompt(alert, portfolio_context)
    prompt += f"\n\n### 资产类别分析提示\n{asset_hint}"

    response = await llm.ainvoke([
        SystemMessage(content=RESEARCH_SYSTEM),
        HumanMessage(content=prompt),
    ])

    return response.content