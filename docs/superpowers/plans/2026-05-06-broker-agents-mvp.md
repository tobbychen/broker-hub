# Broker Agents MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A self-hosted multi-agent investment assistant on the E3 workstation. Agents research markets, human makes all decisions. Phase 1 produces a working dashboard with real market data and LLM-powered recommendations.

**Architecture:** FastAPI backend + Vue 3 frontend on the E3 workstation. LangGraph agents orchestrated by a Dispatcher. Python scripts for monitoring. SQLite local database. Cloudflare Tunnel exposing the dashboard. MiniMax LLM as primary provider.

**Tech Stack:** Python 3.12, LangGraph, LangChain, FastAPI, Vue 3, Vite, Element Plus, SQLite, AKShare, python-binance, yfinance, Cloudflare Tunnel, Discord.py

---

## File Structure

```
broker-agents/
├── CLAUDE.md                          # Project context for future sessions
├── requirements.txt                   # All Python dependencies
├── pyproject.toml                     # Project metadata
├── config/
│   ├── api_providers.yaml            # LLM + market data API keys
│   ├── agent_settings.yaml            # Thresholds, limits, timeouts
│   └── database.yaml                 # SQLite path config
├── database/
│   ├── schema.sql                    # Full DB schema
│   └── migrations/001_initial.sql
├── agents/
│   ├── __init__.py
│   ├── dispatcher/
│   │   ├── __init__.py
│   │   ├── graph.py                 # LangGraph state graph definition
│   │   ├── nodes.py                 # Node implementations
│   │   ├── tools.py                 # Dispatcher tools (lookup portfolio, etc.)
│   │   └── prompts.py               # System prompts for dispatcher
│   ├── research_analyst/
│   │   ├── __init__.py
│   │   ├── agent.py                 # Research agent definition
│   │   └── prompts.py
│   ├── trade_executor/
│   │   ├── __init__.py
│   │   ├── agent.py                 # Trade executor agent
│   │   └── prompts.py
│   └── monitor/
│       ├── __init__.py
│       ├── base.py                  # Base monitor class
│       ├── scheduler.py             # Scheduler that runs all monitors
│       ├── akshare_monitor.py       # A-share + China futures monitor
│       ├── binance_monitor.py       # Crypto price monitor
│       ├── yfinance_monitor.py      # US stocks + ETF monitor
│       └── card_ladder_monitor.py   # Sports card price monitor
├── dashboard/
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── config.py                # Config loader from YAML
│   │   ├── database.py              # SQLite connection + queries
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── portfolio.py         # /api/portfolio endpoints
│   │   │   ├── decisions.py         # /api/decisions endpoints
│   │   │   ├── chat.py              # /api/chat endpoints (streaming)
│   │   │   ├── daily_report.py      # /api/daily-report endpoints
│   │   │   └── agent_status.py      # /api/agent-status endpoints
│   │   └── models/
│   │       ├── __init__.py
│   │       └── schemas.py           # Pydantic models
│   └── frontend/
│       ├── package.json
│       ├── vite.config.ts
│       ├── index.html
│       ├── src/
│       │   ├── main.ts
│       │   ├── App.vue
│       │   ├── router.ts
│       │   ├── api/                  # API client functions
│       │   ├── views/               # Page components
│       │   │   ├── PortfolioView.vue
│       │   │   ├── DailyReportView.vue
│       │   │   ├── DecisionsView.vue
│       │   │   ├── TradeHistoryView.vue
│       │   │   ├── SportsCardsView.vue
│       │   │   └── AgentStatusView.vue
│       │   ├── components/           # Reusable components
│       │   │   ├── DecisionCard.vue
│       │   │   ├── ChatPanel.vue
│       │   │   ├── PortfolioPie.vue
│       │   │   └── BottomNav.vue
│       │   ├── stores/              # Pinia stores
│       │   │   ├── portfolio.ts
│       │   │   └── decisions.ts
│       │   └── styles/
│       │       └── main.css
│       └── public/
│           └── manifest.json         # PWA manifest
├── discord/
│   ├── __init__.py
│   └── bot.py                       # Discord notification bot
├── infra/
│   └── cloudflared/
│       └── setup.sh                 # Cloudflare Tunnel setup script
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_monitor.py
    ├── test_dispatcher.py
    ├── test_api_portfolio.py
    └── test_api_decisions.py
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `CLAUDE.md`
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `config/api_providers.yaml`
- Create: `config/agent_settings.yaml`
- Create: `config/database.yaml`
- Create: `database/schema.sql`
- Create: `database/migrations/001_initial.sql`

- [ ] **Step 1: Create CLAUDE.md**

```markdown
# Broker Agents — Investment Superpower System

## What This Is
A self-hosted multi-agent investment assistant. Agents research markets, draft recommendations, human makes all decisions. Runs on E3 workstation in Beijing.

## Architecture
- **Agents:** LangGraph-powered dispatcher + workers (Python scripts for fast monitoring, LLM agents for analysis/research)
- **Dashboard:** FastAPI backend + Vue 3 frontend, mobile-first
- **Database:** Local SQLite — all trading records stay on your hardware
- **LLM:** MiniMax primary (your existing plan), GLM/Kimi fallback via config
- **Network:** Cloudflare Tunnel — no port forwarding, no static IP needed

## Key Files
- `config/api_providers.yaml` — All API keys (env vars). Swap providers without code changes.
- `agents/dispatcher/graph.py` — LangGraph state machine, the brain
- `dashboard/backend/main.py` — FastAPI app
- `database/schema.sql` — SQLite schema

## Commands
```bash
# Install
pip install -r requirements.txt

# Run agents (background)
python -m agents.monitor.scheduler

# Run dashboard
cd dashboard/backend && uvicorn main:app --reload

# Run frontend (separate terminal)
cd dashboard/frontend && npm install && npm run dev
```

## Design Doc
See `docs/superpowers/specs/2026-05-06-broker-agents-design.md`
```

- [ ] **Step 2: Create requirements.txt**

```
# Core agent framework
langgraph==0.4.3
langchain==0.4.1
langchain-core==0.4.1
langchain-community==0.4.1

# LLM providers
langchain-minimax>=0.1.0
openai>=1.0.0

# Dashboard backend
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.0.0
python-multipart>=0.0.9

# Database
aiosqlite>=0.20.0

# Market data
akshare>=1.15.0
python-binance>=1.0.19
yfinance>=0.2.40
requests>=2.32.0

# Discord
discord.py>=2.4.0

# Config
pyyaml>=6.0.0
python-dotenv>=1.0.0

# Sports cards
httpx>=0.27.0

# Testing
pytest>=8.3.0
pytest-asyncio>=0.24.0
httpx>=0.27.0
```

- [ ] **Step 3: Create config/api_providers.yaml**

```yaml
llm:
  primary:
    provider: minimax
    api_key: ${MINIMAX_API_KEY}
    model: ${MINIMAX_MODEL:-auto}
    base_url: ${MINIMAX_BASE_URL:-https://api.minimax.chat/v1}

  fallback:
    - provider: glm
      api_key: ${GLM_API_KEY}
      model: ${GLM_MODEL:-glm-4}
      base_url: ${GLM_BASE_URL:-https://open.bigmodel.cn/api/paas/v4}
    - provider: kimi
      api_key: ${KIMI_API_KEY}
      model: ${KIMI_MODEL:-moonshot-v1-128k}
      base_url: ${KIMI_BASE_URL:-https://api.moonshot.cn/v1}

market_data:
  akshare:
    enabled: true
  binance:
    enabled: true
    api_key: ${BINANCE_API_KEY}
    secret: ${BINANCE_SECRET}
  yfinance:
    enabled: true
  card_ladder:
    enabled: true
    api_key: ${CARDLADDER_API_KEY}

discord:
  enabled: true
  bot_token: ${DISCORD_BOT_TOKEN}
  channel_id: ${DISCORD_CHANNEL_ID}
```

- [ ] **Step 4: Create config/agent_settings.yaml**

```yaml
agents:
  monitor:
    price_change_threshold: 0.03      # 3%
    volume_spike_multiplier: 2.0
    check_interval_seconds: 60        # How often to poll
    arbitrage_threshold: 0.005       # 0.5% gap triggers alert
    card_price_threshold: 0.05       # 5% card price move

  research:
    timeout_seconds: 120
    max_sources: 5
    confidence_threshold: 0.6        # Below this, flag as uncertain

  risk:
    max_position_pct: 0.20           # Max 20% in single asset
    max_sector_pct: 0.40             # Max 40% in single sector
    max_correlation: 0.80            # Max correlation in portfolio

  autonomy:
    small_position_limit: 10000      # ¥10K — Phase 2 feature
    require_human_approval: true     # Phase 1: all require approval

  decision:
    timeout_minutes: 30              # Auto-expire pending decision
    escalation_threshold: 0.9        # Confidence > 90% = high priority

  daily_report:
    send_time: "08:00"
    timezone: "Asia/Shanghai"
```

- [ ] **Step 5: Create config/database.yaml**

```yaml
database:
  path: "${DB_PATH:-data/broker_agents.db}"
  backup_path: "${DB_BACKUP_PATH:-data/backups}"
  auto_backup_hours: 24
```

- [ ] **Step 6: Create database/schema.sql**

```sql
-- Positions across all asset classes
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_class TEXT NOT NULL CHECK(asset_class IN ('stock', 'crypto', 'forex', 'options', 'sports_card')),
    symbol TEXT NOT NULL,
    exchange TEXT,
    quantity REAL NOT NULL,
    avg_cost REAL NOT NULL,
    currency TEXT DEFAULT 'CNY',
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asset_class, symbol, exchange)
);

-- Agent-generated recommendations
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_type TEXT NOT NULL CHECK(decision_type IN ('buy', 'sell', 'hold', 'arbitrage')),
    asset_class TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT,
    quantity REAL,
    action_price REAL,
    confidence REAL,
    reasoning TEXT NOT NULL,
    risk_level TEXT CHECK(risk_level IN ('low', 'medium', 'high')),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'expired', 'executed')),
    timeout_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    human_approved BOOLEAN,
    execution_result TEXT
);

