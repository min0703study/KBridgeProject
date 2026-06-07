from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from pydantic import BaseModel


LOG_PATH = Path(__file__).resolve().parents[4] / "logs" / "roleplay_agent.log"
LOGGER_NAME = "kbridge.roleplay_agent"
MAX_LOG_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5


def log_node_completed(node_name: str, payload: dict[str, Any]) -> None:
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "node_completed",
        "node": node_name,
        "payload": _to_jsonable(payload),
    }
    _get_logger().info(json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str))


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    return value


def _get_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
