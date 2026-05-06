# Broker Agents Investment Superpower System — Design Spec
**Date:** 2026-05-06
**Version:** 1.0

---

## 1. Overview

A self-hosted multi-agent system that monitors global markets (stocks, crypto, forex, options, sports cards) and assists human investment decision-making. Runs on a home workstation (E3-1280 V2) in Beijing — no static IP, no GPU, no data leaves local infrastructure.

**Core principle:** Agents do research, analysis, and drafting. Humans make decisions. Small positions (< ¥10K) can execute autonomously after Phase 2.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         HUMAN (You)                           │
│  Approves trades, asks questions, reviews daily reports        │
└──────────────────────────┬───────────────────────────────────┘
                           │ Chat / Click
                           ▼
┌──────────────────────────────────────────────────────────────┐
│               WEB DASHBOARD (FastAPI + Vue 3)                │
│  Portfolio Overview | Daily Report | Pending Decisions        │
│  Trade History | Agent Status | Sports Cards                  │
│  ─────────────────────────────────────────────────────────── │
│  All data stored in local SQLite — no third-party access      │
│  Runs on E3 workstation, exposed via Cloudflare Tunnel         │
└──────────────────────────┬───────────────────────────────────┘
                           ▲
         ┌─────────────────┴──────────────────┐
         │        DISCORD (Notification Only)  │
         │  Agent pushes alert card → click    │
         │  opens local dashboard to review     │
         └──────────────────────────────────────┘
                           ▲
         ┌─────────────────┴──────────────────┐
         │   DISPATCHER (LangGraph Agent)       │
         │  Orchestrates all workers            │
         │  Maintains portfolio state            │
         │  Routes to human for approvals        │
         │  Multi-provider LLM with fallback    │
         └──────────────────────────────────────┘
              │    │    │    │    │
     ┌────────┘    │    │    │    └────────┐
     ▼             ▼    ▼    ▼             ▼
  ┌────────┐  ┌─────────┐  ┌───────┐  ┌──────────┐
  │ Monitor│  │ Research │  │ Risk  │  │ Executor │
  │(Script)│  │ (Agent)  │  │(Rule) │  │ (Agent)  │
  └────────┘  └─────────┘  └───────┘  └──────────┘
     │             │            │           │
     └─────────────┴────────────┴───────────┘
                        │
              ┌─────────┴─────────┐
              │   Local SQLite DB  │
              │  Positions, logs,  │
              │  decisions, config  │
              └────────────────────┘
```

---

## 3. Agent Roles

| Agent | Type | Responsibility | LLM Needed |
|-------|------|---------------|------------|
| **Monitor** | Python script | Watches AKShare, Binance, Yahoo, Card Ladder. Detects price anomalies, volume spikes, arbitrage windows | No |
| **Research Analyst** | LLM Agent | Investigates flagged opportunities: news, macro data, fundamentals, historical patterns | Yes |
| **Risk Manager** | Rule engine | Pre-trade checks: position limits, volatility exposure, correlation, asset-specific rules | No |
| **Trade Executor** | LLM Agent | Drafts orders for IBKR / domestic broker / Binance. Sends to human for approval before executing | Yes |
| **Portfolio Tracker** | Python script | Maintains positions, P&L, allocation. Sends periodic summaries | No |
| **Dispatcher** | LLM Agent (LangGraph) | Orchestrates everything. Routes tasks, maintains state, calls human for approvals, manages LLM fallback | Yes |

### Two-Stage Monitoring Filter
```
Stage 1: Monitor Script (fast, always-on, no LLM cost)
  - Price change > 3% in 5min
  - Volume spike > 2x average
  - Arbitrage window detected
  - Card price anomaly (Card Ladder)

Stage 2: Dispatcher (context check, no LLM)
  - Is asset in portfolio or watchlist?
  - Does it match our strategy?
  - If yes → route to Research Analyst
  - If no → log and discard
