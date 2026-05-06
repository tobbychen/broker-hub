"""Pytest fixtures for broker-agents tests."""
import pytest
import asyncio
import aiosqlite
from pathlib import Path
import tempfile

TEST_DB = Path(tempfile.gettempdir()) / "test_broker_agents.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    db = await aiosqlite.connect(str(TEST_DB))
    db.row_factory = aiosqlite.Row
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    with open(schema_path, encoding="utf-8") as f:
        schema = f.read()
    for stmt in schema.split(";"):
        stmt = stmt.strip()
        if stmt:
            await db.execute(stmt)
    await db.commit()
    yield db
    await db.close()
    TEST_DB.unlink(missing_ok=True)