"""Config loader — reuses dashboard config module."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.backend.config import (
    get_llm_config,
    get_market_data_config,
    get_agent_settings,
    get_discord_config,
    get_database_config,
    get_notification_config,
)

__all__ = [
    "get_llm_config",
    "get_market_data_config",
    "get_agent_settings",
    "get_discord_config",
    "get_database_config",
    "get_notification_config",
]