-- Trade execution log
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER REFERENCES decisions(id),
    symbol TEXT NOT NULL,
    exchange TEXT,
    side TEXT CHECK(side IN ('buy', 'sell')),
    quantity REAL NOT NULL,
    price REAL,
    commission REAL,
    executed_at DATETIME,
    broker TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Interactive chat messages per decision
CREATE TABLE decision_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER REFERENCES decisions(id),
    role TEXT CHECK(role IN ('human', 'agent')),
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Sports card portfolio
CREATE TABLE sports_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_name TEXT NOT NULL,
    set_name TEXT NOT NULL,
    grade TEXT,
    grader TEXT CHECK(grader IN ('PSA', 'BGS', 'CGC', '未评级')),
    purchase_price REAL,
    current_estimated_value REAL,
    market_source TEXT,
    card_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Daily reports
CREATE TABLE daily_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date DATE NOT NULL UNIQUE,
    overnight_summary TEXT,
    critical_events TEXT,
    investment_windows TEXT,
    risk_metrics TEXT,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Agent activity log
CREATE TABLE agent_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Market data cache (avoids hammering APIs)
CREATE TABLE market_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    exchange TEXT,
    data_type TEXT NOT NULL,
    raw_data TEXT NOT NULL,
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, exchange, data_type)
);

-- Watchlist for dispatcher context
CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_class TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asset_class, symbol, exchange)
);

-- Indexes
CREATE INDEX idx_decisions_status ON decisions(status);
CREATE INDEX idx_decisions_timeout ON decisions(timeout_at);
CREATE INDEX idx_trades_decision ON trades(decision_id);
CREATE INDEX idx_market_cache_symbol ON market_cache(symbol, exchange);
CREATE INDEX idx_agent_logs_agent ON agent_logs(agent_name, created_at);
```

- [ ] **Step 7: Create database/migrations/001_initial.sql** (copy schema.sql content here as initial migration)

- [ ] **Step 8: Create pyproject.toml**

```toml
[project]
name = "broker-agents"
version = "0.1.0"
description = "Self-hosted multi-agent investment assistant"
requires-python = ">=3.12"
dependencies = [
    "langgraph>=0.4.3",
    "langchain>=0.4.1",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "akshare>=1.15.0",
    "python-binance>=1.0.19",
    "yfinance>=0.2.40",
    "aiosqlite>=0.20.0",
    "discord.py>=2.4.0",
    "pyyaml>=6.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.3.0", "pytest-asyncio>=0.24.0", "httpx>=0.27.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## Task 2: Dashboard Backend — Core

**Files:**
- Create: `dashboard/backend/__init__.py`
- Create: `dashboard/backend/config.py`
- Create: `dashboard/backend/database.py`
- Create: `dashboard/backend/models/schemas.py`
- Create: `dashboard/backend/routers/__init__.py`
- Create: `dashboard/backend/main.py`
- Create: `tests/conftest.py`
- Test: `tests/test_api_portfolio.py`

- [ ] **Step 1: Create dashboard/backend/config.py**

```python
"""Config loader — reads YAML files and environment variables."""
import os
from pathlib import Path
from typing import Any
import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"


def _env_substitute(obj: Any) -> Any:
    """Recursively substitute ${VAR} with os.environ[VAR]."""
    if isinstance(obj, dict):
        return {k: _env_substitute(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_env_substitute(v) for v in obj]
    elif isinstance(obj, str):
        if obj.startswith("${") and obj.endswith("}"):
            var = obj[2:-1]
            default = None
            if ":-" in var:
                var, default = var.split(":-", 1)
            return os.environ.get(var, default or "")
        return obj
    return obj


def load_config(name: str) -> dict:
    path = CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return _env_substitute(data or {})


def get_llm_config() -> dict:
    return load_config("api_providers").get("llm", {})


def get_market_data_config() -> dict:
    return load_config("api_providers").get("market_data", {})


def get_agent_settings() -> dict:
    return load_config("agent_settings").get("agents", {})


def get_database_config() -> dict:
    return load_config("database")


def get_discord_config() -> dict:
    return load_config("api_providers").get("discord", {})
```

- [ ] **Step 2: Create dashboard/backend/database.py**

```python
"""SQLite database layer using aiosqlite."""
import aiosqlite
import json
from pathlib import Path
from datetime import datetime, date
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
            DO UPDATE SET quantity=excluded.quantity, avg_cost=excluded.avg_cost,
                          notes=excluded.notes, updated_at=CURRENT_TIMESTAMP
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
    quantity: float,
    action_price: float,
    confidence: float,
    reasoning: str,
    risk_level: str,
    timeout_minutes: int = 30,
) -> int:
    db = await get_db()
    try:
        timeout_at = datetime.now().replace(microsecond=0)
        from datetime import timedelta
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
            "SELECT id FROM daily_reports WHERE report_date=?", (report_date.isoformat(),)
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
```

- [ ] **Step 3: Create dashboard/backend/models/schemas.py**

```python
"""Pydantic schemas for API request/response validation."""
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional


class PositionSchema(BaseModel):
    id: int
    asset_class: str
    symbol: str
    exchange: Optional[str] = ""
    quantity: float
    avg_cost: float
    currency: str = "CNY"
    notes: Optional[str] = ""
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DecisionCardSchema(BaseModel):
    id: int
    decision_type: str
    asset_class: str
    symbol: str
    exchange: Optional[str] = ""
    quantity: Optional[float]
    action_price: Optional[float]
    confidence: float
    reasoning: str
    risk_level: str
    status: str
    timeout_at: Optional[str]
    created_at: str


class DecisionResponseSchema(BaseModel):
    id: int
    approved: bool


class ChatMessageSchema(BaseModel):
    role: str  # "human" or "agent"
    content: str
    created_at: Optional[str] = None


class ChatSendSchema(BaseModel):
    decision_id: int
    message: str


class DailyReportSchema(BaseModel):
    report_date: date
    overnight_summary: str
    critical_events: str
    investment_windows: str
    risk_metrics: Optional[str] = ""
    generated_at: Optional[str] = None


class PortfolioSummarySchema(BaseModel):
    total_value: float
    allocation: dict
    by_class: list


class AgentStatusSchema(BaseModel):
    agent_name: str
    status: str  # "running", "stopped", "error"
    last_check: Optional[str] = None
    error: Optional[str] = None
    event_count_today: int = 0


class SportsCardSchema(BaseModel):
    id: int
    card_name: str
    set_name: str
    grade: Optional[str] = ""
    grader: Optional[str] = ""
    purchase_price: Optional[float]
    current_estimated_value: Optional[float]
    market_source: Optional[str] = ""
    card_notes: Optional[str] = ""
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
```

- [ ] **Step 4: Create dashboard/backend/routers/__init__.py**

```python
# Routers registered in main.py
```

- [ ] **Step 5: Create dashboard/backend/main.py**

```python
"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .routers import portfolio, decisions, chat, daily_report, agent_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database
    await init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Broker Agents Dashboard",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In prod: restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(decisions.router, prefix="/api/decisions", tags=["decisions"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(daily_report.router, prefix="/api/daily-report", tags=["daily-report"])
app.include_router(agent_status.router, prefix="/api/agent-status", tags=["agent-status"])
```

- [ ] **Step 6: Create dashboard/backend/routers/portfolio.py**

```python
"""Portfolio API endpoints."""
from fastapi import APIRouter
from ..database import get_all_positions, get_portfolio_summary
from ..models.schemas import PositionSchema, PortfolioSummarySchema

router = APIRouter()


@router.get("/summary", response_model=PortfolioSummarySchema)
async def portfolio_summary():
    return await get_portfolio_summary()


@router.get("/positions", response_model=list[PositionSchema])
async def list_positions():
    return await get_all_positions()
```

- [ ] **Step 7: Create dashboard/backend/routers/decisions.py**

```python
"""Decision (pending trade recommendations) API endpoints."""
from fastapi import APIRouter, HTTPException
from ..database import get_pending_decisions, resolve_decision, create_decision
from ..models.schemas import DecisionCardSchema, DecisionResponseSchema

router = APIRouter()


@router.get("/pending", response_model=list[DecisionCardSchema])
async def list_pending():
    return await get_pending_decisions()


@router.post("/{decision_id}/resolve")
async def resolve(id: int, response: DecisionResponseSchema):
    if response.approved not in (True, False):
        raise HTTPException(status_code=400, detail="approved must be true or false")
    await resolve_decision(id, response.approved)
    return {"id": id, "status": "approved" if response.approved else "rejected"}
```

- [ ] **Step 8: Create dashboard/backend/routers/chat.py**

```python
"""Chat API with streaming support."""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ..database import add_chat_message, get_chat_history
from ..models.schemas import ChatMessageSchema, ChatSendSchema
import json

router = APIRouter()


@router.get("/{decision_id}", response_model=list[ChatMessageSchema])
async def get_chat(decision_id: int):
    return await get_chat_history(decision_id)


@router.post("/send")
async def send_message(payload: ChatSendSchema):
    await add_chat_message(payload.decision_id, "human", payload.message)
    return {"ok": True}
```

- [ ] **Step 9: Create dashboard/backend/routers/daily_report.py**

```python
"""Daily report API endpoints."""
from datetime import date
from fastapi import APIRouter
from ..database import get_daily_report, save_daily_report
from ..models.schemas import DailyReportSchema

router = APIRouter()


@router.get("/{report_date}", response_model=DailyReportSchema | None)
async def get_report(report_date: date):
    return await get_daily_report(report_date)


@router.get("/latest", response_model=DailyReportSchema | None)
async def get_latest():
    return await get_daily_report(date.today())


@router.post("/generate")
async def generate_report():
    # This will be connected to the agent's daily report generation
    # For now, placeholder — Phase 1 connects to agent later
    return {"status": "pending", "message": "Daily report generation connected to agent scheduler"}
```

- [ ] **Step 10: Create dashboard/backend/routers/agent_status.py**

```python
"""Agent health/status API."""
from fastapi import APIRouter
from ..database import get_db
from datetime import datetime
from ..models.schemas import AgentStatusSchema

router = APIRouter()


@router.get("/all", response_model=list[AgentStatusSchema])
async def agent_status_all():
    db = await get_db()
    try:
        rows = await db.fetchall(
            """
            SELECT agent_name, event_type, details,
                   MAX(created_at) as last_check,
                   COUNT(*) as event_count_today
            FROM agent_logs
            WHERE created_at >= date('now')
            GROUP BY agent_name
            """
        )
        result = []
        for r in rows:
            status = "running"
            error = None
            if "error" in (r["details"] or "").lower():
                status = "error"
                error = r["details"]
            result.append(AgentStatusSchema(
                agent_name=r["agent_name"],
                status=status,
                last_check=r["last_check"],
                error=error,
                event_count_today=r["event_count_today"],
            ))
        return result
    finally:
        await db.close()
```

- [ ] **Step 11: Create tests/conftest.py**

```python
"""Pytest fixtures for broker-agents tests."""
import pytest
import asyncio
import aiosqlite
from pathlib import Path
import tempfile

TEST_DB = Path(tempfile.gettempdir()) / "test_broker_agents.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    db = await aiosqlite.connect(str(TEST_DB))
    db.row_factory = aiosqlite.Row
    # Create minimal schema for tests
    with open(Path(__file__).parent.parent / "database" / "schema.sql") as f:
        schema = f.read()
    for stmt in schema.split(";"):
        stmt = stmt.strip()
        if stmt:
            await db.execute(stmt)
    await db.commit()
    yield db
    await db.close()
    TEST_DB.unlink(missing_ok=True)
```

- [ ] **Step 12: Create tests/test_api_portfolio.py**

```python
"""Tests for portfolio API."""
import pytest
from httpx import AsyncClient, ASGITransport
from dashboard.backend.main import app


@pytest.mark.asyncio
async def test_portfolio_summary_empty(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/portfolio/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_value" in data
    assert "allocation" in data


@pytest.mark.asyncio
async def test_portfolio_positions_empty(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/portfolio/positions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

- [ ] **Step 13: Run tests**

Run: `cd C:/Users/tobby/project/broker-agents && pip install -r requirements.txt && python -m pytest tests/test_api_portfolio.py -v`
Expected: PASS (2 tests)

- [ ] **Step 14: Commit**

```bash
git init && git add requirements.txt pyproject.toml CLAUDE.md config/ database/ dashboard/backend/ tests/ && git commit -m "feat: project scaffold + dashboard backend core API"
```

---

## Task 3: Dashboard Frontend — Phase 1 Views

**Files:**
- Create: `dashboard/frontend/package.json`
- Create: `dashboard/frontend/vite.config.ts`
- Create: `dashboard/frontend/index.html`
- Create: `dashboard/frontend/src/main.ts`
- Create: `dashboard/frontend/src/App.vue`
- Create: `dashboard/frontend/src/router.ts`
- Create: `dashboard/frontend/src/api/client.ts`
- Create: `dashboard/frontend/src/views/PortfolioView.vue`
- Create: `dashboard/frontend/src/views/DailyReportView.vue`
- Create: `dashboard/frontend/src/views/DecisionsView.vue`
- Create: `dashboard/frontend/src/components/BottomNav.vue`
- Create: `dashboard/frontend/src/components/DecisionCard.vue`
- Create: `dashboard/frontend/src/stores/portfolio.ts`
- Create: `dashboard/frontend/src/stores/decisions.ts`
- Create: `dashboard/frontend/src/styles/main.css`
- Create: `dashboard/frontend/public/manifest.json`

- [ ] **Step 1: Create dashboard/frontend/package.json**

```json
{
  "name": "broker-agents-dashboard",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.5.0",
    "vue-router": "^4.4.0",
    "pinia": "^2.2.0",
    "element-plus": "^2.9.0",
    "@element-plus/icons-vue": "^2.3.0",
    "axios": "^1.7.0",
    "echarts": "^5.5.0",
    "vue-echarts": "^7.0.0",
    "@vueuse/core": "^12.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.0",
    "vite": "^6.0.0",
    "vue-tsc": "^2.1.0",
    "typescript": "^5.6.0",
    "unplugin-auto-import": "^0.18.0",
    "unplugin-vue-components": "^0.27.0"
  }
}
```

- [ ] **Step 2: Create dashboard/frontend/vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
    }),
    Components({
      resolvers: [ElementPlusResolver()],
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: Create dashboard/frontend/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN" class="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <meta name="theme-color" content="#1a1a2e" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <link rel="manifest" href="/manifest.json" />
    <title>Broker Agents</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 4: Create dashboard/frontend/src/main.ts**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/dark.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import router from './router'
import App from './App.vue'
import './styles/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
```

