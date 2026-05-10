"""SQLite database layer using aiosqlite."""
import aiosqlite
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional
from .config import get_database_config

DB_PATH = Path(get_database_config().get("path", "data/broker_agents.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA_PATH = Path(__file__).parent.parent.parent / "database" / "schema.sql"


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """Run schema if tables don't exist."""
    db = await get_db()
    try:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            schema = f.read()
        for stmt in schema.split(";"):
            stmt = stmt.strip()
            if stmt:
                await db.execute(stmt)
        await db.commit()
    finally:
        await db.close()


# ---- Position helpers ----

async def get_all_positions() -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM positions ORDER BY asset_class, symbol"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def upsert_position(
    asset_class: str,
    symbol: str,
    quantity: float,
    avg_cost: float,
    exchange: str = "",
    currency: str = "CNY",
    notes: str = "",
) -> int:
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO positions (asset_class, symbol, exchange, quantity, avg_cost, currency, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(asset_class, symbol, exchange)
            DO UPDATE SET
                quantity=excluded.quantity,
                avg_cost=excluded.avg_cost,
                notes=excluded.notes,
                updated_at=CURRENT_TIMESTAMP
            """,
            (asset_class, symbol, exchange, quantity, avg_cost, currency, notes),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT id FROM positions WHERE asset_class=? AND symbol=? AND exchange=?",
            (asset_class, symbol, exchange),
        )
        row = await cursor.fetchone()
        return row["id"] if row else 0
    finally:
        await db.close()


# ---- Decision helpers ----

async def create_decision(
    decision_type: str,
    asset_class: str,
    symbol: str,
    quantity: float | None,
    action_price: float | None,
    confidence: float,
    reasoning: str,
    risk_level: str,
    timeout_minutes: int = 30,
) -> int:
    db = await get_db()
    try:
        timeout_at = datetime.now() + timedelta(minutes=timeout_minutes)
        cursor = await db.execute(
            """
            INSERT INTO decisions
            (decision_type, asset_class, symbol, quantity, action_price, confidence, reasoning, risk_level, timeout_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (decision_type, asset_class, symbol, quantity, action_price, confidence, reasoning, risk_level, timeout_at.isoformat()),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_pending_decisions() -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM decisions WHERE status='pending' ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def resolve_decision(decision_id: int, approved: bool) -> None:
    db = await get_db()
    try:
        status = "approved" if approved else "rejected"
        await db.execute(
            "UPDATE decisions SET status=?, resolved_at=CURRENT_TIMESTAMP, human_approved=? WHERE id=?",
            (status, approved, decision_id),
        )
        await db.commit()
    finally:
        await db.close()


async def add_chat_message(decision_id: int, role: str, content: str) -> int:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO decision_chat (decision_id, role, content) VALUES (?, ?, ?)",
            (decision_id, role, content),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_chat_history(decision_id: int) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM decision_chat WHERE decision_id=? ORDER BY created_at",
            (decision_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


# ---- Daily report helpers ----

async def save_daily_report(
    report_date: date,
    overnight_summary: str,
    critical_events: str,
    investment_windows: str,
    risk_metrics: str = "",
) -> int:
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO daily_reports (report_date, overnight_summary, critical_events, investment_windows, risk_metrics)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(report_date) DO UPDATE SET
                overnight_summary=excluded.overnight_summary,
                critical_events=excluded.critical_events,
                investment_windows=excluded.investment_windows,
                risk_metrics=excluded.risk_metrics,
                generated_at=CURRENT_TIMESTAMP
            """,
            (report_date.isoformat(), overnight_summary, critical_events, investment_windows, risk_metrics),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT id FROM daily_reports WHERE report_date=?",
            (report_date.isoformat(),),
        )
        row = await cursor.fetchone()
        return row["id"] if row else 0
    finally:
        await db.close()


async def get_daily_report(report_date: date) -> Optional[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM daily_reports WHERE report_date=?", (report_date.isoformat(),)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


# ---- Sports card helpers ----

async def get_sports_cards() -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sports_cards ORDER BY set_name, card_name")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


# ---- Agent log helpers ----

async def log_agent_event(agent_name: str, event_type: str, details: str = "") -> None:
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO agent_logs (agent_name, event_type, details) VALUES (?, ?, ?)",
            (agent_name, event_type, details),
        )
        await db.commit()
    finally:
        await db.close()


# ---- Watchlist helpers ----

async def upsert_watchlist_item(
    asset_class: str,
    symbol: str,
    exchange: str = "",
    notes: str = "",
) -> int:
    db = await get_db()
    try:
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
        cursor = await db.execute(
            "SELECT id FROM watchlist WHERE asset_class=? AND symbol=? AND exchange=?",
            (asset_class, symbol, exchange),
        )
        row = await cursor.fetchone()
        return row["id"] if row else 0
    finally:
        await db.close()


async def get_watchlist_items(asset_class: str = "") -> list[dict]:
    db = await get_db()
    try:
        if asset_class:
            cursor = await db.execute(
                "SELECT * FROM watchlist WHERE asset_class=? ORDER BY symbol",
                (asset_class,),
            )
        else:
            cursor = await db.execute("SELECT * FROM watchlist ORDER BY asset_class, symbol")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def delete_watchlist_item(watchlist_id: int) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute(
            "DELETE FROM watchlist WHERE id=?",
            (watchlist_id,),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


# ---- Market cache helpers ----

async def set_market_cache(
    symbol: str,
    data_type: str,
    raw_data: str,
    exchange: str = "",
) -> None:
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO market_cache (symbol, exchange, data_type, raw_data, fetched_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol, exchange, data_type)
            DO UPDATE SET raw_data=excluded.raw_data, fetched_at=CURRENT_TIMESTAMP
            """,
            (symbol, exchange, data_type, raw_data),
        )
        await db.commit()
    finally:
        await db.close()


async def get_market_cache_latest(
    symbol: str,
    data_type: str,
    exchange: str = "",
    max_age_seconds: int = 300,
) -> Optional[dict]:
    """Get cached market data if fresh enough, else None."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            SELECT * FROM market_cache
            WHERE symbol=? AND exchange=? AND data_type=?
            AND (strftime('%s','now') - strftime('%s', fetched_at)) < ?
            """,
            (symbol, exchange, data_type, max_age_seconds),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_watchlist_prices(asset_class: str = "") -> list[dict]:
    """Get latest cached prices for all watchlist items."""
    import json
    db = await get_db()
    try:
        if asset_class:
            cursor = await db.execute(
                """
                SELECT w.id, w.asset_class, w.symbol, w.exchange, w.notes, w.created_at,
                       m.raw_data, m.fetched_at
                FROM watchlist w
                LEFT JOIN market_cache m
                    ON m.symbol = w.symbol
                    AND m.data_type = 'latest_price'
                WHERE w.asset_class = ?
                ORDER BY w.asset_class, w.symbol
                """,
                (asset_class,),
            )
        else:
            cursor = await db.execute(
                """
                SELECT w.id, w.asset_class, w.symbol, w.exchange, w.notes, w.created_at,
                       m.raw_data, m.fetched_at
                FROM watchlist w
                LEFT JOIN market_cache m
                    ON m.symbol = w.symbol
                    AND m.data_type = 'latest_price'
                ORDER BY w.asset_class, w.symbol
                """,
            )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("raw_data") and isinstance(d["raw_data"], str):
                try:
                    d["raw_data"] = json.loads(d["raw_data"])
                except Exception:
                    pass
            result.append(d)
        return result
    finally:
        await db.close()


# ---- Portfolio summary ----

async def get_portfolio_summary() -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            SELECT
                asset_class,
                COUNT(*) as position_count,
                SUM(quantity * avg_cost) as total_cost
            FROM positions
            GROUP BY asset_class
            """
        )
        rows = await cursor.fetchall()
        total = sum(r["total_cost"] or 0 for r in rows)
        allocation = {}
        for r in rows:
            pct = (r["total_cost"] or 0) / total * 100 if total else 0
            allocation[r["asset_class"]] = {"cost": r["total_cost"] or 0, "pct": round(pct, 1)}

        return {
            "total_value": total,
            "allocation": allocation,
            "by_class": [dict(r) for r in rows],
        }
    finally:
        await db.close()


async def get_market_cache(
    symbol: str,
    exchange: str = "",
    data_type: str = "latest_price",
) -> Optional[dict]:
    """Get the most recent cached market data for a symbol (no age check)."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            SELECT * FROM market_cache
            WHERE symbol=? AND exchange=? AND data_type=?
            ORDER BY fetched_at DESC LIMIT 1
            """,
            (symbol, exchange, data_type),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def set_portfolio_snapshot(
    total_value: float,
    positions_json: str,
    allocation_json: str,
) -> int:
    """Store a portfolio snapshot for P&L tracking."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            INSERT INTO portfolio_snapshots (total_value, positions_json, allocation_json)
            VALUES (?, ?, ?)
            """,
            (total_value, positions_json, allocation_json),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def log_dispatcher_event(
    event_type: str,
    alert_source: str = "",
    decision_id: int = 0,
    details: str = "",
) -> int:
    """Log a dispatcher pipeline event for audit trail."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            INSERT INTO dispatcher_events (event_type, alert_source, decision_id, details)
            VALUES (?, ?, ?, ?)
            """,
            (event_type, alert_source, decision_id, details),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_decision_by_id(decision_id: int) -> Optional[dict]:
    """Get a single decision by ID."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM decisions WHERE id=?", (decision_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()
