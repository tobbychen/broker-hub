"""Telegram chat handler — routes inbound messages to the chat agent."""
import logging

from .receiver import TelegramMessage
from agents.chat_agent.agent import (
    detect_chat_mode,
    free_chat,
    ask_decision,
)
from telegram.bot import get_notifier

logger = logging.getLogger(__name__)


async def handle_telegram_message(msg: TelegramMessage) -> None:
    """
    Route an inbound Telegram message to the appropriate handler.
    Responds via TelegramSender.send_message().
    """
    notifier = get_notifier()

    mode, params = detect_chat_mode(msg.text)

    try:
        if mode == "ask":
            response = await ask_decision(
                decision_id=params["decision_id"],
                question=params["question"],
            )
        elif mode == "portfolio":
            from agents.dispatcher.tools import lookup_portfolio
            response = await lookup_portfolio.ainvoke({})
        elif mode == "pending":
            from agents.dispatcher.tools import lookup_pending_decisions
            response = await lookup_pending_decisions.ainvoke({})
        else:
            response = await free_chat(params["message"])

        await notifier.send_text(f"📩 你: {msg.text}\n\n{response}")
    except Exception as e:
        logger.error(f"[chat_handler] Error handling message: {e}")
        await notifier.send_text("抱歉，处理消息时出错，请稍后再试。")