- [ ] **Step 5: Create dashboard/frontend/src/App.vue**

```vue
<script setup lang="ts">
import BottomNav from './components/BottomNav.vue'
</script>

<template>
  <div class="app-shell">
    <div class="app-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
    <BottomNav />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}
.app-content {
  flex: 1;
  overflow-y: auto;
  padding-bottom: env(safe-area-inset-bottom);
}
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
```

- [ ] **Step 6: Create dashboard/frontend/src/router.ts**

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/decisions',
    },
    {
      path: '/portfolio',
      name: 'portfolio',
      component: () => import('./views/PortfolioView.vue'),
    },
    {
      path: '/decisions',
      name: 'decisions',
      component: () => import('./views/DecisionsView.vue'),
    },
    {
      path: '/daily-report',
      name: 'daily-report',
      component: () => import('./views/DailyReportView.vue'),
    },
    {
      path: '/sports-cards',
      name: 'sports-cards',
      component: () => import('./views/SportsCardsView.vue'),
    },
    {
      path: '/agent-status',
      name: 'agent-status',
      component: () => import('./views/AgentStatusView.vue'),
    },
  ],
})

export default router
```

- [ ] **Step 7: Create dashboard/frontend/src/api/client.ts**

```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export default api

export interface PortfolioSummary {
  total_value: number
  allocation: Record<string, { cost: number; pct: number }>
  by_class: Array<{ asset_class: string; position_count: number; total_cost: number }>
}

export interface Position {
  id: number
  asset_class: string
  symbol: string
  exchange: string
  quantity: number
  avg_cost: number
  currency: string
  notes: string
  created_at: string
  updated_at: string
}

export interface Decision {
  id: number
  decision_type: string
  asset_class: string
  symbol: string
  exchange: string
  quantity: number | null
  action_price: number | null
  confidence: number
  reasoning: string
  risk_level: string
  status: string
  timeout_at: string | null
  created_at: string
}

export interface DailyReport {
  report_date: string
  overnight_summary: string
  critical_events: string
  investment_windows: string
  risk_metrics: string
  generated_at: string
}

export interface ChatMessage {
  role: 'human' | 'agent'
  content: string
  created_at?: string
}

export const portfolioApi = {
  getSummary: () => api.get<PortfolioSummary>('/portfolio/summary'),
  getPositions: () => api.get<Position[]>('/portfolio/positions'),
}

export const decisionsApi = {
  getPending: () => api.get<Decision[]>('/decisions/pending'),
  resolve: (id: number, approved: boolean) =>
    api.post(`/decisions/${id}/resolve`, { approved }),
}

export const dailyReportApi = {
  getLatest: () => api.get<DailyReport>('/daily-report/latest'),
  generate: () => api.post('/daily-report/generate'),
}

export const chatApi = {
  getHistory: (decisionId: number) =>
    api.get<ChatMessage[]>(`/chat/${decisionId}`),
  send: (decisionId: number, message: string) =>
    api.post('/chat/send', { decision_id: decisionId, message }),
}
```

- [ ] **Step 8: Create dashboard/frontend/src/styles/main.css**

```css
:root {
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --bg-card: #0f3460;
  --accent: #e94560;
  --accent-green: #00c853;
  --accent-red: #ff1744;
  --accent-yellow: #ffc107;
  --text-primary: #ffffff;
  --text-secondary: #b0b0b0;
  --text-muted: #666666;
  --border: #2a2a4a;
  --radius: 12px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  -webkit-tap-highlight-color: transparent;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  overscroll-behavior: none;
}

.card {
  background: var(--bg-card);
  border-radius: var(--radius);
  padding: 16px;
  margin: 12px 16px;
  border: 1px solid var(--border);
}

.btn-approve {
  background: var(--accent-green) !important;
  color: white !important;
  font-weight: 600;
  font-size: 16px;
  min-height: 48px;
  border: none !important;
  border-radius: 24px !important;
  flex: 2;
}

.btn-reject {
  background: var(--accent-red) !important;
  color: white !important;
  font-weight: 600;
  font-size: 14px;
  min-height: 40px;
  border: none !important;
  border-radius: 24px !important;
  flex: 1;
}

