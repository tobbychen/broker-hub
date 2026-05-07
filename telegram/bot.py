"""Telegram notification bot — sends alert cards to a chat."""
import asyncio
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from agents.config import get_notification_config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends decision alerts and daily reports via Telegram bot."""

    API_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self):
        cfg = get_notification_config()
        self.token = cfg.get("bot_token", "")
        self.chat_id = cfg.get("channel_id", "")
        self.enabled = cfg.get("enabled", False)

    def _endpoint(self, method: str) -> str:
        return self.API_URL.format(token=self.token, method=method)

    async def _send(self, payload: dict) -> bool:
        """Send a request to the Telegram Bot API."""
        if not self.enabled or not self.token or not self.chat_id:
            return False
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(self._endpoint("sendMessage"), json=payload)
                if resp.status_code == 200:
                    return True
                logger.warning(f"[telegram] API error: {resp.status_code} {resp.text[:100]}")
                return False
        except httpx.RequestError as e:
            logger.error(f"[telegram] Request error: {e}")
            return False

    async def send_decision_alert(
        self,
        decision_id: int,
        decision_type: str,
        symbol: str,
        confidence: float,
        reasoning: str,
        risk_level: str,
        dashboard_url: str = "",
    ):
        """Send a rich decision alert card to Telegram."""
        if not self.enabled:
            return

        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk_level, "⚪")
        risk_text = {"low": "低风险", "medium": "中风险", "high": "高风险"}.get(risk_level, risk_level)

        text = (
            f"📊 *{decision_type.upper()} {symbol}*\n"
            f"{risk_emoji} {risk_text}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"置信度: {confidence:.0%}\n"
            f"标的: {symbol}\n"
            f"ID: `{decision_id}`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{reasoning[:200]}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔗 [打开仪表盘审批]({dashboard_url})"
        )

        await self._send({
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "✅ 批准", "callback_data": f"approve_{decision_id}"},
                    {"text": "❌ 拒绝", "callback_data": f"reject_{decision_id}"},
                    {"text": "🔍 追问", "url": dashboard_url},
                ]]
            },
        })

    async def send_daily_report(self, summary: str = "", dashboard_url: str = ""):
        """Send daily report to Telegram."""
        if not self.enabled:
            return

        text = (
            f"📋 *每日早间简报*\\n"
            f"━━━━━━━━━━━━━━━━━━\\n"
            f"{summary[:300] if summary else '简报已生成'}\n"
            f"━━━━━━━━━━━━━━━━━━\\n"
            f"🔗 [查看完整日报]({dashboard_url})"
        )

        await self._send({
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
        })

    async def send_text(self, message: str):
        """Send a plain text message."""
        await self._send({
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "MarkdownV2",
        })


_notifier: TelegramNotifier | None = None


def get_notifier() -> TelegramNotifier:
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier
