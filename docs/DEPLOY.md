# Broker Agents — Deployment Guide

## Prerequisites

- E3-1280 V2 workstation with Ubuntu 24.04 LTS installed
- Existing Python 3.12+ environment
- Tailscale account (free, from tailscale.com) — for remote access
- Telegram bot token (free, from @BotFather)
- eBay Developer account (free, from developer.ebay.com) — for sports card price monitoring
- MiniMax API key (already purchased)
- VPN connection (for accessing international APIs from Beijing)

---

## Step 1: Install Dependencies

On your E3 workstation:

```bash
# Clone the project
git clone <your-repo-url> broker-agents
cd broker-agents

# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# .env
MINIMAX_API_KEY=your_minimax_api_key_here
MINIMAX_MODEL=auto
MINIMAX_BASE_URL=https://api.minimax.chat/v1

# Optional — for Phase 2
GLM_API_KEY=your_glm_key_here
KIMI_API_KEY=your_kimi_key_here
BINANCE_API_KEY=your_binance_key_here
BINANCE_SECRET=your_binance_secret_here

# eBay API (free, from developer.ebay.com)
EBAY_API_KEY=your_ebay_oauth_token_here

# Telegram notification bot (free, from @BotFather)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

---

## Step 3: Tailscale Setup (Remote Access)

```bash
cd infra/tailscale
chmod +x setup.sh
./setup.sh
```

Follow the on-screen instructions:
1. Sign up at tailscale.com with your email (free, no card needed)
2. Run `sudo tailscale up --operator=$USER` on your E3 workstation
3. Authorize the device in your Tailscale admin console
4. Install Tailscale app on your phone and laptop

**Access the dashboard:**
- From Tailscale app: `http://broker-agents.<your-tailnet>.ts.net:8000`
- Or via IP: `http://<tailscale-ip>:8000`

---

## Step 4: Initialize Database

```bash
# The database is created automatically on first run
# Or initialize manually:
python -c "import asyncio; from dashboard.backend.database import init_db; asyncio.run(init_db())"
```

---

## Step 5: Start the Dashboard Backend

```bash
# In one terminal
cd broker-agents
source .venv/bin/activate
cd dashboard/backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Step 6: Start the Frontend

```bash
# In another terminal
cd broker-agents/dashboard/frontend
npm install
npm run dev
```

Access the dashboard at `http://localhost:5173` (local) or via Cloudflare Tunnel URL.

---

## Step 7: Start the Monitor Scheduler

```bash
# In a third terminal (runs in background in production)
cd broker-agents
source .venv/bin/activate
python -m agents.monitor.scheduler
```

---

## Step 8: Telegram Bot Setup

1. Open Telegram → search for **@BotFather**
2. Send `/newbot` → follow prompts → copy the bot token
3. Search for your new bot by its username → click **Start**
4. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` to find your **chat_id**
5. Add both to your `.env` file

---

## Running Everything on Boot (systemd)

Create `/etc/systemd/system/broker-agents-dashboard.service`:

```ini
[Unit]
Description=Broker Agents Dashboard
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/broker-agents
ExecStart=/home/your_username/broker-agents/.venv/bin/uvicorn dashboard.backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable broker-agents-dashboard
sudo systemctl start broker-agents-dashboard
```

---

## Project Structure

```
broker-agents/
├── agents/                  # Agent code
│   ├── monitor/             # Market monitors (AKShare, Binance, Yahoo, eBay)
│   ├── dispatcher/          # LangGraph dispatcher agent
│   ├── research_analyst/     # Research agent
│   └── trade_executor/      # Trade executor agent
├── dashboard/
│   ├── backend/             # FastAPI backend
│   │   ├── main.py          # App entry point
│   │   ├── config.py         # Config loader
│   │   ├── database.py       # SQLite helpers
│   │   ├── models/           # Pydantic schemas
│   │   └── routers/          # API endpoints
│   └── frontend/            # Vue 3 frontend
├── telegram/                  # Telegram notification bot
├── infra/                    # Infrastructure (Tailscale)
├── config/                   # YAML config files
├── database/                 # SQL schema
└── tests/                    # Tests
```

---

## Troubleshooting

**Dashboard not loading:**
- Check backend is running: `curl http://localhost:8000/api/portfolio/summary`
- Check Tailscale is connected: `tailscale status`

**No market data:**
- AKShare may fail outside China — ensure VPN is connected
- Binance API requires valid API keys

**LLM errors:**
- Verify MINIMAX_API_KEY is set in `.env`
- Check API quota at MiniMax dashboard

**Database errors:**
- Ensure `data/` directory exists and is writable
- Check disk space on E3 workstation