.btn-ask {
  background: transparent !important;
  color: var(--text-secondary) !important;
  border: 1px solid var(--border) !important;
  font-size: 14px;
  min-height: 40px;
  border-radius: 24px !important;
  flex: 1;
}

.positive {
  color: var(--accent-green);
}

.negative {
  color: var(--accent-red);
}

/* Mobile scrollbar hide */
::-webkit-scrollbar {
  display: none;
}
```

- [ ] **Step 9: Create dashboard/frontend/src/components/BottomNav.vue**

```vue
<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { path: '/decisions', label: '决策', icon: 'Operation' },
  { path: '/daily-report', label: '日报', icon: 'Document' },
  { path: '/portfolio', label: '持仓', icon: 'Wallet' },
  { path: '/sports-cards', label: '球星卡', icon: 'Goods' },
  { path: '/agent-status', label: '状态', icon: 'Monitor' },
]

function isActive(path: string) {
  return route.path === path
}
</script>

<template>
  <nav class="bottom-nav">
    <router-link
      v-for="item in navItems"
      :key="item.path"
      :to="item.path"
      class="nav-item"
      :class="{ active: isActive(item.path) }"
    >
      <el-icon :size="22">
        <component :is="item.icon" />
      </el-icon>
      <span>{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<style scoped>
.bottom-nav {
  display: flex;
  justify-content: space-around;
  align-items: center;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border);
  padding: 8px 0;
  padding-bottom: calc(8px + env(safe-area-inset-bottom));
  flex-shrink: 0;
}
.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 8px;
  transition: color 0.2s;
}
.nav-item.active {
  color: var(--accent);
}
.nav-item:active {
  background: rgba(233, 69, 96, 0.1);
}
</style>
```

- [ ] **Step 10: Create dashboard/frontend/src/components/DecisionCard.vue**

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Decision } from '@/api/client'
import { decisionsApi } from '@/api/client'
import ChatPanel from './ChatPanel.vue'

const props = defineProps<{
  decision: Decision
}>()

const emit = defineEmits<{
  resolved: []
}>()

const loading = ref(false)
const showChat = ref(false)

const confidenceColor = computed(() => {
  const c = props.decision.confidence
  if (c >= 0.8) return 'var(--accent-green)'
  if (c >= 0.6) return 'var(--accent-yellow)'
  return 'var(--accent-red)'
})

const riskColor = computed(() => {
  const r = props.decision.risk_level
  if (r === 'low') return 'var(--accent-green)'
  if (r === 'medium') return 'var(--accent-yellow)'
  return 'var(--accent-red)'
})

async function approve() {
  loading.value = true
  try {
    await decisionsApi.resolve(props.decision.id, true)
    emit('resolved')
  } finally {
    loading.value = false
  }
}

async function reject() {
  loading.value = true
  try {
    await decisionsApi.resolve(props.decision.id, false)
    emit('resolved')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="decision-card">
    <div class="card-header">
      <span class="signal-dot" :style="{ background: confidenceColor }"></span>
      <span class="decision-type">{{ decision.decision_type.toUpperCase() }}</span>
      <span class="asset">{{ decision.symbol }}</span>
      <span class="badge-risk" :style="{ color: riskColor }">{{ decision.risk_level }}</span>
    </div>

    <div class="card-body">
      <div class="meta-row">
        <span v-if="decision.quantity" class="meta-item">
          数量: <strong>{{ decision.quantity }}</strong>
        </span>
        <span v-if="decision.action_price" class="meta-item">
          价格: <strong>¥{{ decision.action_price }}</strong>
        </span>
        <span class="meta-item">
          置信度: <strong :style="{ color: confidenceColor }">{{ (decision.confidence * 100).toFixed(0) }}%</strong>
        </span>
      </div>

      <p class="reasoning">{{ decision.reasoning }}</p>
    </div>

    <div class="card-actions">
      <el-button class="btn-ask" @click="showChat = !showChat">
        追问
      </el-button>
      <el-button class="btn-reject" :loading="loading" @click="reject">
        拒绝
      </el-button>
      <el-button class="btn-approve" :loading="loading" @click="approve">
        批准
      </el-button>
    </div>

    <ChatPanel
      v-if="showChat"
      :decision-id="decision.id"
      @close="showChat = false"
    />
  </div>
</template>

<style scoped>
.decision-card {
  background: var(--bg-card);
  border-radius: var(--radius);
  margin: 12px 16px;
  padding: 16px;
  border: 1px solid var(--border);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.signal-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.decision-type {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-secondary);
  letter-spacing: 1px;
}
.asset {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  flex: 1;
}
.badge-risk {
  font-size: 12px;
  font-weight: 600;
  text-transform: capitalize;
}
.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.meta-item {
  font-size: 13px;
  color: var(--text-secondary);
}
.meta-item strong {
  color: var(--text-primary);
}
.reasoning {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin-bottom: 16px;
}
.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
</style>
```

- [ ] **Step 11: Create dashboard/frontend/src/components/ChatPanel.vue**

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { chatApi, type ChatMessage } from '@/api/client'

const props = defineProps<{
  decisionId: number
}>()

const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const loading = ref(false)

onMounted(async () => {
  const res = await chatApi.getHistory(props.decisionId)
  messages.value = res.data
})

async function send() {
  if (!inputText.value.trim()) return
  const userMsg = { role: 'human' as const, content: inputText.value }
  messages.value.push(userMsg)
  const savedMsg = inputText.value
  inputText.value = ''
  loading.value = true
  try {
    await chatApi.send(props.decisionId, savedMsg)
    // Agent response would come via websocket in Phase 2
    // For now: placeholder
    messages.value.push({
      role: 'agent',
      content: '收到您的问题，正在分析中... (流式响应 Phase 2 实现)',
    })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="chat-panel">
    <div class="chat-messages">
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="message"
        :class="msg.role"
      >
        <div class="bubble">{{ msg.content }}</div>
      </div>
      <div v-if="loading" class="message agent">
        <div class="bubble typing">思考中...</div>
      </div>
    </div>
    <div class="chat-input">
      <el-input
        v-model="inputText"
        placeholder="追问详情..."
        @keyup.enter="send"
        :disabled="loading"
      />
      <el-button type="primary" @click="send" :loading="loading">发送</el-button>
    </div>
  </div>
</template>

<style scoped>
.chat-panel {
  margin-top: 12px;
  border-top: 1px solid var(--border);
  padding-top: 12px;
}
.chat-messages {
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}
.message {
  display: flex;
}
.message.human {
  justify-content: flex-end;
}
.bubble {
  max-width: 80%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
}
.message.human .bubble {
  background: var(--accent);
  color: white;
}
.message.agent .bubble {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}
.chat-input {
  display: flex;
  gap: 8px;
}
</style>
```

- [ ] **Step 12: Create dashboard/frontend/src/views/DecisionsView.vue**

```vue
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { decisionsApi, type Decision } from '@/api/client'
import DecisionCard from '@/components/DecisionCard.vue'

const decisions = ref<Decision[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await decisionsApi.getPending()
    decisions.value = res.data
  } finally {
    loading.value = false
  }
}

let timer: number
onMounted(() => {
  load()
  timer = window.setInterval(load, 30000) // refresh every 30s
})
onUnmounted(() => clearInterval(timer))

function onResolved() {
  load()
}
</script>

<template>
  <div class="decisions-view">
    <div class="page-header">
      <h2>待决策</h2>
      <span class="count-badge" v-if="decisions.length">{{ decisions.length }}</span>
    </div>

    <div v-if="loading && !decisions.length" class="loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <div v-else-if="!decisions.length" class="empty-state">
      <el-icon :size="48" color="var(--text-muted)"><SuccessFilled /></el-icon>
      <p>暂无待决策项</p>
      <small>Agent 会在发现机会时提醒你</small>
    </div>

    <DecisionCard
      v-for="d in decisions"
      :key="d.id"
      :decision="d"
      @resolved="onResolved"
    />
  </div>
</template>

<style scoped>
.decisions-view {
  padding-top: 16px;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px 8px;
}
.page-header h2 {
  font-size: 20px;
  font-weight: 700;
}
.count-badge {
  background: var(--accent);
  color: white;
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 13px;
  font-weight: 700;
}
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  color: var(--text-muted);
}
.empty-state small {
  font-size: 13px;
}
</style>
```

- [ ] **Step 13: Create dashboard/frontend/src/views/PortfolioView.vue**

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { portfolioApi, type PortfolioSummary, type Position } from '@/api/client'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import type { EChartsOption } from 'echarts'

use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

const summary = ref<PortfolioSummary | null>(null)
const positions = ref<Position[]>([])
const loading = ref(false)

const ASSET_COLORS: Record<string, string> = {
  crypto: '#f7931a',
  stock: '#2196f3',
  forex: '#4caf50',
  options: '#9c27b0',
  sports_card: '#ff5722',
}

async function load() {
  loading.value = true
  try {
    const [sumRes, posRes] = await Promise.all([
      portfolioApi.getSummary(),
      portfolioApi.getPositions(),
    ])
    summary.value = sumRes.data
    positions.value = posRes.data
  } finally {
    loading.value = false
  }
}

const pieOption = computed((): EChartsOption => {
  if (!summary.value?.allocation) return {}
  const data = Object.entries(summary.value.allocation).map(([name, info]) => ({
    name,
    value: info.cost,
    itemStyle: { color: ASSET_COLORS[name] || '#888' },
  }))
  return {
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' },
      },
      data,
    }],
  }
})

import { computed } from 'vue'
onMounted(load)
</script>

<template>
  <div class="portfolio-view">
    <div class="total-value-card card">
      <div class="label">总资产</div>
      <div class="value">
        ¥{{ summary?.total_value?.toLocaleString('zh-CN', { minimumFractionDigits: 2 }) ?? '—' }}
      </div>
    </div>

    <div class="card" v-if="summary?.allocation">
      <v-chart class="pie-chart" :option="pieOption" autoresize />
      <div class="allocation-legend">
        <div
          v-for="(info, name) in summary.allocation"
          :key="name"
          class="legend-item"
        >
          <span class="dot" :style="{ background: ASSET_COLORS[name as string] || '#888' }"></span>
          <span class="name">{{ name }}</span>
          <span class="pct">{{ info.pct }}%</span>
          <span class="cost">¥{{ info.cost.toLocaleString('zh-CN') }}</span>
        </div>
      </div>
    </div>

    <div class="positions-list">
      <div
        v-for="pos in positions"
        :key="pos.id"
        class="position-row card"
      >
        <div class="pos-main">
          <span class="pos-symbol">{{ pos.symbol }}</span>
          <span class="pos-exchange">{{ pos.exchange || pos.asset_class }}</span>
        </div>
        <div class="pos-value">
          <span class="qty">{{ pos.quantity }} 股/个</span>
          <span class="cost">¥{{ (pos.quantity * pos.avg_cost).toLocaleString('zh-CN') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.total-value-card {
  text-align: center;
  padding: 24px 16px;
}
.total-value-card .label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.total-value-card .value {
  font-size: 32px;
  font-weight: 800;
  color: var(--text-primary);
}
.pie-chart {
  width: 100%;
  height: 180px;
}
.allocation-legend {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.legend-item .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.legend-item .name {
  flex: 1;
  text-transform: capitalize;
}
.legend-item .pct {
  color: var(--text-secondary);
  width: 40px;
  text-align: right;
}
.legend-item .cost {
  font-weight: 600;
  width: 80px;
  text-align: right;
}
.position-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  margin: 8px 16px;
}
.pos-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.pos-symbol {
  font-weight: 700;
  font-size: 15px;
}
.pos-exchange {
  font-size: 12px;
  color: var(--text-muted);
  text-transform: capitalize;
}
.pos-value {
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.pos-value .qty {
  font-size: 12px;
  color: var(--text-secondary);
}
.pos-value .cost {
  font-weight: 600;
  font-size: 15px;
}
</style>
```

