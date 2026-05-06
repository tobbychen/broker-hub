"""Tests for portfolio API."""
import pytest
from httpx import AsyncClient, ASGITransport
from dashboard.backend.main import app


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
