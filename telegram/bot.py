"""Telegram notification bot — sends alert cards to a chat."""
import asyncio
import logging
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from agents.config import get_notification_config

logger = logging.getLogger(__name__)


def _detect_proxy() -> str | None:
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        val = os.environ.get(var)
        if val:
            return val
    return None


class TelegramNotifier:
    """Sends decision alerts and daily reports via Telegram bot."""

    API_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self):
        cfg = get_notification_config()
        self.token = cfg.get("bot_token", "")
        self.chat_id = cfg.get("channel_id", "")
        self.enabled = cfg.get("enabled", False)
        self._proxy = _detect_proxy()

    def _endpoint(self, method: str) -> str:
        return self.API_URL.format(token=self.token, method=method)

    async def _send(self, payload: dict) -> bool:
        """Send a request to the Telegram Bot API."""
        if not self.enabled or not self.token or not self.chat_id:
            return False
        try:
            async with httpx.AsyncClient(proxy=self._proxy, timeout=15) as client:
                resp = await client.post(self._endpoint("sendMessage"), json=payload)
                if resp.status_code == 200:
                    return True
                logger.warning(f"[telegram] API error: {resp.status_code} {resp.text[:200]}")
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
    ) -> bool:
        """Send a rich decision alert card to Telegram using HTML."""
        if not self.enabled:
            return False

        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk_level, "⚪")
        risk_text = {"low": "低风险", "medium": "中风险", "high": "高风险"}.get(risk_level, risk_level)

        text = (
            f"📊 <b>{decision_type.upper()} {symbol}</b>\n"
            f"{risk_emoji} {risk_text}\n"
            f"────────────────────\n"
            f"置信度: {confidence:.0%}\n"
            f"标的: {symbol}\n"
            f"ID: {decision_id}\n"
            f"────────────────────\n"
            f"{reasoning[:200]}\n"
            f"────────────────────\n"
            f"🔗 <a href='{dashboard_url}'>打开仪表盘审批</a>"
        )

        # Inline keyboard requires a public HTTPS URL — skip if dashboard_url is localhost
        reply_markup = None
        if dashboard_url and not dashboard_url.startswith("http://localhost"):
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "✅ 批准", "callback_data": f"approve_{decision_id}"},
                        {"text": "❌ 拒绝", "callback_data": f"reject_{decision_id}"},
                    ],
                    [
                        {"text": "🔍 打开仪表盘", "url": dashboard_url},
                    ],
                ]
            }

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self._send(payload)

    async def send_daily_report(self, summary: str = "", dashboard_url: str = "") -> bool:
        """Send daily report to Telegram."""
        if not self.enabled:
            return False

        text = (
            f"📋 <b>每日早间简报</b>\n"
            f"────────────────────\n"
            f"{summary[:300] if summary else '简报已生成'}\n"
            f"────────────────────\n"
            f"🔗 <a href='{dashboard_url}'>查看完整日报</a>"
        )

        return await self._send({
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        })

    async def send_text(self, message: str) -> bool:
        """Send a plain text message."""
        return await self._send({
            "chat_id": self.chat_id,
            "text": message,
        })

    async def send_watchlist(self, items: list[dict]) -> bool:
        """Send a watchlist card showing current prices of all monitored assets."""
        if not self.enabled or not items:
            return False

        # Build per-exchange sections
        sections = {}
        for item in items:
            exchange = item.get("exchange", "Other")
            sections.setdefault(exchange, []).append(item)

        lines = ["📋 <b>实时行情监控</b>", ""]
        for exchange, assets in sections.items():
            lines.append(f"<b>{exchange}</b>")
            for a in assets:
                symbol = a.get("symbol", "")
                name = a.get("name", "")
                price = a.get("price")
                change = a.get("change_pct") or a.get("change_1h_pct", 0)
                arrow = "▲" if change >= 0 else "▼"
                color = "+" if change >= 0 else ""
                if price is not None:
                    if isinstance(price, float):
                        if price > 100:
                            price_str = f"{price:,.2f}"
                        else:
                            price_str = f"{price:.6f}"
                    else:
                        price_str = str(price)
                    lines.append(f"{arrow} {symbol} {price_str}  {color}{change:+.2f}%")
                else:
                    lines.append(f"{arrow} {symbol} —")
            lines.append("")

        return await self._send({
            "chat_id": self.chat_id,
            "text": "\n".join(lines).strip(),
            "parse_mode": "HTML",
        })


_notifier: TelegramNotifier | None = None


def get_notifier() -> TelegramNotifier:
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier
