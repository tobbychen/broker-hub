"""Telegram message receiver via long-polling getUpdates."""
import logging
import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class TelegramMessage:
    message_id: int
    chat_id: int
    text: str
    first_name: str = ""
    username: str = ""


def _detect_proxy() -> Optional[str]:
    import os
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        val = os.environ.get(var)
        if val:
            return val
    return None


async def poll_messages(
    bot_token: str,
    offset: int = 0,
    timeout: int = 30,
    proxy: Optional[str] = None,
) -> tuple[list[TelegramMessage], int]:
    """
    Poll Telegram for new messages via getUpdates.
    Returns (list of messages, next offset).
    """
    if not bot_token:
        return [], offset

    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {"timeout": timeout, "offset": offset}
    messages = []
    next_offset = offset

    try:
        async with httpx.AsyncClient(proxy=proxy, timeout=timeout + 5) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"[telegram] getUpdates failed: {resp.status_code}")
                return [], offset

            data = resp.json()
            if not data.get("ok"):
                logger.warning(f"[telegram] getUpdates not ok: {data}")
                return [], offset

            updates = data.get("result", [])
            if not updates:
                return [], offset

            for update in updates:
                msg = update.get("message", {})
                if not msg:
                    continue

                msg_id = update.get("update_id", 0)
                chat = msg.get("chat", {})
                text = msg.get("text", "") or msg.get("caption", "")

                # Skip non-text messages
                if not text:
                    continue

                messages.append(TelegramMessage(
                    message_id=msg_id,
                    chat_id=chat.get("id", 0),
                    text=text.strip(),
                    first_name=chat.get("first_name", ""),
                    username=chat.get("username", ""),
                ))

                # Update offset to acknowledge this message
                next_offset = msg_id + 1

            return messages, next_offset

    except httpx.RequestError as e:
        logger.error(f"[telegram] getUpdates request error: {e}")
        return [], offset
    except Exception as e:
        logger.error(f"[telegram] getUpdates error: {e}")
        return [], offset


async def run_polling_loop(bot_token: str, on_message, interval: float = 1.0):
    """
    Long-running polling loop that calls on_message for each new message.
    Run as an asyncio task.
    """
    proxy = _detect_proxy()
    offset = 0
    logger.info("[telegram] Starting polling loop")

    while True:
        try:
            messages, offset = await poll_messages(bot_token, offset=offset, timeout=30, proxy=proxy)
            for msg in messages:
                try:
                    await on_message(msg)
                except Exception as e:
                    logger.error(f"[telegram] on_message error: {e}")
            if messages:
                await asyncio.sleep(0.5)  # short delay after processing
            else:
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("[telegram] Polling loop cancelled")
            break
        except Exception as e:
            logger.error(f"[telegram] Polling loop error: {e}")
            await asyncio.sleep(5)
