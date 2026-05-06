"""Research Analyst LLM agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..config import get_llm_config

RESEARCH_SYSTEM = """你是一个专业的投资研究分析师。你的任务是：
1. 深度分析市场警报是否构成真实的投资机会
2. 收集并整合多个数据来源的信息
3. 给出置信度评估和风险评级
4. 用清晰的中文解释分析逻辑

分析维度：
- 基本面：相关新闻、宏观数据、行业趋势
- 技术面：价格走势、成交量、关键支撑/压力位
- 风险因素：市场情绪、政策风险、流动性风险

输出格式：
置信度: XX%
风险等级: low/medium/high
分析理由: ...
建议行动: buy/sell/hold
建议数量: (如适用)
"""


async def research_opportunity(alert: dict, portfolio_context: str = "") -> str:
    """Run research analysis on an alert opportunity."""
    cfg = get_llm_config()
    primary = cfg.get("primary", {})
    llm = ChatOpenAI(
        api_key=primary.get("api_key", ""),
        model=primary.get("model", "auto"),
        base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
        temperature=0.3,
    )

    prompt = f"""请分析以下投资机会：

警报详情：
- 来源: {alert.get('source')}
- 类型: {alert.get('alert_type')}
- 标的: {alert.get('symbol')}
- 交易所: {alert.get('exchange')}
- 详情: {alert.get('details')}

当前投资组合：
{portfolio_context}

请给出完整分析。"""

    response = await llm.ainvoke([
        SystemMessage(content=RESEARCH_SYSTEM),
        HumanMessage(content=prompt),
    ])

    return response.content
