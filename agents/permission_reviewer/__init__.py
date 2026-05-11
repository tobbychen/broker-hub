"""Permission reviewer for Claude Code.

Provides both rule-based and LLM-based permission review.

Usage:
    # Rule-based (fast, no LLM cost)
    from agents.permission_reviewer import review
    result = review("Bash", command="rm -rf /tmp")

    # LLM-based (uses project context via LLM)
    from agents.permission_reviewer import review_with_llm
    result = await review_with_llm("Bash", command="rm -rf /tmp")
"""
import asyncio
from .reviewer import (
    PermissionDecision,
    PermissionReviewer,
    get_reviewer,
    review,
)
from .agent import (
    PermissionReviewAgent,
    get_permission_agent,
    review_permission as review_with_llm,
)

__all__ = [
    "PermissionDecision",
    "PermissionReviewer",
    "get_reviewer",
    "review",
    "PermissionReviewAgent",
    "get_permission_agent",
    "review_with_llm",
]


async def review_permission_async(**kwargs) -> dict:
    """Async wrapper for LLM-based review."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, review_with_llm, **kwargs)