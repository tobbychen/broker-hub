"""Tests for portfolio API."""
import pytest
import aiosqlite
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from dashboard.backend.main import app


# Use in-memory database for tests
TEST_DB = "data/test_broker_agents.db"


@pytest.fixture(autouse=True)
async def clean_db():
    """Ensure clean database state before each test."""
    db_path = Path("data/broker_agents.db")
    db_path.unlink(missing_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    with open(schema_path, encoding="utf-8") as f:
        schema = f.read()
    for stmt in schema.split(";"):
        stmt = stmt.strip()
        if stmt:
            await db.execute(stmt)
    await db.commit()
    await db.close()
    yield
    # Cleanup after test
    db_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_portfolio_summary_empty():
    """Test portfolio summary endpoint with no data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/portfolio/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_value" in data
    assert "allocation" in data
    assert "by_class" in data
    assert data["total_value"] == 0


@pytest.mark.asyncio
async def test_portfolio_positions_empty():
    """Test positions endpoint with no data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/portfolio/positions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
