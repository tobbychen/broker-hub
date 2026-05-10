"""LLM chain utility with fallback support."""
import logging
import asyncio
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from openai import APIError

logger = logging.getLogger(__name__)


class FallbackChatOpenAI:
    """ChatOpenAI wrapper that retries with fallback providers on failure."""

    def __init__(self, providers: list[dict]):
        """
        providers: list of {"name": str, "api_key": str, "model": str,
                             "base_url": str, "temperature": float}
        Ordered by priority (first = primary).
        """
        self.providers = providers
        if not providers:
            raise ValueError("At least one LLM provider must be configured")

    async def ainvoke(self, messages: list[BaseMessage]) -> BaseMessage:
        errors = []
        for i, cfg in enumerate(self.providers):
            try:
                llm = ChatOpenAI(
                    api_key=cfg.get("api_key", ""),
                    model=cfg.get("model", "auto"),
                    base_url=cfg.get("base_url", "https://api.minimax.chat/v1"),
                    temperature=cfg.get("temperature", 0.3),
                    request_timeout=cfg.get("timeout", 60),
                )
                return await llm.ainvoke(messages)
            except APIError as e:
                logger.warning(f"[llm] {cfg.get('name', cfg.get('provider'))} API error: {e}")
                errors.append(f"{cfg.get('name', cfg.get('provider'))}: {e}")
                continue
            except asyncio.TimeoutError as e:
                logger.warning(f"[llm] {cfg.get('name', cfg.get('provider'))} timeout")
                errors.append(f"{cfg.get('name', cfg.get('provider'))}: timeout")
                continue
            except Exception as e:
                logger.warning(f"[llm] {cfg.get('name', cfg.get('provider'))} unexpected error: {e}")
                errors.append(f"{cfg.get('name', cfg.get('provider'))}: {e}")
                continue

        raise RuntimeError(f"All LLM providers failed: {errors}")

    def invoke(self, messages: list[BaseMessage]) -> BaseMessage:
        """Synchronous wrapper."""
        return asyncio.get_event_loop().run_until_complete(self.ainvoke(messages))


def create_llm_chain() -> FallbackChatOpenAI:
    """Build an LLM chain from config using all available providers."""
    from agents.config import get_llm_config

    cfg = get_llm_config()
    primary = cfg.get("primary", {})
    fallbacks = cfg.get("fallback", [])

    providers = []

    if primary.get("api_key"):
        providers.append({
            "name": primary.get("provider", "primary"),
            "api_key": primary["api_key"],
            "model": primary.get("model", "auto"),
            "base_url": primary.get("base_url", "https://api.minimax.chat/v1"),
            "temperature": primary.get("temperature", 0.3),
        })

    for fb in fallbacks:
        if fb.get("api_key"):
            providers.append({
                "name": fb.get("provider", "fallback"),
                "api_key": fb["api_key"],
                "model": fb.get("model", "auto"),
                "base_url": fb.get("base_url", ""),
                "temperature": float(fb.get("temperature", 0.3)),
            })

    return FallbackChatOpenAI(providers)


def get_single_llm() -> ChatOpenAI:
    """Get a single ChatOpenAI instance (primary only, no fallback)."""
    from agents.config import get_llm_config

    cfg = get_llm_config()
    primary = cfg.get("primary", {})

    return ChatOpenAI(
        api_key=primary.get("api_key", ""),
        model=primary.get("model", "auto"),
        base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
        temperature=0.3,
    )
