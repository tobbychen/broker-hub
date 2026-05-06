"""Config loader — reads YAML files and environment variables."""
import os
from pathlib import Path
from typing import Any
import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"


def _env_substitute(obj: Any) -> Any:
    """Recursively substitute ${VAR} with os.environ[VAR]."""
    if isinstance(obj, dict):
        return {k: _env_substitute(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_env_substitute(v) for v in obj]
    elif isinstance(obj, str):
        if obj.startswith("${") and obj.endswith("}"):
            var = obj[2:-1]
            default = None
            if ":-" in var:
                var, default = var.split(":-", 1)
            return os.environ.get(var, default or "")
        return obj
    return obj


def load_config(name: str) -> dict:
    path = CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return _env_substitute(data or {})


def get_llm_config() -> dict:
    return load_config("api_providers").get("llm", {})


def get_market_data_config() -> dict:
    return load_config("api_providers").get("market_data", {})


def get_agent_settings() -> dict:
    return load_config("agent_settings").get("agents", {})


def get_database_config() -> dict:
    return load_config("database")


def get_discord_config() -> dict:
    return load_config("api_providers").get("discord", {})
