"""Trade Executor agent — drafts orders, does not execute without approval."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..config import get_llm_config

EXECUTION_SYSTEM = """你是一个交易执行专家。你的职责是：
1. 根据研究分析结果起草交易订单
2. 订单必须包含：标的、数量、价格（或市价）、交易所
3. 所有订单必须标注"待人类审批" — 永远不要假设已获批准
4. 用中文输出订单详情

Phase 1 规则：所有订单都需要人类批准后才能执行。永远不要执行未经批准的订单。"""


async def draft_order(research_result: str) -> str:
    """Draft a trade order based on research. Does NOT execute."""
    cfg = get_llm_config()
    primary = cfg.get("primary", {})
    llm = ChatOpenAI(
        api_key=primary.get("api_key", ""),
        model=primary.get("model", "auto"),
        base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
        temperature=0.2,
    )

    prompt = f"""基于以下研究分析结果，起草交易订单：

{research_result}

注意：这是 Phase 1，所有订单都需要人类批准后才能执行。
请起草订单详情，标注[待审批]。"""

    response = await llm.ainvoke([
        SystemMessage(content=EXECUTION_SYSTEM),
        HumanMessage(content=prompt),
    ])

    return response.content
