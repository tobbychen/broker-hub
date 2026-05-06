"""Scheduler that runs all monitors at configured intervals."""
import asyncio
import logging
from datetime import datetime
from .base import Alert
from .akshare_monitor import AKShareMonitor
from .binance_monitor import BinanceMonitor
from .yfinance_monitor import YFinanceMonitor
from .card_ladder_monitor import CardLadderMonitor
from ..config import get_agent_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MONITORS = [
    BinanceMonitor(),
    AKShareMonitor(),
    YFinanceMonitor(),
    CardLadderMonitor(),
]


async def run_monitor_cycle() -> list[Alert]:
    """Run one cycle of all monitors. Return all alerts."""
    all_alerts: list[Alert] = []
    for monitor in MONITORS:
        try:
            alerts = await monitor.check()
            all_alerts.extend(alerts)
            if alerts:
                logger.info(f"[{monitor.name}] {len(alerts)} alert(s) found")
        except Exception as e:
            logger.error(f"[{monitor.name}] Error: {e}")
    return all_alerts


async def scheduler_loop():
    """Main scheduler loop."""
    settings = get_agent_settings()
    interval = settings.get("monitor", {}).get("check_interval_seconds", 60)

    logger.info(f"Monitor scheduler started — interval: {interval}s")
    while True:
        try:
            await run_monitor_cycle()
        except Exception as e:
            logger.error(f"Scheduler cycle error: {e}")
        await asyncio.sleep(interval)


async def main():
    await scheduler_loop()


if __name__ == "__main__":
    asyncio.run(main())
