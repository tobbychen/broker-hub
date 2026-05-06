"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .routers import portfolio, decisions, chat, daily_report, agent_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


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