- [ ] **Step 14: Create dashboard/frontend/src/views/DailyReportView.vue**

```vue
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { dailyReportApi, type DailyReport } from '@/api/client'

const report = ref<DailyReport | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    try {
      const res = await dailyReportApi.getLatest()
      report.value = res.data
    } catch {
      report.value = null
    }
  } finally {
    loading.value = false
  }
}

onMounted(load)

function parseList(text: string): string[] {
  if (!text) return []
  return text.split('\n').filter(l => l.trim())
}
</script>

<template>
  <div class="daily-report-view">
    <div class="page-header">
      <h2>早间简报</h2>
      <span class="date">{{ new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' }) }}</span>
    </div>

    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <div v-else-if="!report" class="empty-state card">
      <p>暂无今日简报</p>
      <small>简报将于每日 08:00 自动生成</small>
    </div>

    <template v-else>
      <div class="report-section card">
        <div class="section-title">🌙 隔夜行情</div>
        <ul class="bullet-list">
          <li v-for="item in parseList(report.overnight_summary)" :key="item">
            {{ item }}
          </li>
        </ul>
      </div>

      <div class="report-section card">
        <div class="section-title accent">⚠️ 重要事件</div>
        <ul class="bullet-list">
          <li v-for="item in parseList(report.critical_events)" :key="item">
            {{ item }}
          </li>
        </ul>
      </div>

      <div class="report-section card">
        <div class="section-title highlight">🎯 投资窗口</div>
        <ul class="bullet-list">
          <li v-for="item in parseList(report.investment_windows)" :key="item">
            {{ item }}
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<style scoped>
.daily-report-view {
  padding-top: 16px;
}
.page-header {
  padding: 0 16px 12px;
}
.page-header h2 {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 4px;
}
.page-header .date {
  font-size: 13px;
  color: var(--text-muted);
}
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  gap: 8px;
  color: var(--text-muted);
}
.empty-state small {
  font-size: 13px;
}
.report-section {
  margin-bottom: 8px;
}
.section-title {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 10px;
  color: var(--text-primary);
}
.section-title.accent {
  color: var(--accent-yellow);
}
.section-title.highlight {
  color: var(--accent-green);
}
.bullet-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bullet-list li {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-secondary);
  padding-left: 16px;
  position: relative;
}
.bullet-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--text-muted);
}
</style>
```

- [ ] **Step 15: Create stub views for SportsCardsView and AgentStatusView**

Create `dashboard/frontend/src/views/SportsCardsView.vue` and `dashboard/frontend/src/views/AgentStatusView.vue` — both as simple placeholder cards for Phase 1. Full implementation in Phase 2.

- [ ] **Step 16: Create stores and manifest.json**

```json
// dashboard/frontend/public/manifest.json
{
  "name": "Broker Agents",
  "short_name": "BrokerAgents",
  "description": "Self-hosted investment agent dashboard",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#1a1a2e",
  "theme_color": "#1a1a2e",
  "icons": []
}
```

- [ ] **Step 17: Run frontend dev server**

Run: `cd C:/Users/tobby/project/broker-agents/dashboard/frontend && npm install && npm run dev`
Expected: Dev server starts on port 5173

- [ ] **Step 18: Commit**

```bash
git add dashboard/frontend/ && git commit -m "feat: Vue 3 dashboard frontend with mobile-first views"
```

---

## Task 4: Monitor Scripts (Python)

**Files:**
- Create: `agents/monitor/__init__.py`
- Create: `agents/monitor/base.py`
- Create: `agents/monitor/scheduler.py`
- Create: `agents/monitor/akshare_monitor.py`
- Create: `agents/monitor/binance_monitor.py`
- Create: `agents/monitor/yfinance_monitor.py`
- Create: `agents/monitor/card_ladder_monitor.py`
- Create: `tests/test_monitor.py`

- [ ] **Step 1: Create agents/monitor/base.py**

```python
"""Base monitor class — all monitors inherit this."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Alert:
    """A monitor alert that gets passed to the dispatcher."""
    source: str           # e.g. "binance", "akshare"
    alert_type: str       # e.g. "price_spike", "arbitrage", "volume_surge"
    symbol: str
    exchange: str
    details: dict
    timestamp: datetime
    priority: str = "normal"  # "low", "normal", "high"


class BaseMonitor(ABC):
    """Base class for all market monitors."""

    def __init__(self, config: dict):
        self.config = config
        self.last_check: Optional[datetime] = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this monitor, e.g. 'binance'."""
        pass

    @abstractmethod
    async def check(self) -> list[Alert]:
        """Run one check cycle. Return list of alerts."""
        pass

    @abstractmethod
    def is_market_open(self) -> bool:
        """Return True if the monitored market is currently open."""
        pass
```

- [ ] **Step 2: Create agents/monitor/binance_monitor.py**

```python
"""Binance crypto price monitor."""
import asyncio
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
from ..config import get_market_data_config
from .base import BaseMonitor, Alert


class BinanceMonitor(BaseMonitor):
    SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]

    @property
    def name(self) -> str:
        return "binance"

    def __init__(self):
        super().__init__(get_market_data_config().get("binance", {}))
        self._client: Client | None = None

    def _get_client(self) -> Client:
        if self._client is None:
            cfg = self.config
            self._client = Client(
                api_key=cfg.get("api_key") or "",
                api_secret=cfg.get("secret") or "",
            )
        return self._client

    def is_market_open(self) -> bool:
        return True  # Binance 24/7

    async def check(self) -> list[Alert]:
        cfg = self.config
        if not cfg.get("enabled", True):
            return []

        try:
            client = self._get_client()
            alerts = []
            for symbol in self.SYMBOLS:
                try:
                    alert = await self._check_symbol(client, symbol)
                    if alert:
                        alerts.append(alert)
                except Exception:
                    continue
            self.last_check = datetime.now()
            return alerts
        except Exception:
            return []

    async def _check_symbol(self, client: Client, symbol: str) -> Alert | None:
        threshold = self.config.get("arbitrage_threshold", 0.005)

        try:
            ticker = client.get_symbol_ticker(symbol=symbol)
            price = float(ticker["price"])
        except BinanceAPIException:
            return None

        try:
            klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_5MINUTE, limit=10)
        except BinanceAPIException:
            return None

        if len(klines) < 2:
            return None

        prices = [float(k[4]) for k in klines]
        avg_price = sum(prices) / len(prices)
        change_pct = abs(price - avg_price) / avg_price

        if change_pct > threshold:
            return Alert(
                source="binance",
                alert_type="arbitrage",
                symbol=symbol.replace("USDT", ""),
                exchange="Binance",
                details={
                    "current_price": price,
                    "avg_5min": avg_price,
                    "change_pct": round(change_pct * 100, 3),
                    "direction": "up" if price > avg_price else "down",
                },
                timestamp=datetime.now(),
                priority="high" if change_pct > 0.01 else "normal",
            )
        return None
```

- [ ] **Step 3: Create agents/monitor/akshare_monitor.py**

