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
from .okx_monitor import OKXMonitor
from .yfinance_monitor import YFinanceMonitor
from .ebay_monitor import EbayMonitor
from .ebay_merchandise_monitor import EbayMerchandiseMonitor
from .amazon_monitor import AmazonMonitor
from .jd_monitor import JDMonitor
from ..config import get_agent_settings
from .. import database as agents_db
from telegram.bot import get_notifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Standard monitors (crypto, stocks, sports cards) - fast interval
STANDARD_MONITORS = [
    BinanceMonitor(),
    OKXMonitor(),
    AKShareMonitor(),
    YFinanceMonitor(),
    EbayMonitor(),               # sports cards
]

# Merchandise monitors - slower interval
MERCHANDISE_MONITORS = [
    EbayMerchandiseMonitor(),    # merchandise on eBay
    AmazonMonitor(),             # merchandise on Amazon
    JDMonitor(),                 # merchandise on JD
]

ALL_MONITORS = STANDARD_MONITORS + MERCHANDISE_MONITORS


async def run_monitor_cycle(monitors: list) -> list[Alert]:
    """Run one cycle of monitors. Return all alerts."""
    all_alerts: list[Alert] = []
    for monitor in monitors:
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
    await agents_db.init_db()
    all_items = []
    for monitor in ALL_MONITORS:
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
    """Main scheduler loop — runs standard monitors fast, merchandise monitors slow."""
    from ..dispatcher.graph import get_dispatcher

    settings = get_agent_settings()
    standard_interval = settings.get("monitor", {}).get("check_interval_seconds", 60)
    merchandise_interval = settings.get("merchandise", {}).get("check_interval_seconds", 300)

    logger.info(f"Monitor scheduler started — standard: {standard_interval}s, merchandise: {merchandise_interval}s")

    standard_counter = 0
    merchandise_counter = 0

    while True:
        try:
            all_alerts = []

            # Always run standard monitors
            standard_counter += standard_interval
            alerts = await run_monitor_cycle(STANDARD_MONITORS)
            all_alerts.extend(alerts)

            # Run merchandise monitors on their interval
            merchandise_counter += standard_interval
            if merchandise_counter >= merchandise_interval:
                merchandise_counter = 0
                alerts = await run_monitor_cycle(MERCHANDISE_MONITORS)
                all_alerts.extend(alerts)

            # Trigger dispatcher with alerts
            if all_alerts:
                logger.info(f"[scheduler] Dispatching {len(all_alerts)} alert(s) to dispatcher")
                try:
                    dispatcher = get_dispatcher()
                    await dispatcher.ainvoke({"alerts": all_alerts})
                    logger.info("[scheduler] Dispatcher cycle complete")
                except Exception as e:
                    logger.error(f"[scheduler] Dispatcher error: {e}")
        except Exception as e:
            logger.error(f"Scheduler cycle error: {e}")
        await asyncio.sleep(standard_interval)


async def main():
    await agents_db.init_db()
    parser = argparse.ArgumentParser(description="Broker agents monitor scheduler")
    parser.add_argument("--watchlist", action="store_true", help="Send watchlist card to Telegram and exit")
    args = parser.parse_args()

    if args.watchlist:
        await send_watchlist_card()
    else:
        await scheduler_loop()


if __name__ == "__main__":
    asyncio.run(main())
