"""Tests for decisions API."""
import pytest
import aiosqlite
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from dashboard.backend.main import app, init_db


@pytest.fixture(autouse=True)
async def clean_db():
    """Ensure clean database state before each test."""
    db_path = Path("data/broker_agents.db")
    db_path.unlink(missing_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Run init_db to create tables
    await init_db()
    yield
    db_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_pending_decisions_empty():
    """Test pending decisions endpoint with no data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/decisions/pending")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_resolve_decision_not_found():
    """Test resolving a non-existent decision - Phase 1 doesn't validate existence."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/decisions/99999/resolve", json={"approved": True})
    # Phase 1: SQLite UPDATE doesn't fail for non-existent ID
    assert response.status_code == 200