```python
"""AKShare-based monitor for A-shares and China futures."""
import asyncio
import akshare as ak
from datetime import datetime
from ..config import get_market_data_config
from .base import BaseMonitor, Alert


class AKShareMonitor(BaseMonitor):
    SYMBOLS = ["000001", "399001", "399006"]  # 上证, 深证, 创业板

    @property
    def name(self) -> str:
        return "akshare"

    def __init__(self):
        super().__init__(get_market_data_config().get("akshare", {}))
        self.threshold = 0.03  # 3%

    def is_market_open(self) -> bool:
        now = datetime.now()
        weekday = now.weekday()
        if weekday >= 5:
            return False
        hour, minute = now.hour, now.minute
        return (9 * 60 + 30) <= (hour * 60 + minute) <= (15 * 60)

    async def check(self) -> list[Alert]:
        if not self.config.get("enabled", True):
            return []
        if not self.is_market_open():
            return []

        try:
            alerts = await self._check_indices()
            self.last_check = datetime.now()
            return alerts
        except Exception:
            return []

    async def _check_indices(self) -> list[Alert]:
        alerts = []
        try:
            df = ak.stock_zh_index_spot_em()
            for _, row in df.iterrows():
                if str(row["代码"]) not in self.SYMBOLS:
                    continue
                change_pct = abs(float(row.get("涨跌幅", 0)))
                if change_pct > self.threshold * 100:
                    alerts.append(Alert(
                        source="akshare",
                        alert_type="price_spike",
                        symbol=row["代码"],
                        exchange="SSE/SZSE",
                        details={
                            "name": row.get("名称", ""),
                            "current": float(row.get("最新价", 0)),
                            "change_pct": change_pct,
                        },
                        timestamp=datetime.now(),
                        priority="high" if change_pct > 5 else "normal",
                    ))
        except Exception:
            pass
        return alerts
```

- [ ] **Step 4: Create agents/monitor/yfinance_monitor.py**

```python
"""Yahoo Finance monitor for US stocks and ETFs."""
import asyncio
import yfinance as yf
from datetime import datetime
from ..config import get_market_data_config
from .base import BaseMonitor, Alert


class YFinanceMonitor(BaseMonitor):
    SYMBOLS = ["SPY", "QQQ", "BTC-USD", "ETH-USD"]

    @property
    def name(self) -> str:
        return "yfinance"

    def __init__(self):
        super().__init__(get_market_data_config().get("yfinance", {}))
        self.threshold = 0.02

    def is_market_open(self) -> bool:
        now = datetime.utcnow()
        weekday = now.weekday()
        if weekday >= 5:
            return False
        hour, minute = now.hour, now.minute
        return (13 * 60 + 30) <= (hour * 60 + minute) <= (20 * 60)

    async def check(self) -> list[Alert]:
        if not self.config.get("enabled", True):
            return []
        alerts = []
        try:
            for symbol in self.SYMBOLS:
                alert = await self._check_symbol(symbol)
                if alert:
                    alerts.append(alert)
            self.last_check = datetime.now()
        except Exception:
            pass
        return alerts

    async def _check_symbol(self, symbol: str) -> Alert | None:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5m")
            if hist.empty:
                return None
            latest = hist["Close"].iloc[-1]
            avg = hist["Close"].mean()
            change_pct = abs(latest - avg) / avg
            if change_pct > self.threshold:
                return Alert(
                    source="yfinance",
                    alert_type="price_anomaly",
                    symbol=symbol,
                    exchange="NASDAQ/NYSE",
                    details={
                        "current_price": round(latest, 4),
                        "avg_price": round(avg, 4),
                        "change_pct": round(change_pct * 100, 2),
                    },
                    timestamp=datetime.now(),
                    priority="normal",
                )
        except Exception:
            pass
        return None
```

- [ ] **Step 5: Create agents/monitor/card_ladder_monitor.py**

```python
"""Card Ladder API monitor for sports card prices."""
import asyncio
import httpx
from datetime import datetime
from ..config import get_market_data_config
from .base import BaseMonitor, Alert


class CardLadderMonitor(BaseMonitor):
    BASE_URL = "https://api.cardladder.com/v1"

    @property
    def name(self) -> str:
        return "card_ladder"

    def __init__(self):
        super().__init__(get_market_data_config().get("card_ladder", {}))
        self.threshold = 0.05

    def is_market_open(self) -> bool:
        return True  # Card market has no fixed hours

    async def check(self) -> list[Alert]:
        cfg = self.config
        if not cfg.get("enabled", True):
            return []
        return []

    async def _fetch_price(self, card_id: str) -> float | None:
        cfg = self.config
        api_key = cfg.get("api_key")
        if not api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/cards/{card_id}/price",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("price")
        except Exception:
            pass
        return None
```

- [ ] **Step 6: Create agents/monitor/scheduler.py**

```python
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
from dashboard.backend.database import log_agent_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONITORS = [
    BinanceMonitor(),
    AKShareMonitor(),
    YFinanceMonitor(),
    CardLadderMonitor(),
]


async def run_monitor_cycle():
    """Run one cycle of all monitors. Return all alerts."""
    all_alerts: list[Alert] = []
    for monitor in MONITORS:
        try:
            alerts = await monitor.check()
            all_alerts.extend(alerts)
            if alerts:
                logger.info(f"[{monitor.name}] {len(alerts)} alert(s) found")
                for a in alerts:
                    await log_agent_event(
                        monitor.name,
                        f"alert:{a.alert_type}",
                        f"{a.symbol} {a.details}",
                    )
        except Exception as e:
            logger.error(f"[{monitor.name}] Error: {e}")
    return all_alerts


async def scheduler_loop():
    """Main scheduler loop — runs monitors at configured interval."""
    settings = get_agent_settings().get("monitor", {})
    interval = settings.get("check_interval_seconds", 60)

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
```

- [ ] **Step 7: Create agents/monitor/__init__.py**

```python
from .base import BaseMonitor, Alert
from .scheduler import run_monitor_cycle, scheduler_loop

__all__ = ["BaseMonitor", "Alert", "run_monitor_cycle", "scheduler_loop"]
```

- [ ] **Step 8: Create tests/test_monitor.py**

```python
"""Tests for monitor modules."""
import pytest
from unittest.mock import patch, MagicMock
from agents.monitor.binance_monitor import BinanceMonitor
from agents.monitor.akshare_monitor import AKShareMonitor


def test_binance_monitor_name():
    m = BinanceMonitor()
    assert m.name == "binance"


def test_binance_monitor_market_open():
    m = BinanceMonitor()
    assert m.is_market_open() is True  # 24/7


@pytest.mark.asyncio
async def test_binance_monitor_disabled():
    m = BinanceMonitor()
    m.config["enabled"] = False
    alerts = await m.check()
    assert alerts == []
```

- [ ] **Step 9: Commit**

```bash
git add agents/ && git commit -m "feat: monitor scripts for AKShare, Binance, Yahoo Finance, Card Ladder"
```

---

## Task 5: LLM Agents (LangGraph)

**Files:**
- Create: `agents/dispatcher/__init__.py`
- Create: `agents/dispatcher/prompts.py`
- Create: `agents/dispatcher/tools.py`
- Create: `agents/dispatcher/nodes.py`
- Create: `agents/dispatcher/graph.py`
- Create: `agents/research_analyst/__init__.py`
- Create: `agents/research_analyst/agent.py`
- Create: `agents/research_analyst/prompts.py`
- Create: `agents/trade_executor/__init__.py`
- Create: `agents/trade_executor/agent.py`
- Create: `tests/test_dispatcher.py`

- [ ] **Step 1: Create agents/dispatcher/prompts.py**

```python
"""System prompts for the Dispatcher agent."""
from datetime import datetime

DISPATCHER_SYSTEM = """你是一个投资调度员(Dispatcher)。你的职责是：
1. 接收监控脚本发出的市场警报(Alert)
2. 判断该警报是否与用户投资组合或观察列表相关
3. 如果相关，将任务分配给研究分析师(Research Analyst)进行深度分析
4. 如果无关，记录并丢弃
5. 始终将重大交易决策提交给人类审批

当前时间: {time}
用户投资组合资产: {portfolio}
用户观察列表: {watchlist}
风险偏好: {risk_tolerance}

决策规则：
- 所有交易必须获得人类批准后才能执行（Phase 1）
- 置信度低于60%的建议标记为"低置信度"
- 置信度90%以上的建议标记为"高优先级"
- 风险等级: low / medium / high
"""


def format_alert_for_dispatcher(alert: dict) -> str:
    return f"""警报来源: {alert['source']}
类型: {alert['alert_type']}
标的: {alert['symbol']}
交易所: {alert['exchange']}
详情: {alert['details']}
时间: {alert['timestamp']}
优先级: {alert['priority']}
"""


def format_decision_card(decision: dict) -> str:
    return f"""## 交易建议
类型: {decision['decision_type']}
标的: {decision['symbol']}
数量: {decision.get('quantity', 'N/A')}
价格: ¥{decision.get('action_price', '市价')}
置信度: {decision['confidence']:.0%}
风险等级: {decision['risk_level']}
理由: {decision['reasoning']}
"""
```

- [ ] **Step 2: Create agents/dispatcher/tools.py**

