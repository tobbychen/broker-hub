# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A self-hosted multi-agent investment assistant. Python scripts monitor markets cheaply; LLM agents (LangGraph + MiniMax) analyze and recommend; a human approves all trades. Frontend: Vue 3 mobile-first dashboard. Database: local SQLite. Network: Cloudflare Tunnel (no port forwarding).

---

## Commands

```bash
# Python environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Backend (FastAPI, port 8000)
cd dashboard/backend && uvicorn main:app --reload --port 8000

# Frontend (Vue 3 + Vite, port 5173, proxies /api to backend)
cd dashboard/frontend && npm install && npm run dev

# Monitor scheduler (runs all market monitors in a loop)
python -m agents.monitor.scheduler

# Daily report generator (one-shot)
python agents/daily_report_generator.py

# Run a single test
pytest tests/test_api_portfolio.py -v
pytest tests/test_monitor.py -v

# Run all tests
pytest
```

Three services must run simultaneously: backend, frontend, and monitor scheduler.

---

## Architecture

### Three-Service Model

```
dashboard/backend/  → FastAPI REST API (port 8000)
dashboard/frontend/ → Vue 3 SPA (port 5173, proxies /api to backend)
agents/            → Python processes (monitor scheduler, daily report)
```

The frontend never calls market APIs directly — all data flows through the backend API which reads from SQLite.

### Config Loading

`dashboard/backend/config.py` is the single source of truth for all configuration. It reads YAML files under `config/` and substitutes `${VAR}` and `${VAR:-default}` with environment variables.

`agents/config.py` re-exports from `dashboard.backend.config` via `sys.path.insert`. This means the agents package can import config without circular imports, but it creates a soft coupling — agents imports succeed as long as the project root is in sys.path.

LLM and market data API keys come from environment variables only — never hardcoded.

### LLM Abstraction

All LLM calls use `langchain_openai.ChatOpenAI` with MiniMax's OpenAI-compatible endpoint (`https://api.minimax.chat/v1`). The model name and API key are read from `config/api_providers.yaml` at runtime. Adding GLM or Kimi as fallback requires adding their base URLs to the YAML and updating the fallback chain in `agents/dispatcher/graph.py`.

### Dispatcher Agent (LangGraph)

`agents/dispatcher/graph.py` builds a `StateGraph` with three sequential nodes:
- `monitor_handler` — receives alerts, checks if relevant to portfolio via LLM
- `research_router` — marks alerts for research analysis
- `approval_router` — drafts decision cards and submits to SQLite

The graph is a singleton (`get_dispatcher()`). Tools are hot-loaded from markdown files in `agents/dispatcher/skills/`.

### Skill Hot-Loading

Skills (tools) are defined as markdown files with YAML frontmatter. The `SkillLoader` in `agents/dispatcher/skills/loader.py` hot-loads and monitors these files for changes.

```
agents/dispatcher/skills/
├── SKILL_FORMAT.md              # Format documentation
├── lookup_portfolio.md          # Portfolio query skill
├── get_live_price.md            # Market price skill
├── submit_decision.md           # Decision submission skill
└── parse_research_and_submit.md # Research parser skill
```

Edit a skill file and it will be reloaded on next use (mtime-based detection).

### Permission Reviewer

`agents/permission_reviewer/` reviews Claude Code permission requests against project policies defined in `config/permission_policies.yaml`.

- **ALLOW**: Standard development operations (Python, pytest, npm run, git status)
- **DENY**: Dangerous operations (rm -rf, force push, credentials files)
- **REVIEW**: Operations requiring human confirmation (package install, agent spawn)

### Spec Compliance Checker

Before any action, check if it aligns with the active spec scope. Specs are in `docs/superpowers/specs/`.

```python
from agents.spec_compliance import check_compliance

# Check if action is allowed
result = check_compliance(action="write", target="agents/dispatcher/skills/loader.py")
if not result.compliant:
    # Action requires spec amendment
    print(result.reason)
    print(result.suggestion)
```

**Workflow:**
1. Check specs in `docs/superpowers/specs/` for active feature
2. Activate relevant spec with `checker.activate_spec("skill-hot-loading")`
3. All actions must comply with spec scope
4. If outside scope → amend spec first, then proceed

**Spec Frontmatter Format:**
```yaml
---
name: feature-name
date: YYYY-MM-DD
version: 1.0.0
scope:
  files:
    read: ["path/**/*.py"]
    write: ["path/**/*.py"]
  commands:
    allowed: ["python", "pytest"]
    blocked: ["git push --force"]
---
```

### Two-Stage Monitoring

Stage 1 (monitor scripts, no LLM cost) runs continuously via `agents/monitor/scheduler.py`. Each monitor (`binance_monitor.py`, `akshare_monitor.py`, `yfinance_monitor.py`, `ebay_monitor.py`) inherits `BaseMonitor` and returns `Alert` dataclasses. A threshold check determines whether an alert fires.

Stage 2 (LLM) is only triggered when the Dispatcher receives an alert. The LLM decides whether the alert is relevant to the portfolio before invoking the Research Analyst.

### Database

SQLite via `aiosqlite`. The schema lives in `database/schema.sql` and runs automatically on backend startup (`init_db()` in `dashboard/backend/main.py` lifespan). The database file is at `data/broker_agents.db` (configured in `config/database.yaml`).

Key tables: `positions`, `decisions`, `trades`, `decision_chat`, `daily_reports`, `agent_logs`, `sports_cards`, `watchlist`.

---

## Key Patterns

- **Async throughout**: FastAPI, aiosqlite, httpx, LangChain async LLM calls. Never mix sync blocking calls in async contexts.
- **Agents use `sys.path` hacks**: `sys.path.insert(0, str(Path(__file__).parent.parent.parent))` to reach `dashboard.backend` from within `agents/`.
- **Dashboard config shared with agents**: `agents/config.py` re-exports from `dashboard/backend/config.py`. If you change the config structure, update both.
- **API keys via env vars only**: All provider credentials come from `${ENV_VAR}` substitutions in YAML, never from code.
- **Mobile-first Vue**: Dashboard uses Element Plus, dark theme, bottom navigation. Components live in `src/components/`, views in `src/views/`. API calls go through `src/api/client.ts`.

---

## File Locations

- `config/api_providers.yaml` — LLM + market data + notification (Telegram) credentials
- `config/agent_settings.yaml` — monitor thresholds, autonomy limits, decision timeouts
- `config/database.yaml` — SQLite path
- `agents/dispatcher/graph.py` — LangGraph dispatcher singleton
- `agents/dispatcher/tools.py` — async LangChain tools (lookup_portfolio, submit_decision, lookup_pending_decisions)
- `agents/monitor/scheduler.py` — main loop, imports all monitors
- `dashboard/backend/main.py` — FastAPI app, CORS, lifespan (init_db)
- `dashboard/backend/database.py` — all async SQLite helpers
- `database/schema.sql` — all table definitions
- `docs/superpowers/specs/` — design specifications
- `docs/superpowers/plans/` — implementation plans