```
LLM Research Analyst is only invoked after Dispatcher approves — keeping API costs low.

### Human-Only Decisions (Never Delegated)
- New asset class entry
- Changing investment strategy or risk tolerance
- Emergency liquidation during market crisis
- Position size above autonomous threshold
- Adding/removing broker connections

### Tiered Autonomy
- Small positions (< ¥10K, configurable) → agent can execute autonomously after internal approval
- Large positions → always routes to human for confirmation

---

## 4. Asset Classes

| Class | Data Source | Access Method |
|-------|-------------|---------------|
| A-shares (China) | AKShare | Python lib, free |
| US/international stocks | Yahoo Finance, IBKR | yfinance + ib-insync |
| Crypto | Binance API, CoinGecko | Python-binance + Coingecko API |
| Forex | IBKR | ib-insync |
| Options | IBKR + domestic broker (QMT/XTP) | ib-insync + 证券公司 API |
| Sports cards | Card Ladder API, 327cards | REST API |

---

## 5. LLM Configuration

### Provider Setup (All configurable via config/api_providers.yaml)
```yaml
llm:
  primary:
    provider: minimax
    api_key: ${MINIMAX_API_KEY}
    model: minimax-2026-05-06
    base_url: https://api.minimax.chat/v1

  fallback:
    - provider: glm
      api_key: ${GLM_API_KEY}
      model: glm-4
    - provider: kimi
      api_key: ${KIMI_API_KEY}
      model: moonshot-v1-128k

