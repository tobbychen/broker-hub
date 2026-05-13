"""Chat agent for Telegram bidirectional chat."""
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from agents.config import get_llm_config
from agents.dispatcher.tools import lookup_portfolio, lookup_pending_decisions
from .skills import (
    add_stock_watchlist,
    add_crypto_watchlist,
    add_sports_card_watchlist,
    add_merchandise_watchlist,
    search_and_add_stock,
    remove_from_watchlist,
    analyze_watchlist_asset,
    list_my_watchlist,
    get_latest_price,
)

logger = logging.getLogger(__name__)

CHAT_SYSTEM = """你是一个投资助手的智能聊天界面。用户通过Telegram与你对话。

你的职责：
1. 回答关于投资组合、持仓、P&L的问题
2. 回答关于待审批决策的问题
3. 解释市场警报和交易决策
4. 帮助用户理解风险和机会
5. 当用户要求添加/移除监控资产时，调用相应的技能工具

技能（自动判断是否调用）：
- get_latest_price(symbol, asset_class): 【最重要】查询资产最新价格，当用户问"xxx现在多少钱"、"xxx价格"时必须调用
- add_stock_watchlist(symbol, notes): 添加A股监控，symbol需是6位数字如'600519'
- add_crypto_watchlist(symbol, exchange): 添加加密货币监控，如'BTC'
- add_sports_card_watchlist(name, set_name, year, ...): 添加球星卡监控
- add_merchandise_watchlist(symbol, brand, model, variant, purchase_price, purchase_currency): 添加商品监控，如品牌包包、靴子、手表等
- search_and_add_stock(name): 按公司名搜索A股代码并加入监控，如"贵州茅台"
- analyze_watchlist_asset(symbol, asset_class): 分析监控列表中的某个资产，调用研究agent深度分析
- remove_from_watchlist(symbol, asset_class): 移除监控
- list_my_watchlist(): 仅当用户明确要求"列出"或"查看所有监控"时才调用

常见问价格场景：
- "BTC现在多少钱" → get_latest_price(symbol="BTC", asset_class="crypto")
- "RW-875-10D价格" → get_latest_price(symbol="RW-875-10D", asset_class="merchandise")
- "whiteboots-7.5d现在多少钱" → get_latest_price(symbol="whiteboots-7.5d", asset_class="merchandise")

规则：
- 用中文回答
- 简洁但信息丰富
- 【关键】用户问价格时必须调用get_latest_price，不要调用list_my_watchlist
- 如果不需要调用技能，直接回答用户问题
- 对于投资建议类问题，提醒用户这是参考信息，需自行判断"""


def _get_chat_llm(temperature: float = 0.5):
    """Get a ChatOpenAI instance (uses system proxy for routing)."""
    cfg = get_llm_config()
    primary = cfg.get("primary", {})
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        api_key=primary.get("api_key", ""),
        model=primary.get("model", "auto"),
        base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
        temperature=temperature,
    )


async def free_chat(message: str) -> str:
    """Handle free-form chat — LLM decides whether to call a skill tool."""
    llm = _get_chat_llm(temperature=0.5)
    bound_llm = llm.bind_tools([
        add_stock_watchlist,
        add_crypto_watchlist,
        add_sports_card_watchlist,
        add_merchandise_watchlist,
        search_and_add_stock,
        remove_from_watchlist,
        analyze_watchlist_asset,
        list_my_watchlist,
        get_latest_price,
    ])

    try:
        portfolio_str = await lookup_portfolio.ainvoke({})
    except Exception:
        portfolio_str = "无法获取投资组合信息"

    try:
        pending_str = await lookup_pending_decisions.ainvoke({})
    except Exception:
        pending_str = "无法获取待审批决策"

    response = await bound_llm.ainvoke([
        SystemMessage(content=CHAT_SYSTEM),
        HumanMessage(content=f"用户消息: {message}\n\n当前投资组合：\n{portfolio_str}\n\n待审批决策：\n{pending_str}"),
    ])

    if response.tool_calls:
        tool_map = {
            add_stock_watchlist.name: add_stock_watchlist,
            add_crypto_watchlist.name: add_crypto_watchlist,
            add_sports_card_watchlist.name: add_sports_card_watchlist,
            add_merchandise_watchlist.name: add_merchandise_watchlist,
            search_and_add_stock.name: search_and_add_stock,
            remove_from_watchlist.name: remove_from_watchlist,
            analyze_watchlist_asset.name: analyze_watchlist_asset,
            list_my_watchlist.name: list_my_watchlist,
            get_latest_price.name: get_latest_price,
        }
        for call in response.tool_calls:
            tool_name = call["name"]
            tool = tool_map.get(tool_name)
            if tool:
                result = await tool.ainvoke(call["args"])
        return result if result else "技能执行完成"

    return response.content.strip()


async def ask_decision(decision_id: int, question: str) -> str:
    """Handle decision-linked chat — user asks about a specific decision."""
    from langchain_openai import ChatOpenAI
    from agents.config import get_llm_config
    from dashboard.backend.database import get_decision_by_id, add_chat_message, get_chat_history as db_get_chat_history

    cfg = get_llm_config()
    primary = cfg.get("primary", {})
    llm = ChatOpenAI(
        api_key=primary.get("api_key", ""),
        model=primary.get("model", "auto"),
        base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
        temperature=0.3,
    )

    decision = await get_decision_by_id(decision_id)
    if not decision:
        return f"未找到决策 #{decision_id}，请检查ID是否正确。"

    history = await db_get_chat_history(decision_id)

    context = f"""决策 #{decision_id}:
- 类型: {decision.get('decision_type', '?').upper()}
- 标的: {decision.get('symbol', '?')}
- 交易所: {decision.get('exchange', '?')}
- 置信度: {decision.get('confidence', 0):.0%}
- 风险等级: {decision.get('risk_level', '?')}
- 推理: {decision.get('reasoning', '?')}
- 状态: {decision.get('status', '?')}
"""

    if history:
        chat_lines = [f"对话历史 ({len(history)} 条):"]
        for m in history[-10:]:
            role = "用户" if m.get("role") == "human" else "助手"
            chat_lines.append(f"{role}: {m.get('content', '')[:200]}")
        context += "\n" + "\n".join(chat_lines)

    response = await llm.ainvoke([
        SystemMessage(content=CHAT_SYSTEM),
        HumanMessage(content=f"用户就决策 #{decision_id} 提出问题：\n\n问题: {question}\n\n决策上下文：\n{context}"),
    ])

    try:
        await add_chat_message(decision_id, "agent", response.content.strip())
    except Exception as e:
        logger.warning(f"[chat_agent] Failed to save agent response: {e}")

    return response.content.strip()


def detect_chat_mode(message: str) -> tuple[str, dict]:
    """Detect chat mode from message content."""
    import re
    msg = message.strip()

    ask_match = re.match(r"^/ask\s+(\d+)\s+(.+)", msg)
    if ask_match:
        return "ask", {"decision_id": int(ask_match.group(1)), "question": ask_match.group(2).strip()}

    if re.match(r"^/portfolio\s*$", msg, re.IGNORECASE):
        return "portfolio", {}

    if re.match(r"^/pending\s*$", msg, re.IGNORECASE):
        return "pending", {}

    return "free", {"message": msg}
