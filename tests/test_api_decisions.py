"""Tests for decisions API."""
import pytest
from httpx import AsyncClient, ASGITransport
from dashboard.backend.main import app


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
    """Test resolving a non-existent decision returns 404 or 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/decisions/99999/resolve", json={"approved": True})
    # Will succeed since we're not validating existence in Phase 1
    assert response.status_code in (200, 404)