# All keys from environment variables — no hardcoding
```

### Provider Priority
1. **MiniMax** — primary (coding plan already purchased)
2. **GLM-4** — Chinese market understanding, news analysis
3. **Kimi** — English reasoning, US market analysis

### Agent-Specific Usage
| Agent | LLM Calls | Context Window |
|-------|-----------|----------------|
| Dispatcher | High | 128K |
| Research Analyst | Medium (only on flagged opportunities) | 128K |
| Trade Executor | Low (drafting only) | 32K |
| Monitor / Risk / Tracker | None | N/A |

### Estimated Monthly Cost
- MiniMax: ~¥15-25 (moderate usage)
- GLM fallback: ~¥10-15
- Kimi fallback: ~¥5-10
- **Total: ~¥30-50/month**

---

## 6. Web Dashboard

### Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** Vue 3 + Vite
- **Database:** SQLite (local, on E3 workstation)
- **Styling:** Element Plus (Vue 3)

### Dashboard Views

| View | Content | Mobile Priority |
|------|---------|-----------------|
| **Portfolio Overview** | All positions across asset classes. P&L per asset, allocation pie chart, total value | Medium |
| **Daily Report** | Morning summary: overnight market moves, critical events globally, investment windows identified, portfolio risk metrics | High (read on commute) |
| **Pending Decisions** | Agent recommendations queue — each card shows: asset, action, reasoning, risk level, timeout countdown | Critical (primary mobile action) |
| **Trade History** | All executed trades: agent rationale, human approval/rejection, outcome | Low (rarely needed on mobile) |
| **Interactive Chat** | Per-decision Q&A — ask follow-up questions, agent responds with analysis, then approve/reject | High |
| **Agent Status** | Worker health: Monitor running, last check times, errors, LLM usage | Low (debug only) |
| **Sports Cards** | Graded card prices, portfolio value, market trends | Medium |

### Mobile-First Design Specifications

**Layout approach:** Single-column stack, bottom navigation bar
- Top bar: current portfolio value (one number, large), tap for details
- Bottom nav: Home | Decisions | Chat | Portfolio | Settings (5 icons, always visible)

**Pending Decisions view (mobile):**
```
┌────────────────────────────┐
│ ● BTC Arbitrage Detected  │
│ Buy 0.01 BTC              │
│ Binance vs AKShare gap    │
│ Confidence: 82%          │
│ ━━━━━━━━━━░░░░ 4:32 left  │
│                            │
│ [Ask More] [Reject] [✓]   │
└────────────────────────────┘
```
- One card fills screen width
- Swipe left/right between cards
- Approve button is green, large thumb-target size (48px+)
- Reject button is red, smaller
- "Ask More" opens chat inline — no page navigation

**Portfolio view (mobile):**
```
┌────────────────────────────┐
│ Total: ¥127,432 (+2.3%)  │
├────────────────────────────┤
│ [Pie chart: asset alloc]  │
├────────────────────────────┤
│ BTC    ¥45,000  +3.1%    │
│ A-share ¥32,000  -0.8%   │
│ ETF    ¥28,000   +1.2%   │
│ Cards  ¥22,432   +4.5%   │
│ ...                       │
└────────────────────────────┘
```
- Tap any row → expand to show individual positions
- Pull down to refresh
- Total value always visible at top (sticky)

**Daily Report view (mobile):**
```
┌────────────────────────────┐
│ 📊 Morning Brief           │
│ May 6, 2026  08:30        │
├────────────────────────────┤
│ Overnight:                │
│ • BTC +2.1%, ETH +1.8%   │
│ • S&P500 flat, Nasdaq+0.4│
│ • 日经225 -0.3%          │
├────────────────────────────┤
│ ⚠️ Critical Events:       │
│ • 美联储6月降息预期↑      │
│ • 比特币 ETF净流入创新高  │
├────────────────────────────┤
│ 🎯 Investment Windows:     │
│ • BTC维持强势, 可考虑加仓  │
│ • 上证300触及支撑位       │
│ • 球星卡: Pokemon 151↑    │
└────────────────────────────┘
```
- Formatted for quick scan, 30 seconds to read
- Expandable sections for details
- One-tap share to WeChat/Friends

**Interactive Chat (mobile):**
- Chat panel slides up from bottom as overlay
- Does NOT navigate away from current decision card
- Voice input button (phone keyboard mic)
- AI response streams in real-time (typing indicator)
- Approve/reject buttons persist at bottom of chat

**PWA capability:**
- Dashboard served as Progressive Web App
- Works offline for viewing cached data (positions, history)
- Push notifications via service worker
- Add to home screen icon
- No app store needed — direct URL install

**Responsive breakpoints:**
- < 640px: Single column, bottom nav, large touch targets
- 640-1024px: Two-column where useful (portfolio list + chart)
- > 1024px: Full dashboard, side navigation

**Performance targets:**
- Dashboard loads in < 2s on 4G connection
- AI chat response starts streaming within 1s
- Smooth 60fps scrolling on mobile

### Design Principles
- Mobile-first — designed for phone, extended for desktop
- Dark mode by default (easier on eyes for daily monitoring)
- All sensitive data stored in local SQLite — never leaves homelab
- Minimal taps to approve/reject (max 2 taps)

### Notification Flow
```
Agent recommends → Dashboard notification + Discord alert card
                         ↓
              You click → Dashboard opens
                         ↓
              Interactive chat for Q&A
                         ↓
              Approve / Reject
