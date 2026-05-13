"""SQLite access for agents (read watchlist, write market cache).

Uses aiosqlite directly so agents don't depend on FastAPI's database layer.
DB path resolved from PROJECT_ROOT so it works in any process.
"""
import aiosqlite
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "broker_agents.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"


async def init_db():
    """Ensure all schema tables exist. Safe to call multiple times."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            schema = f.read()
        for stmt in schema.split(";"):
            stmt = stmt.strip()
            if stmt:
                await db.execute(stmt)
        await db.commit()


# ---- Watchlist ----

async def get_watchlist_items(asset_class: str = "") -> list[dict]:
    """Get all watchlist items, optionally filtered by asset class."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        if asset_class:
            rows = await db.execute(
                "SELECT * FROM watchlist WHERE asset_class=? ORDER BY symbol",
                (asset_class,),
            )
        else:
            rows = await db.execute("SELECT * FROM watchlist ORDER BY asset_class, symbol")
        result = await rows.fetchall()
        return [dict(r) for r in result]


async def upsert_watchlist_item(
    asset_class: str,
    symbol: str,
    exchange: str = "",
    notes: str = "",
) -> int:
    """Add or update a watchlist item."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO watchlist (asset_class, symbol, exchange, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(asset_class, symbol, exchange)
            DO UPDATE SET notes=excluded.notes
            """,
            (asset_class, symbol, exchange, notes),
        )
        await db.commit()
        rows = await db.execute(
            "SELECT id FROM watchlist WHERE asset_class=? AND symbol=? AND exchange=?",
            (asset_class, symbol, exchange),
        )
        row = await rows.fetchone()
        return dict(row)["id"] if row else 0


async def delete_watchlist_item(watchlist_id: int) -> bool:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute("DELETE FROM watchlist WHERE id=?", (watchlist_id,))
        await db.commit()
        return cursor.rowcount > 0


# ---- Market cache ----

async def set_market_cache(
    symbol: str,
    data_type: str,
    raw_data: dict,
    exchange: str = "",
) -> None:
    """Write market data to cache. raw_data is a dict (serialized to JSON)."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """
            INSERT INTO market_cache (symbol, exchange, data_type, raw_data, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(symbol, exchange, data_type)
            DO UPDATE SET raw_data=excluded.raw_data, fetched_at=excluded.fetched_at
            """,
            (symbol, exchange, data_type, json.dumps(raw_data, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        await db.commit()


async def get_market_cache(
    symbol: str,
    data_type: str,
    exchange: str = "",
    max_age_seconds: int = 86400,
) -> Optional[dict]:
    """Get cached market data if fresh enough. Default max_age is 24 hours."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        sql = """
            SELECT * FROM market_cache
            WHERE symbol=? AND data_type=? AND exchange=?
            ORDER BY fetched_at DESC LIMIT 1
            """
        rows = await db.execute(sql, (symbol, exchange, data_type))
        row = await rows.fetchone()
        if row:
            d = dict(row)
            return {"raw_data": json.loads(d["raw_data"]), "fetched_at": d["fetched_at"]}
        return None


async def get_last_price(symbol: str, exchange: str = "") -> Optional[float]:
    """Get the last cached price for a symbol if available."""
    cached = await get_market_cache(symbol, "latest_price", exchange, max_age_seconds=86400)
    if cached:
        return cached["raw_data"].get("price")
    return None