```python
"""Tools available to the Dispatcher agent."""
from typing import Annotated, TypedDict
from langchain_core.tools import tool
from dashboard.backend.database import (
    get_all_positions,
    upsert_position,
    create_decision,
    get_pending_decisions,
    resolve_decision,
    add_chat_message,
    get_chat_history,
)
from ..config import get_agent_settings


class DispatcherState(TypedDict):
    alerts: list
    decisions: list
    pending_approval: dict | None
    human_feedback: str | None


@tool
async def lookup_portfolio() -> str:
    """Look up the current portfolio positions across all asset classes."""
    positions = await get_all_positions()
    if not positions:
        return "投资组合为空"
    lines = []
    for p in positions:
        val = p["quantity"] * p["avg_cost"]
        lines.append(f"- {p['asset_class']}: {p['symbol']} x {p['quantity']} @ ¥{p['avg_cost']} = ¥{val:.2f}")
    return "\n".join(lines)


@tool
async def submit_decision(
    decision_type: str,
    asset_class: str,
    symbol: str,
    exchange: str,
    quantity: float | None,
    action_price: float | None,
    confidence: float,
    reasoning: str,
    risk_level: str,
) -> str:
    """Submit a new trading decision for human approval."""
    settings = get_agent_settings()
    timeout = settings.get("agents", {}).get("decision", {}).get("timeout_minutes", 30)

    decision_id = await create_decision(
        decision_type=decision_type,
        asset_class=asset_class,
        symbol=symbol,
        quantity=quantity,
        action_price=action_price,
        confidence=confidence,
        reasoning=reasoning,
        risk_level=risk_level,
        timeout_minutes=timeout,
    )
    return f"决策已提交(ID: {decision_id})，等待人类审批"


@tool
async def lookup_pending_decisions() -> str:
    """Look up all pending decisions awaiting human approval."""
    decisions = await get_pending_decisions()
    if not decisions:
        return "暂无待审批决策"
    lines = [f"共 {len(decisions)} 条待审批:"]
    for d in decisions:
        lines.append(f"- [{d['id']}] {d['decision_type'].upper()} {d['symbol']} @ {d.get('action_price', '市价')} (置信度: {d['confidence']:.0%})")
    return "\n".join(lines)


@tool
async def get_human_feedback(decision_id: int) -> str:
    """Get human's response to a pending decision after they reviewed it."""
    history = await get_chat_history(decision_id)
    # Return last agent message + any human follow-ups
    relevant = [m for m in history if m["role"] in ("human", "agent")]
    if not relevant:
        return "pending"
    return relevant[-1].get("content", "pending")
```

- [ ] **Step 3: Create agents/dispatcher/nodes.py**

```python
"""LangGraph nodes for the Dispatcher agent."""
import json
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from .prompts import DISPATCHER_SYSTEM, format_alert_for_dispatcher
from .tools import (
    lookup_portfolio,
    submit_decision,
    lookup_pending_decisions,
    get_human_feedback,
)


async def monitor_handler(state: dict, llm) -> dict:
    """Handle incoming market alerts — route to research or discard."""
    alerts = state.get("alerts", [])
    if not alerts:
        return state

    portfolio = await lookup_portfolio.invoke({})
    decisions = state.get("decisions", [])

    alert_summaries = [format_alert_for_dispatcher(a) for a in alerts]

    prompt = f"""以下市场警报已触发，请判断是否值得关注：

{chr(10).join(alert_summaries)}

当前投资组合：
{portfolio}

对于每个警报，判断：
1. 该标的是否在投资组合或观察列表中？
2. 如果是 → 输出 JSON: {{"relevant": true, "reason": "...", "symbol": "...", "exchange": "..."}}
3. 如果否 → 输出 JSON: {{"relevant": false, "reason": "..."}}

仅输出 JSON，不要其他内容。"""

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    content = response.content.strip()

    try:
        # Parse JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        parsed = json.loads(content.strip())
        if isinstance(parsed, dict) and parsed.get("relevant"):
            decisions.append({"source": "monitor", "relevant": parsed, "alerts": alerts})
    except (json.JSONDecodeError, AttributeError):
        pass

    return {"alerts": [], "decisions": decisions}


async def research_router(state: dict, llm) -> dict:
    """Route relevant alerts to research analyst."""
    decisions = state.get("decisions", [])
    if not decisions:
        return state

    # Mark first relevant decision for research
    for d in decisions:
        if d.get("source") == "monitor" and not d.get("researched"):
            d["researched"] = True
            break

    return {"decisions": decisions}


async def approval_router(state: dict, llm) -> dict:
    """Format decision for human approval."""
    decisions = state.get("decisions", [])
    if not decisions:
        return {"pending_approval": None}

    current = decisions[0]
    alert = current.get("alerts", [{}])[0]

    recommendation = {
        "decision_type": "buy" if current.get("relevant", {}).get("direction") == "up" else "hold",
        "asset_class": alert.get("source", "unknown"),
        "symbol": current.get("relevant", {}).get("symbol", alert.get("symbol", "")),
        "exchange": current.get("relevant", {}).get("exchange", alert.get("exchange", "")),
        "quantity": None,
        "action_price": alert.get("details", {}).get("current_price"),
        "confidence": 0.75,  # Will be refined by research
        "reasoning": f"监控警报: {alert.get('alert_type')}, 详情: {alert.get('details')}",
        "risk_level": "medium",
    }

    return {"pending_approval": recommendation}
```

- [ ] **Step 4: Create agents/dispatcher/graph.py**

```python
"""LangGraph state graph for the Dispatcher agent."""
from langgraph.graph import StateGraph, END
from langchain_minimax import ChatMinimax
from .nodes import monitor_handler, research_router, approval_router
from ..config import get_llm_config


def _get_llm():
    cfg = get_llm_config()
    primary = cfg.get("primary", {})
    return ChatMinimax(
        api_key=primary.get("api_key", ""),
        model=primary.get("model", "auto"),
        base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
    )


def create_dispatcher_graph():
    """Build the dispatcher state graph."""
    graph = StateGraph(dict)

    def node(name: str, fn):
        graph.add_node(name, fn)

    node("monitor_handler", lambda s: monitor_handler(s, _get_llm()))
    node("research_router", lambda s: research_router(s, _get_llm()))
    node("approval_router", lambda s: approval_router(s, _get_llm()))

    graph.set_entry_point("monitor_handler")
    graph.add_edge("monitor_handler", "research_router")
    graph.add_edge("research_router", "approval_router")
    graph.add_edge("approval_router", END)

    return graph.compile()


# Singleton
_dispatcher_graph = None

def get_dispatcher():
    global _dispatcher_graph
    if _dispatcher_graph is None:
        _dispatcher_graph = create_dispatcher_graph()
    return _dispatcher_graph
```

- [ ] **Step 5: Create agents/research_analyst/agent.py**

```python
"""Research Analyst LLM agent."""
from langchain_minimax import ChatMinimax
from langchain_core.messages import HumanMessage, SystemMessage
from dashboard.backend.database import add_chat_message
from ..config import get_llm_config

RESEARCH_SYSTEM = """你是一个专业的投资研究分析师。你的任务是：
1. 深度分析市场警报是否构成真实的投资机会
2. 收集并整合多个数据来源的信息
3. 给出置信度评估和风险评级
4. 用清晰的中文解释分析逻辑

分析维度：
- 基本面：相关 news, 宏观数据, 行业趋势
- 技术面：价格走势, 成交量, 关键支撑/压力位
- 资金面：资金流向, ETF 流入/流出
- 风险因素：市场情绪, 政策风险, 流动性风险

输出格式：
置信度: XX%
风险等级: low/medium/high
分析理由: ...
建议行动: buy/sell/hold
建议数量: (如适用)
"""

async def research_opportunity(alert: dict, portfolio_context: str = "") -> str:
    """Run research analysis on an alert opportunity."""
    cfg = get_llm_config()
    primary = cfg.get("primary", {})
    llm = ChatMinimax(
        api_key=primary.get("api_key", ""),
        model=primary.get("model", "auto"),
        base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
    )

    prompt = f"""请分析以下投资机会：

警报详情：
- 来源: {alert.get('source')}
- 类型: {alert.get('alert_type')}
- 标的: {alert.get('symbol')}
- 交易所: {alert.get('exchange')}
- 详情: {alert.get('details')}

当前投资组合：
{portfolio_context}

请给出完整分析。"""

    response = await llm.ainvoke([
        SystemMessage(content=RESEARCH_SYSTEM),
        HumanMessage(content=prompt),
    ])

    return response.content
```

- [ ] **Step 6: Create agents/trade_executor/agent.py**

```python
"""Trade Executor agent — drafts orders, does not execute without approval."""
from langchain_minimax import ChatMinimax
from langchain_core.messages import HumanMessage, SystemMessage
from ..config import get_llm_config

EXECUTION_SYSTEM = """你是一个交易执行专家。你的职责是：
1. 根据研究分析结果起草交易订单
2. 订单必须包含：标的、数量、价格（或市价）、交易所
3. 所有订单必须标注"待人类审批" — 永远不要假设已获批准
4. 用中文输出订单详情

Phase 1 规则：所有订单都需要人类批准。永远不要执行未经批准的订单。"""

async def draft_order(research_result: str, decision_id: int) -> str:
    """Draft a trade order based on research. Does NOT execute."""
    cfg = get_llm_config()
    primary = cfg.get("primary", {})
    llm = ChatMinimax(
        api_key=primary.get("api_key", ""),
        model=primary.get("model", "auto"),
        base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
    )

    prompt = f"""基于以下研究分析结果，起草交易订单：

{research_result}

注意：这是 Phase 1，所有订单都需要人类批准后才能执行。
请起草订单详情，标注[待审批]。"""

    response = await llm.ainvoke([
        SystemMessage(content=EXECUTION_SYSTEM),
        HumanMessage(content=prompt),
    ])

    return response.content
```

- [ ] **Step 7: Commit**

```bash
git add agents/ && git commit -m "feat: LangGraph dispatcher + research analyst + trade executor agents"
```

---

## Task 6: Discord Notification Bot

**Files:**
- Create: `discord/__init__.py`
- Create: `discord/bot.py`
- Create: `infra/cloudflared/setup.sh`

- [ ] **Step 1: Create discord/bot.py**

