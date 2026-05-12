"""Pytest fixtures for broker-agents tests."""
import pytest
import asyncio
import aiosqlite
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()