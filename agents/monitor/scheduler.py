"""Scheduler that runs all monitors at configured intervals."""
import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .base import Alert
from .akshare_monitor import AKShareMonitor
from .binance_monitor import BinanceMonitor
from .yfinance_monitor import YFinanceMonitor
from .ebay_monitor import EbayMonitor
from ..config import get_agent_settings
from telegram.bot import get_notifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MONITORS = [
    BinanceMonitor(),
    AKShareMonitor(),
    YFinanceMonitor(),
    EbayMonitor(),
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


async def send_watchlist_card():
    """Fetch and send a watchlist card to Telegram."""
    all_items = []
    for monitor in MONITORS:
        try:
            items = await monitor.get_watchlist()
            all_items.extend(items)
        except Exception as e:
            logger.error(f"[{monitor.name}] watchlist error: {e}")
    if all_items:
        notifier = get_notifier()
        await notifier.send_watchlist(all_items)
        logger.info(f"Watchlist sent — {len(all_items)} asset(s)")
    else:
        logger.warning("Watchlist empty — no data fetched")


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
    parser = argparse.ArgumentParser(description="Broker agents monitor scheduler")
    parser.add_argument("--watchlist", action="store_true", help="Send watchlist card to Telegram and exit")
    args = parser.parse_args()

    if args.watchlist:
        await send_watchlist_card()
    else:
        await scheduler_loop()


if __name__ == "__main__":
    asyncio.run(main())