```

---

## 7. Homelab Setup

### Hardware (already owned)
- Intel Xeon E3-1280 V2 (4C/8T) — more than sufficient
- 16GB DDR3 RAM — sufficient
- Existing drives — add SSD for SQLite speed if needed
- Xiaomi router (default settings, no port forwarding needed)

### Software Stack
```
Ubuntu 24.04 LTS
├── Cloudflare Tunnel (cloudflared) — exposes dashboard, no port forwarding
├── Python 3.12+ — all agent code
├── LangGraph + LangChain — agent framework
├── FastAPI — dashboard backend
├── Vue 3 + Vite — dashboard frontend
├── SQLite — local database
├── AKShare — A-share market data
├── python-binance — Binance API
├── yfinance — Yahoo Finance
├── ib-insync — IBKR API (Phase 2)
└── Docker (optional) — isolated services
```

### No GPU needed — cloud LLM APIs handle all intelligence.

### Cloudflare Tunnel Setup
```bash
# On E3 workstation
curl -L https://github.com/cloudflare/cloudflared/releases/download/2024.1.5/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
./cloudflared tunnel run --token YOUR_TOKEN_HERE
```
- No port forwarding on Xiaomi router
- Router only needs: outbound internet access (default)
- Dashboard accessible via `*.trycloudflare.com` URL

### Ugreen NAS (DXP 4800)
- Currently runs many Docker apps
- NOT used for agent hosting (keep clean)
- Used as backup storage if needed

### Ongoing Cost
- Electricity: ~¥10-20/month
- Cloudflare Tunnel: free
- LLM APIs: ~¥30-50/month
- **Total: ~¥40-70/month**

---

## 8. Implementation Phases

### Phase 1 — MVP (This sprint)
- E3 workstation setup (Ubuntu 24 + cloudflared)
- Dashboard (Portfolio + Daily Report + Pending Decisions views)
- Dispatcher agent (LangGraph, MiniMax primary)
- Research Analyst agent
- Monitor script (AKShare + Binance)
- Trade Executor (drafts only, all human-approved)
- Sports cards: Card Ladder integration
- Local SQLite database for all records
- Discord notification relay

### Phase 2 — Enhanced
- Interactive chat on dashboard
- IBKR integration (stocks, options, forex)
- Domestic broker integration (QMT/XTP for A-shares)
- Sports card price alerting
- Small-position autonomous execution (< ¥10K)
- Tailscale as backup VPN access

### Phase 3 — Advanced
- Portfolio analytics (Sharpe ratio, correlation matrix, drawdown charts)
- Multi-broker unified view
- Advanced sports card market analysis
- Autonomous tier expansion (configurable thresholds)

---

## 9. Configuration Management

All configuration via YAML files — no hardcoded values.

```yaml
# config/api_providers.yaml
llm:
  primary:
    provider: minimax
    api_key: ${MINIMAX_API_KEY}
    model: minimax-2026-05-06
    base_url: https://api.minimax.chat/v1
  fallback:
    - provider: glm
      api_key: ${GLM_API_KEY}
      model: glm-4

market_data:
  akshare: enabled
  binance:
    api_key: ${BINANCE_API_KEY}
    secret: ${BINANCE_SECRET}
  yfinance: enabled
  card_ladder:
    api_key: ${CARDLADDER_API_KEY}

# config/agent_settings.yaml
agents:
  monitor:
    price_change_threshold: 0.03  # 3%
    volume_spike_multiplier: 2.0
  autonomy:
    small_position_limit: 10000  # ¥10K
```

All API keys from environment variables — swap providers anytime without code changes.

---

## 10. Network & Security

### Cloudflare Tunnel
- No static IP required
- No port forwarding on router
- TLS-encrypted end-to-end
- Optional: password protection + allowed email list

### Data Sovereignty
- All trading records stored locally on E3 workstation
- SQLite database never leaves homelab
- Dashboard accessible only to you (Cloudflare access list)

### Backup
- Tailscale as backup VPN for SSH/admin access
- NAS can be used for database backup

---

## 11. File Structure

```
broker-agents/
├── config/
│   ├── api_providers.yaml
│   ├── agent_settings.yaml
│   └── database.yaml
├── agents/
│   ├── dispatcher/
│   ├── research_analyst/
│   ├── trade_executor/
│   └── monitor/
│       ├── akshare_monitor.py
│       ├── binance_monitor.py
│       └── card_ladder_monitor.py
├── dashboard/
│   ├── backend/
│   │   ├── main.py
│   │   ├── routers/
│   │   └── models/
│   └── frontend/
│       ├── src/
│       └── vite.config.ts
├── database/
│   └── schema.sql
├── infra/
│   └── cloudflared/
├── tests/
├── docs/
│   └── superpowers/
│       └── specs/
├── CLAUDE.md
└── requirements.txt
```