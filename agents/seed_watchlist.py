"""Seed the watchlist with initial assets.

Run once to populate SQLite with the assets you want to monitor.
After this, manage assets via the API: POST /api/watchlist/
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import database as db


async def seed():
    await db.init_db()  # Ensure tables exist
    items = [
        # A-shares
        {
            "asset_class": "stock",
            "symbol": "600519",
            "exchange": "SSE",
            "notes": "贵州茅台",
        },
        # Crypto (exchange=Binance, symbols stored without USDT suffix)
        {
            "asset_class": "crypto",
            "symbol": "BTC",
            "exchange": "Binance",
            "notes": "Bitcoin",
        },
        {
            "asset_class": "crypto",
            "symbol": "ETH",
            "exchange": "Binance",
            "notes": "Ethereum",
        },
        {
            "asset_class": "crypto",
            "symbol": "SOL",
            "exchange": "Binance",
            "notes": "Solana",
        },
        {
            "asset_class": "crypto",
            "symbol": "BNB",
            "exchange": "Binance",
            "notes": "Binance Coin",
        },
        # Sports cards
        {
            "asset_class": "sports_card",
            "symbol": "charizard_pika001",
            "exchange": "eBay",
            "notes": "Charizard|Base Set|1999|pokemon|PSA 10|5000",
        },
        {
            "asset_class": "sports_card",
            "symbol": "jordan_nba001",
            "exchange": "eBay",
            "notes": "Michael Jordan|1986 Fleer|1986|basketball|PSA 10|150000",
        },
    ]

    print("Seeding watchlist...")
    for item in items:
        row_id = await db.upsert_watchlist_item(
            asset_class=item["asset_class"],
            symbol=item["symbol"],
            exchange=item["exchange"],
            notes=item["notes"],
        )
        print(f"  [{row_id}] {item['asset_class']:12} | {item['symbol']:20} | {item['notes']}")

    print("\nAll done. Run the backend, then:")
    print("  curl http://localhost:8000/api/watchlist/")
    print("to see your watchlist.")


if __name__ == "__main__":
    asyncio.run(seed())
