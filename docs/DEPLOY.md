# Broker Agents — Deployment Guide

## Prerequisites

- E3-1280 V2 workstation with Ubuntu 24.04 LTS installed
- Existing Python 3.12+ environment
- Cloudflare account (free tier)
- Discord bot token (free, from Discord Developer Portal)
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
CARDLADDER_API_KEY=your_card_ladder_key_here

# Discord bot
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
```

---

## Step 3: Cloudflare Tunnel Setup

```bash
cd infra/cloudflared
chmod +x setup.sh
./setup.sh
```

Follow the on-screen instructions to:
1. Install cloudflared
2. Create a tunnel at dash.cloudflare.com
3. Get your tunnel token

Run the tunnel:
```bash
cloudflared tunnel run --token YOUR_TUNNEL_TOKEN_HERE
```

The dashboard will be accessible at `https://your-tunnel-name.trycloudflare.com`

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

## Step 8: Discord Bot Setup

1. Go to https://discord.com/developers/applications
2. Create a new application → Bot
3. Enable Message Content Intent
4. Copy the bot token to your `.env` file
5. Invite the bot to your server with these permissions:
   - Send Messages
   - Embed Links
   - Use Slash Commands

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
│   ├── monitor/             # Market monitors (AKShare, Binance, Yahoo, Card Ladder)
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
├── discord/                  # Discord notification bot
├── infra/                    # Infrastructure (Cloudflare Tunnel)
├── config/                   # YAML config files
├── database/                 # SQL schema
└── tests/                    # Tests
```

---

## Troubleshooting

**Dashboard not loading:**
- Check backend is running: `curl http://localhost:8000/api/portfolio/summary`
- Check Cloudflare Tunnel is connected: `cloudflared tunnel --version`

**No market data:**
- AKShare may fail outside China — ensure VPN is connected
- Binance API requires valid API keys

**LLM errors:**
- Verify MINIMAX_API_KEY is set in `.env`
- Check API quota at MiniMax dashboard

**Database errors:**
- Ensure `data/` directory exists and is writable
- Check disk space on E3 workstation
