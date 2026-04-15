from __future__ import annotations

from typing import Any, TypedDict


class LogTurnPayload(TypedDict):
    session_name: str
    turn: int
    query: str
    action: str
    style_modifier: str
    intent_type: str
    complexity: float
    ambiguity: float
    threshold: float
    arousal: float
    risk_aversion: float
    resolution: float
    topic_familiarity: float
    confidence: float
    low_confidence: float
    over_beneficial: float
    over_safety: float
    over_honesty: float
    hallucinate: float
    redundant: float
    rabbit_hole: float
    premature: float
    homeo_mode: str
    homeo_trigger_count: int
    homeo_trigger_keys: list[str]
    context_memory_enabled: bool
    context_window_turns: int
    score_top3_text: str
    answer: str
    context: dict[str, Any]
    decision: dict[str, Any]
    pre_update: dict[str, Any]
    post_update: dict[str, Any]
