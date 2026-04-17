from __future__ import annotations

from typing import TypedDict


class ScoringInputs(TypedDict):
    cx: float
    ambiguity: float
    ux: float
    u: float
    res: float
    threshold: float
    threshold_signal: float
    familiarity: float
    familiarity_signal: float
    failure_wariness: float
    failure_signal: float
    securing: float
    approach: float
    arousal: float
    risk_aversion: float
    error_tolerance: float
    creativity: float
    valence: float
    low_confidence: float
    answerability: float
    needs_external_evidence: float
    needs_task_plan: float
    needs_multi_source_integration: float
    reflective_intent: float
    verify_request: bool
    anti_hall: float
    anti_redundant: float
    anti_rabbit_hole: float
    anti_premature: float
    coherence: float
    originality: float
    social: float
    help_short: float
    help_long: float
    over_beneficial: float
    over_safety: float
    over_honesty: float
    knowledge: float
    novelty: float
    success_breakthrough: float
    reflective_think_bonus: float
    reflective_search_penalty: float
    weights: dict


class RoutingInputs(TypedDict):
    cx: float
    ambiguity: float
    threshold: float
    threshold_signal: float
    familiarity_signal: float
    failure_signal: float
    urgent_flag: bool
    intent_type: str
    verify_request: bool
    reflective_intent: float
    needs_external_evidence: float
    needs_task_plan: float
    needs_multi_source_integration: float
    low_confidence: float
    failure_wariness: float
    approach: float
    help_short: float
    decompose_min_complexity: float
    decompose_urgent_min_complexity: float
    decompose_max_ambiguity: float


class StyleInputs(TypedDict):
    urgency: float
    complexity: float
    ambiguity: float
    user_expertise: float
    threshold: float
    failure_wariness: float
    low_confidence: float
    resolution: float
    approach: float
    creativity: float
    risk_aversion: float
    verify_request: bool

