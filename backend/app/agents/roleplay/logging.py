from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


def log_node_completed(node_name: str, payload: dict[str, Any]) -> None:
    print(f"[RoleplayAgent] node={node_name} completed")
    print(json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2, default=str))


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