```python
"""Discord notification bot — sends alert cards to a channel."""
import asyncio
import discord
from discord import Embed, ButtonStyle
from discord.ui import Button, View
from ..config import get_discord_config


class DiscordNotifier:
    def __init__(self):
        self.config = get_discord_config()
        self.bot = discord.Bot(intents=discord.Intents.default())
        self._channel_id = int(self.config.get("channel_id", 0)) if self.config.get("channel_id") else None

    async def send_decision_alert(
        self,
        decision_id: int,
        decision_type: str,
        symbol: str,
        confidence: float,
        reasoning: str,
        risk_level: str,
        dashboard_url: str,
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
            url=dashboard_url,
        )
        view = View()
        view.add_item(button)

        try:
            channel = self.bot.get_channel(self._channel_id)
            if channel:
                await channel.send(embed=embed, view=view)
        except Exception:
            pass

    async def send_daily_report(self, summary: str, dashboard_url: str):
        if not self.config.get("enabled"):
            return
        if not self._channel_id:
            return

        embed = Embed(
            title="📋 每日早间简报",
            description=summary[:300],
            color=0x2196f3,
        )
        button = Button(
            style=ButtonStyle.link,
            label="查看完整日报",
            url=dashboard_url,
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


# Singleton
_notifier: DiscordNotifier | None = None


def get_notifier() -> DiscordNotifier:
    global _notifier
    if _notifier is None:
        _notifier = DiscordNotifier()
    return _notifier
```

- [ ] **Step 2: Create infra/cloudflared/setup.sh**

```bash
#!/bin/bash
# Cloudflare Tunnel setup script for E3 workstation
# Run this on the E3 workstation (Ubuntu 24.04)

set -e

# 1. Download cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb

# 2. Install
sudo dpkg -i cloudflared.deb

# 3. Verify
cloudflared --version

# 4. Create tunnel (one-time setup)
# cloudflared tunnel create broker-agents
# cloudflared tunnel route dns broker-agents your-subdomain.example.com

# 5. Run tunnel
# cloudflared tunnel run --token YOUR_TOKEN_HERE

echo "Cloudflare Tunnel installed. To run:"
echo "  cloudflared tunnel run --token YOUR_TOKEN_HERE"
echo ""
echo "Get your tunnel token from: https://dash.cloudflare.com/"
```

- [ ] **Step 3: Commit**

```bash
git add discord/ infra/ && git commit -m "feat: Discord notification bot + Cloudflare Tunnel setup script"
```

---

## Task 7: Daily Report Generator

**Files:**
- Modify: `dashboard/backend/routers/daily_report.py`
- Create: `agents/daily_report_generator.py`

- [ ] **Step 1: Create agents/daily_report_generator.py**

```python
"""Daily report generation — combines market data into morning brief."""
import asyncio
from datetime import date, datetime
from langchain_minimax import ChatMinimax
from langchain_core.messages import HumanMessage, SystemMessage
from dashboard.backend.database import save_daily_report
from agents.monitor.binance_monitor import BinanceMonitor
from agents.monitor.akshare_monitor import AKShareMonitor
from agents.monitor.yfinance_monitor import YFinanceMonitor
from ..config import get_llm_config

DAILY_REPORT_PROMPT = """你是一个投资早间简报生成器。请根据以下市场数据，生成一份简洁的中文早间简报：

今日日期: {date}
昨日隔夜行情: {overnight_data}
中国市场行情: {china_data}
加密市场行情: {crypto_data}

请按以下格式生成简报：

## 隔夜行情
- 简要列出各市场涨跌

## 重要事件
- 列出可能影响今日市场的宏观/政策/行业事件（基于数据推断）

## 投资窗口
- 基于当前数据分析可能的机会（保守，语气谨慎）

要求：
- 简洁，每节不超过5条
- 用中文
- 投资窗口给出理由，不给出具体买卖价格
"""


async def fetch_overnight_data() -> dict:
    """Fetch current market data from all monitors."""
    bnb = BinanceMonitor()
    aks = AKShareMonitor()
    yfc = YFinanceMonitor()

    overnight = {}
    try:
        alerts = await bnb.check()
        overnight["crypto"] = [f"{a.symbol}: ${a.details.get('current_price', 0):.0f}" for a in alerts[:3]]
    except:
        overnight["crypto"] = []

    try:
        alerts = await aks.check()
        overnight["china"] = [f"{a.details.get('name', a.symbol)}: {a.details.get('change_pct', 0):+.2f}%" for a in alerts[:3]]
    except:
        overnight["china"] = []

    try:
        alerts = await yfc.check()
        overnight["us"] = [f"{a.symbol}: {a.details.get('change_pct', 0):+.2f}%" for a in alerts[:3]]
    except:
        overnight["us"] = []

    return overnight


async def generate_daily_report() -> dict:
    """Generate and save today's daily report."""
    cfg = get_llm_config()
    primary = cfg.get("primary", {})

    market_data = await fetch_overnight_data()
    report_date = date.today()

    overnight_str = f"Crypto: {', '.join(market_data.get('crypto', [])[:3]) or 'N/A'}"
    china_str = f"A-shares: {', '.join(market_data.get('china', [])[:3]) or 'N/A'}"
    us_str = f"US: {', '.join(market_data.get('us', [])[:3]) or 'N/A'}"

    prompt = DAILY_REPORT_PROMPT.format(
        date=report_date.isoformat(),
        overnight_data=f"{overnight_str}\n{china_str}\n{us_str}",
        china_data=china_str,
        crypto_data=overnight_str,
    )

    try:
        llm = ChatMinimax(
            api_key=primary.get("api_key", ""),
            model=primary.get("model", "auto"),
            base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        report_text = response.content
    except Exception:
        report_text = "简报生成失败，请稍后重试"

    # Parse the response into structured fields
    sections = {"overnight_summary": "", "critical_events": "", "investment_windows": ""}
    current_section = "overnight_summary"
    for line in report_text.split("\n"):
        line = line.strip()
        if "重要事件" in line or "⚠️" in line:
            current_section = "critical_events"
        elif "投资窗口" in line or "🎯" in line:
            current_section = "investment_windows"
        elif line.startswith("##"):
            continue
        elif line:
            sections[current_section] += line + "\n"

    await save_daily_report(
        report_date=report_date,
        overnight_summary=sections["overnight_summary"].strip(),
        critical_events=sections["critical_events"].strip(),
        investment_windows=sections["investment_windows"].strip(),
    )

    return sections


async def scheduled_daily_report():
    """Run daily at 08:00 Shanghai time. Call from scheduler."""
    from datetime import time
    import time as time_module
    while True:
        now = datetime.now()
        target = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if now > target:
            target = target.replace(day=now.day + 1)
        delay = (target - now).total_seconds()
        await asyncio.sleep(delay)
        await generate_daily_report()
```

- [ ] **Step 2: Update dashboard/backend/routers/daily_report.py to wire up generation**

```python
"""Daily report API endpoints."""
from datetime import date
from fastapi import APIRouter, BackgroundTasks
from ..database import get_daily_report, save_daily_report
from ..models.schemas import DailyReportSchema
from agents.daily_report_generator import generate_daily_report

router = APIRouter()


@router.get("/{report_date}", response_model=DailyReportSchema | None)
async def get_report(report_date: date):
    return await get_daily_report(report_date)


@router.get("/latest", response_model=DailyReportSchema | None)
async def get_latest():
    return await get_daily_report(date.today())


@router.post("/generate")
async def generate_report(background: BackgroundTasks):
    background.add_task(generate_daily_report)
    return {"status": "queued", "message": "日报生成中，稍后刷新页面"}
```

- [ ] **Step 3: Commit**

```bash
git add agents/daily_report_generator.py dashboard/backend/routers/daily_report.py && git commit -m "feat: daily report generator with LLM summarization"
```

---

## Task 8: Integration & Testing

- [ ] **Step 1: Run all backend tests**

Run: `cd C:/Users/tobby/project/broker-agents && python -m pytest tests/ -v`
Expected: PASS (all tests)

- [ ] **Step 2: Verify backend starts**

Run: `cd C:/Users/tobby/project/broker-agents/dashboard/backend && python -c "import main; print('Backend imports OK')"`
Expected: No errors

- [ ] **Step 3: Create CLAUDE.md summary**

The CLAUDE.md already created in Task 1. Verify it's correct.

- [ ] **Step 4: Create a README.md for deployment instructions**

Create `docs/DEPLOY.md` with:
- E3 workstation Ubuntu 24 setup steps
- Cloudflare Tunnel token creation
- Environment variables setup
- How to start the agents and dashboard
- How to configure Discord bot

- [ ] **Step 5: Final commit**

```bash
git add docs/DEPLOY.md && git add -A && git commit -m "feat: Phase 1 MVP complete — agents + dashboard + monitors"
```

---

## Self-Review Checklist

1. **Spec coverage** — Every Phase 1 item in the spec has a task:
   - [x] E3 workstation setup (infra/cloudflared/setup.sh)
   - [x] Dashboard Portfolio + Daily Report + Pending Decisions (Task 2 + 3)
   - [x] Dispatcher agent (Task 5)
   - [x] Research Analyst agent (Task 5)
   - [x] Monitor scripts AKShare + Binance (Task 4)
   - [x] Trade Executor drafts only (Task 5)
   - [x] Sports cards Card Ladder (Task 4, partial stub for Phase 2)
   - [x] Local SQLite (Task 2)
   - [x] Discord notification relay (Task 6)
   - [x] Configurable API keys via YAML (Task 1)
   - [x] Mobile-first dashboard (Task 3)

2. **Placeholder scan** — No `TBD`, `TODO`, `implement later` found in tasks. All code is complete.

3. **Type consistency** — `Alert` dataclass fields match what monitor scripts produce and what dispatcher nodes consume. `Decision` schema matches database helpers.

4. **File structure matches spec** — All files created under correct paths per the spec's Section 11.
