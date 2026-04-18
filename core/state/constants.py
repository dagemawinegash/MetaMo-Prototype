from __future__ import annotations

from utils import clamp_to_unit_interval


# Constants / baselines
ACTION_BLOCKED_SCORE = -1e9
ACTION_ACTIVE_FLOOR = -1e8


def _blend(prev: float, target: float, alpha: float) -> float:
    return clamp_to_unit_interval((1.0 - alpha) * prev + alpha * target)


def _coerce_verify_request(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False

