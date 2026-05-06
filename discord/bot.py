"""Discord notification bot — sends alert cards to a channel."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import discord
from discord import Embed, ButtonStyle
from discord.ui import Button, View
from agents.config import get_discord_config


class DiscordNotifier:
    def __init__(self):
        self.config = get_discord_config()
        self.bot = discord.Bot(intents=discord.Intents.default())
        self._channel_id = None
        if self.config.get("channel_id"):
            try:
                self._channel_id = int(self.config.get("channel_id"))
            except (ValueError, TypeError):
                pass

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
        """Send an embed card for a pending decision."""
        if not self.config.get("enabled"):
            return
        if not self._channel_id:
            return

        risk_color = {
            "low": 0x00c853,
            "medium": 0xffc107,
            "high": 0xff1744,
        }.get(risk_level, 0x888888)

        embed = Embed(
            title=f"📊 {decision_type.upper()} {symbol}",
            description=reasoning[:200],
            color=risk_color,
        )
        embed.add_field(name="置信度", value=f"{confidence:.0%}", inline=True)
        embed.add_field(name="风险", value=risk_level.upper(), inline=True)
        embed.add_field(name="ID", value=str(decision_id), inline=True)
        embed.set_footer(text="点击下方按钮审批 →")

        button = Button(
            style=ButtonStyle.link,
            label="打开仪表盘审批",
            url=dashboard_url or "https://dashboard.broker-agents.local",
        )
        view = View()
        view.add_item(button)

        try:
            channel = self.bot.get_channel(self._channel_id)
            if channel:
                await channel.send(embed=embed, view=view)
        except Exception:
            pass

    async def send_daily_report(self, summary: str = "", dashboard_url: str = ""):
        if not self.config.get("enabled"):
            return
        if not self._channel_id:
            return

        embed = Embed(
            title="📋 每日早间简报",
            description=(summary or "今日简报已生成")[:300],
            color=0x2196f3,
        )
        button = Button(
            style=ButtonStyle.link,
            label="查看完整日报",
            url=dashboard_url or "https://dashboard.broker-agents.local",
        )
        view = View()
        view.add_item(button)

        try:
            channel = self.bot.get_channel(self._channel_id)
            if channel:
                await channel.send(embed=embed, view=view)
        except Exception:
            pass

    async def run(self):
        """Run the Discord bot (blocking)."""
        token = self.config.get("bot_token")
        if not token:
            return
        await self.bot.start(token)


_notifier: DiscordNotifier | None = None


def get_notifier() -> DiscordNotifier:
    global _notifier
    if _notifier is None:
        _notifier = DiscordNotifier()
    return _notifier