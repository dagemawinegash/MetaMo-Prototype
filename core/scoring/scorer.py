from __future__ import annotations

from schemas import ScoringInputs

from .adjustments import _apply_action_adjustments
from .penalties import _apply_penalties_and_overgoals
from .relevance import ACTIONS, _weighted_relevance_score


def _extract_scoring_context(inputs: ScoringInputs) -> dict:
    return {
        "cx": float(inputs["cx"]),
        "ambiguity": float(inputs["ambiguity"]),
        "ux": float(inputs["ux"]),
        "u": float(inputs["u"]),
        "res": float(inputs["res"]),
        "threshold": float(inputs["threshold"]),
        "threshold_signal": float(inputs["threshold_signal"]),
        "familiarity": float(inputs["familiarity"]),
        "familiarity_signal": float(inputs["familiarity_signal"]),
        "failure_wariness": float(inputs["failure_wariness"]),
        "failure_signal": float(inputs["failure_signal"]),
        "securing": float(inputs["securing"]),
        "approach": float(inputs["approach"]),
        "arousal": float(inputs["arousal"]),
        "risk_aversion": float(inputs["risk_aversion"]),
        "error_tolerance": float(inputs["error_tolerance"]),
        "creativity": float(inputs["creativity"]),
        "valence": float(inputs["valence"]),
        "low_confidence": float(inputs["low_confidence"]),
        "answerability": float(inputs["answerability"]),
        "needs_external_evidence": float(inputs["needs_external_evidence"]),
        "needs_task_plan": float(inputs["needs_task_plan"]),
        "needs_multi_source_integration": float(inputs["needs_multi_source_integration"]),
        "reflective_intent": float(inputs["reflective_intent"]),
        "verify_request": bool(inputs["verify_request"]),
        "anti_hall": float(inputs["anti_hall"]),
        "anti_redundant": float(inputs["anti_redundant"]),
        "anti_rabbit_hole": float(inputs["anti_rabbit_hole"]),
        "anti_premature": float(inputs["anti_premature"]),
        "coherence": float(inputs["coherence"]),
        "originality": float(inputs["originality"]),
        "social": float(inputs["social"]),
        "help_short": float(inputs["help_short"]),
        "help_long": float(inputs["help_long"]),
        "over_beneficial": float(inputs["over_beneficial"]),
        "over_safety": float(inputs["over_safety"]),
        "over_honesty": float(inputs["over_honesty"]),
        "knowledge": float(inputs["knowledge"]),
        "novelty": float(inputs["novelty"]),
        "success_breakthrough": float(inputs["success_breakthrough"]),
        "reflective_think_bonus": float(inputs["reflective_think_bonus"]),
        "reflective_search_penalty": float(inputs["reflective_search_penalty"]),
        "weights": inputs["weights"],
    }


def _score_actions(
    inputs: ScoringInputs,
) -> dict[str, float]:
    """Score all actions using weighted relevance and anti-goal penalties."""
    v = _extract_scoring_context(inputs)
    scores: dict[str, float] = {}
    for action in ACTIONS:
        score = _weighted_relevance_score(action, v["cx"], v["weights"])
        score = _apply_action_adjustments(action, score, v)
        score = _apply_penalties_and_overgoals(action, score, v)
        scores[action] = score

    return scores

