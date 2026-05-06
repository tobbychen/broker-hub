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
        rows = await db.fetchall(
            "SELECT * FROM positions ORDER BY asset_class, symbol"
        )
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
        row = await db.fetchone(
            "SELECT id FROM positions WHERE asset_class=? AND symbol=? AND exchange=?",
            (asset_class, symbol, exchange),
        )
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
        rows = await db.fetchall(
            "SELECT * FROM decisions WHERE status='pending' ORDER BY created_at DESC"
        )
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
        rows = await db.fetchall(
            "SELECT * FROM decision_chat WHERE decision_id=? ORDER BY created_at",
            (decision_id,),
        )
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
        row = await db.fetchone(
            "SELECT id FROM daily_reports WHERE report_date=?",
            (report_date.isoformat(),),
        )
        return row["id"] if row else 0
    finally:
        await db.close()


async def get_daily_report(report_date: date) -> Optional[dict]:
    db = await get_db()
    try:
        row = await db.fetchone(
            "SELECT * FROM daily_reports WHERE report_date=?", (report_date.isoformat(),)
        )
        return dict(row) if row else None
    finally:
        await db.close()


# ---- Sports card helpers ----

async def get_sports_cards() -> list[dict]:
    db = await get_db()
    try:
        rows = await db.fetchall("SELECT * FROM sports_cards ORDER BY set_name, card_name")
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


# ---- Portfolio summary ----

async def get_portfolio_summary() -> dict:
    db = await get_db()
    try:
        rows = await db.fetchall(
            """
            SELECT
                asset_class,
                COUNT(*) as position_count,
                SUM(quantity * avg_cost) as total_cost
            FROM positions
            GROUP BY asset_class
            """
        )
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
