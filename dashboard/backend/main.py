"""FastAPI application entry point."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .routers import portfolio, decisions, chat, daily_report, agent_status, watchlist


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Start Telegram polling as a background task
    polling_task = None
    from .config import get_notification_config
    cfg = get_notification_config()
    if cfg.get("enabled") and cfg.get("bot_token"):
        try:
            from telegram.receiver import run_polling_loop
            from telegram.chat_handler import handle_telegram_message
            from telegram.bot import get_notifier

            notifier = get_notifier()
            if notifier.enabled and notifier.token:
                polling_task = asyncio.create_task(
                    run_polling_loop(
                        notifier.token,
                        on_message=handle_telegram_message,
                        interval=1.0,
                    )
                )
                asyncio.get_event_loop().call_later(
                    5, lambda: asyncio.create_task(_log_telegram_started())
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to start Telegram polling: {e}")

    async def _log_telegram_started():
        import logging
        logging.getLogger(__name__).info("Telegram polling loop started")

    if polling_task:
        app.state.telegram_polling_task = polling_task

    yield

    # Shutdown
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except Exception:
            pass


app = FastAPI(
    title="Broker Agents Dashboard",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(decisions.router, prefix="/api/decisions", tags=["decisions"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(daily_report.router, prefix="/api/daily-report", tags=["daily-report"])
app.include_router(agent_status.router, prefix="/api/agent-status", tags=["agent-status"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
