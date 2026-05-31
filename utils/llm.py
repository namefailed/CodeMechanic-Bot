"""
Shared helpers for talking to the local Ollama server.

Model selection and the endpoint are driven by config.yaml so the bot has a
single source of truth instead of model names hardcoded across agents.
"""

import os
import yaml
import logging

logger = logging.getLogger(__name__)

# Sensible defaults if config.yaml is missing or incomplete.
# NOTE: there is no "gemma4" model; the local default is Gemma 3 4B.
DEFAULT_ENDPOINT = "http://localhost:11434"
DEFAULT_MODELS = ["gemma3:4b", "llama3", "mistral"]


def get_ollama_config(config_path: str = "config.yaml"):
    """
    Returns (endpoint, [models]) from config.yaml.

    The primary model is tried first, followed by any configured fallbacks.
    Falls back to DEFAULT_ENDPOINT / DEFAULT_MODELS when config is absent.
    """
    endpoint = DEFAULT_ENDPOINT
    models = []
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                model_cfg = (yaml.safe_load(f) or {}).get("model", {}) or {}
            endpoint = model_cfg.get("endpoint") or DEFAULT_ENDPOINT
            if model_cfg.get("primary"):
                models.append(model_cfg["primary"])
            models.extend(model_cfg.get("fallbacks", []) or [])
    except Exception as e:
        logger.warning(f"get_ollama_config: failed to read {config_path}: {e}")

    # De-duplicate while preserving order; fall back to defaults if empty.
    seen = set()
    models = [m for m in models if m and not (m in seen or seen.add(m))]
    return endpoint, (models or DEFAULT_MODELS)
