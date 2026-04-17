from __future__ import annotations

from schemas import ScoringInputs
from utils import clamp_to_unit_interval


# Penalty functions
def _hallucination_penalty(action: str, cx: float, ambiguity: float) -> float:
    base = {
        "act_respond": 0.90,
        "act_search": 0.30,
        "act_verify": 0.12,
        "act_clarify": 0.15,
        "act_decompose": 0.40,
        "act_think": 0.22,
        "act_synthesize": 0.20,
    }.get(action, 0.50)
    if action == "act_respond":
        base += 0.25 * cx + 0.20 * ambiguity
    elif action == "act_search":
        base += 0.10 * ambiguity
    elif action == "act_decompose":
        base += 0.10 * cx
    return clamp_to_unit_interval(base)


def _redundancy_penalty(
    action: str, cx: float, familiarity: float, urgency: float
) -> float:
    if action == "act_respond":
        return clamp_to_unit_interval(
            0.45 + 0.25 * (1.0 - cx) + 0.15 * familiarity + 0.10 * (1.0 - urgency)
        )
    return {
        "act_search": 0.42,
        "act_verify": 0.30,
        "act_clarify": 0.18,
        "act_decompose": 0.72,
        "act_think": 0.82,
        "act_synthesize": 0.26,
    }.get(action, 0.35)


def _premature_penalty(
    action: str, cx: float, ambiguity: float, threshold: float
) -> float:
    if action == "act_respond":
        return clamp_to_unit_interval(0.40 + 0.35 * cx + 0.25 * ambiguity + 0.20 * threshold)
    return {
        "act_search": 0.20,
        "act_verify": 0.08,
        "act_clarify": 0.12,
        "act_decompose": 0.10,
        "act_think": 0.15,
        "act_synthesize": 0.06,
    }.get(action, 0.20)


def _rabbit_hole_penalty(action: str, cx: float, ambiguity: float) -> float:
    if action == "act_think":
        return clamp_to_unit_interval(0.36 + 0.16 * (1.0 - cx) + 0.14 * (1.0 - ambiguity))
    if action == "act_decompose":
        return clamp_to_unit_interval(0.48 + 0.18 * (1.0 - cx) + 0.18 * (1.0 - ambiguity))
    if action == "act_search":
        return clamp_to_unit_interval(0.35 + 0.15 * (1.0 - cx) + 0.15 * (1.0 - ambiguity))
    return {
        "act_respond": 0.10,
        "act_verify": 0.18,
        "act_clarify": 0.14,
        "act_synthesize": 0.22,
    }.get(action, 0.20)


# Action relevance map
ACTIONS = {
    "act_respond": {
        "efficiency": 1.00,
        "accuracy": lambda cx: clamp_to_unit_interval(1.00 - 1.10 * cx),
        "success_moderate": lambda cx: clamp_to_unit_interval(0.80 - 0.20 * cx),
        "knowledge": lambda cx: clamp_to_unit_interval(0.28 + 0.18 * cx),
        "novelty": lambda cx: clamp_to_unit_interval(0.18 + 0.10 * cx),
        "success_breakthrough": lambda cx: clamp_to_unit_interval(0.18 + 0.12 * cx),
        "coherence": lambda cx: clamp_to_unit_interval(0.72 - 0.10 * cx),
        "originality": lambda cx: clamp_to_unit_interval(0.16 + 0.10 * cx),
        "social": lambda cx: clamp_to_unit_interval(0.74 + 0.08 * (1.0 - cx)),
        "help_short": lambda cx: clamp_to_unit_interval(0.95 - 0.20 * cx),
        "help_long": lambda cx: clamp_to_unit_interval(0.25 + 0.20 * cx),
        "over_beneficial": lambda cx: clamp_to_unit_interval(0.45 - 0.15 * cx),
        "over_safety": lambda cx: clamp_to_unit_interval(0.45 - 0.20 * cx),
        "over_honesty": 0.60,
    },
    "act_clarify": {
        "efficiency": 0.65,
        "accuracy": lambda cx: clamp_to_unit_interval(0.55 + 0.25 * cx),
        "success_moderate": 0.72,
        "knowledge": lambda cx: clamp_to_unit_interval(0.45 + 0.20 * cx),
        "novelty": lambda cx: clamp_to_unit_interval(0.28 + 0.12 * cx),
        "success_breakthrough": lambda cx: clamp_to_unit_interval(0.28 + 0.12 * cx),
        "coherence": 0.82,
        "originality": lambda cx: clamp_to_unit_interval(0.18 + 0.10 * cx),
        "social": 0.95,
        "help_short": lambda cx: clamp_to_unit_interval(0.55 + 0.10 * (1.0 - cx)),
        "help_long": lambda cx: clamp_to_unit_interval(0.40 + 0.20 * cx),
        "over_beneficial": 0.85,
        "over_safety": 0.90,
        "over_honesty": 0.95,
    },
    "act_search": {
        "efficiency": 0.25,
        "accuracy": lambda cx: clamp_to_unit_interval(0.30 + 0.90 * cx),
        "success_moderate": lambda cx: clamp_to_unit_interval(0.55 + 0.20 * cx),
        "knowledge": lambda cx: clamp_to_unit_interval(0.68 + 0.22 * cx),
        "novelty": lambda cx: clamp_to_unit_interval(0.58 + 0.18 * cx),
        "success_breakthrough": lambda cx: clamp_to_unit_interval(0.45 + 0.18 * cx),
        "coherence": 0.58,
        "originality": lambda cx: clamp_to_unit_interval(0.48 + 0.16 * cx),
        "social": lambda cx: clamp_to_unit_interval(0.42 + 0.12 * (1.0 - cx)),
        "help_short": lambda cx: clamp_to_unit_interval(0.35 + 0.10 * (1.0 - cx)),
        "help_long": lambda cx: clamp_to_unit_interval(0.55 + 0.35 * cx),
        "over_beneficial": 0.72,
        "over_safety": 0.78,
        "over_honesty": 0.82,
    },
    "act_verify": {
        "efficiency": 0.35,
        "accuracy": lambda cx: clamp_to_unit_interval(0.75 + 0.20 * cx),
        "success_moderate": 0.90,
        "knowledge": lambda cx: clamp_to_unit_interval(0.62 + 0.15 * cx),
        "novelty": lambda cx: clamp_to_unit_interval(0.25 + 0.08 * cx),
        "success_breakthrough": lambda cx: clamp_to_unit_interval(0.38 + 0.10 * cx),
        "coherence": 0.86,
        "originality": lambda cx: clamp_to_unit_interval(0.24 + 0.08 * cx),
        "social": 0.88,
        "help_short": lambda cx: clamp_to_unit_interval(0.40 + 0.10 * (1.0 - cx)),
        "help_long": lambda cx: clamp_to_unit_interval(0.50 + 0.20 * cx),
        "over_beneficial": 0.96,
        "over_safety": 0.97,
        "over_honesty": 0.97,
    },
    "act_decompose": {
        "efficiency": 0.45,
        "accuracy": lambda cx: clamp_to_unit_interval(0.55 + 0.35 * cx),
        "success_moderate": lambda cx: clamp_to_unit_interval(0.65 + 0.15 * cx),
        "knowledge": lambda cx: clamp_to_unit_interval(0.72 + 0.20 * cx),
        "novelty": lambda cx: clamp_to_unit_interval(0.62 + 0.18 * cx),
        "success_breakthrough": lambda cx: clamp_to_unit_interval(0.62 + 0.22 * cx),
        "coherence": 0.80,
        "originality": lambda cx: clamp_to_unit_interval(0.66 + 0.18 * cx),
        "social": 0.72,
        "help_short": lambda cx: clamp_to_unit_interval(0.30 + 0.05 * (1.0 - cx)),
        "help_long": lambda cx: clamp_to_unit_interval(0.70 + 0.25 * cx),
        "over_beneficial": 0.70,
        "over_safety": 0.76,
        "over_honesty": 0.80,
    },
    "act_think": {
        "efficiency": 0.40,
        "accuracy": lambda cx: clamp_to_unit_interval(0.60 + 0.25 * cx),
        "success_moderate": lambda cx: clamp_to_unit_interval(0.45 + 0.20 * cx),
        "knowledge": lambda cx: clamp_to_unit_interval(0.66 + 0.18 * cx),
        "novelty": lambda cx: clamp_to_unit_interval(0.70 + 0.18 * cx),
        "success_breakthrough": lambda cx: clamp_to_unit_interval(0.68 + 0.20 * cx),
        "coherence": 0.74,
        "originality": lambda cx: clamp_to_unit_interval(0.74 + 0.16 * cx),
        "social": 0.58,
        "help_short": lambda cx: clamp_to_unit_interval(0.35 + 0.10 * (1.0 - cx)),
        "help_long": lambda cx: clamp_to_unit_interval(0.60 + 0.25 * cx),
        "over_beneficial": 0.78,
        "over_safety": 0.84,
        "over_honesty": 0.90,
    },
    "act_synthesize": {
        "efficiency": 0.30,
        "accuracy": lambda cx: clamp_to_unit_interval(0.74 + 0.12 * cx),
        "success_moderate": 0.82,
        "knowledge": lambda cx: clamp_to_unit_interval(0.78 + 0.16 * cx),
        "novelty": lambda cx: clamp_to_unit_interval(0.56 + 0.12 * cx),
        "success_breakthrough": lambda cx: clamp_to_unit_interval(0.54 + 0.14 * cx),
        "coherence": 0.84,
        "originality": lambda cx: clamp_to_unit_interval(0.82 + 0.12 * cx),
        "social": 0.68,
        "help_short": lambda cx: clamp_to_unit_interval(0.42 + 0.08 * (1.0 - cx)),
        "help_long": lambda cx: clamp_to_unit_interval(0.72 + 0.18 * cx),
        "over_beneficial": 0.90,
        "over_safety": 0.92,
        "over_honesty": 0.95,
    },
}


# Action reason mapping
def _action_reason(action: str) -> str:
    if action == "act_respond":
        return "Efficiency prevails."
    if action == "act_search":
        return "Accuracy prevails."
    if action == "act_verify":
        return "Risk or low confidence requires verification."
    if action == "act_decompose":
        return "Complex task benefits from decomposition."
    if action == "act_think":
        return "Reflective thinking improves answer quality."
    if action == "act_synthesize":
        return "Synthesis best combines complex evidence coherently."
    return "Ambiguity requires clarification."


# Action scoring
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


def _weighted_relevance_score(action: str, cx: float, weights: dict) -> float:
    score = 0.0
    effects = ACTIONS[action]
    for goal, weight in weights.items():
        effect = effects.get(goal)
        if effect is None:
            continue
        rel = effect(cx) if callable(effect) else float(effect)
        score += float(weight) * float(rel)
    return score


def _adjust_clarify(score: float, v: dict) -> float:
    score += 0.90 * v["ambiguity"] - 0.35 * v["ux"] - 0.15 * v["u"] + 0.20 * v["threshold"]
    score += 0.20 * v["securing"]
    score += 0.10 * v["coherence"] - 0.08 * v["valence"]
    score += 0.22 * v["social"] - 0.06 * v["originality"]
    score += 0.08 * (1.0 - v["error_tolerance"])
    score -= 0.55 * v["answerability"]
    score -= 0.20 * v["help_short"]
    score -= 0.15 * v["anti_redundant"]
    if v["ambiguity"] > 0.75 and (v["threshold_signal"] > 0.55 or v["low_confidence"] > 0.45):
        score += 0.18
    return score


def _adjust_respond(score: float, v: dict) -> float:
    score += 0.35 * v["u"] + 0.25 * (1.0 - v["ambiguity"]) + 0.15 * v["ux"] - 0.20 * v["cx"]
    score += 0.20 * v["familiarity"] - 0.35 * v["threshold"] - 0.30 * v["failure_wariness"]
    score -= 0.35 * v["securing"] + 0.20 * v["low_confidence"]
    score += 0.10 * (1.0 - v["arousal"])
    score += 0.12 * v["coherence"] + 0.10 * v["valence"]
    score += 0.14 * v["social"] - 0.06 * v["originality"]
    score -= 0.18 * v["risk_aversion"]
    score += 0.30 * v["help_short"] - 0.15 * v["help_long"]
    score += 0.45 * v["answerability"]
    score += 0.22 * v["error_tolerance"]
    score += 0.16 * v["help_short"]
    score += 0.12 * v["anti_redundant"]
    if v["cx"] >= 0.50:
        score -= 0.08 * v["knowledge"] + 0.10 * v["success_breakthrough"]
    return score


def _adjust_search(score: float, v: dict) -> float:
    score += 0.35 * v["cx"] + 0.20 * v["res"] - 0.15 * v["u"]
    score += 0.35 * v["threshold"] + 0.35 * (1.0 - v["familiarity"]) + 0.30 * v["failure_wariness"]
    score += 0.15 * v["securing"]
    score += 0.08 * v["arousal"]
    score += 0.06 * v["coherence"] + 0.02 * v["valence"]
    score += 0.10 * v["originality"] + 0.06 * v["social"]
    score += 0.08 * (1.0 - v["risk_aversion"])
    score += 0.10 * (1.0 - v["error_tolerance"])
    score += 0.10 * v["creativity"]
    score += 0.06 * v["help_long"] - 0.08 * v["help_short"]
    score += 0.14 * v["knowledge"] + 0.12 * v["novelty"] + 0.08 * v["success_breakthrough"]
    score += 0.50 * v["needs_external_evidence"]
    score += 0.12 * v["needs_multi_source_integration"]
    score -= 0.08 * v["needs_task_plan"]
    score -= v["reflective_search_penalty"] * v["reflective_intent"]
    return score


def _adjust_verify(score: float, v: dict) -> float:
    score += 0.65 * v["threshold"] + 0.75 * v["low_confidence"] + 0.35 * v["failure_wariness"]
    score += 0.15 * v["cx"] - 0.20 * v["u"] - 0.10 * v["ambiguity"]
    score += 0.30 * v["securing"]
    score += 0.14 * v["coherence"] - 0.14 * v["valence"]
    score += 0.10 * v["social"] - 0.08 * v["originality"]
    score += 0.25 * v["risk_aversion"]
    score -= 0.08 * v["arousal"]
    score += 0.55 * (1.0 - v["error_tolerance"])
    score += 0.08 * (1.0 - v["creativity"])
    score += 0.08 * v["help_long"] - 0.10 * v["help_short"]
    score += 0.32 * (1.0 if v["verify_request"] else 0.0)
    score += 0.05 * v["knowledge"]
    return score


def _adjust_decompose(score: float, v: dict) -> float:
    score += 0.30 * v["cx"] + 0.30 * v["res"] + 0.10 * (1.0 - v["ambiguity"]) - 0.12 * v["u"]
    score -= 0.28 * v["ambiguity"]
    if v["cx"] >= 0.60 and v["ambiguity"] <= 0.60:
        score += 0.10
    if v["cx"] < 0.35:
        score -= 0.35
    score += 0.10 * v["approach"]
    score += 0.10 * v["arousal"]
    score += 0.10 * v["coherence"] + 0.04 * v["valence"]
    score += 0.12 * v["originality"] + 0.08 * v["social"]
    score += 0.08 * v["creativity"]
    score -= 0.08 * (1.0 - v["error_tolerance"])
    score += 0.12 * v["help_long"] - 0.12 * v["help_short"]
    score += 0.08 * v["knowledge"] + 0.06 * v["novelty"] + 0.10 * v["success_breakthrough"]
    score += 0.24 * v["needs_task_plan"]
    score -= 0.12 * v["needs_external_evidence"]
    score += 0.02 * v["needs_multi_source_integration"]
    return score


def _adjust_think(score: float, v: dict) -> float:
    score += 0.35 * v["cx"] + 0.25 * v["ambiguity"] + 0.35 * v["approach"]
    score += 0.10 * v["low_confidence"] + 0.10 * (1.0 - v["u"])
    score -= 0.10 * v["threshold"]
    score += 0.20 * v["arousal"]
    score += 0.08 * v["coherence"] + 0.02 * v["valence"]
    score += 0.14 * v["originality"] + 0.04 * v["social"]
    score += 0.10 * (1.0 - v["risk_aversion"])
    score += 0.26 * v["creativity"]
    score -= 0.14 * (1.0 - v["error_tolerance"])
    score += 0.10 * v["help_long"] - 0.08 * v["help_short"]
    score += 0.10 * v["knowledge"] + 0.12 * v["novelty"] + 0.16 * v["success_breakthrough"]
    score += v["reflective_think_bonus"] * v["reflective_intent"]
    score -= 0.30 * v["anti_redundant"] * (0.70 + 0.30 * v["familiarity"])
    score -= 0.16 * v["answerability"]
    if v["cx"] >= 0.70 and v["approach"] >= 0.62 and (v["ambiguity"] >= 0.25 or v["low_confidence"] >= 0.30):
        score += 0.07
    elif v["cx"] >= 0.65 and v["approach"] >= 0.58 and (v["ambiguity"] >= 0.22 or v["low_confidence"] >= 0.28):
        score += 0.03
    return score


def _adjust_synthesize(score: float, v: dict) -> float:
    score += 0.24 * v["cx"] + 0.12 * v["res"] - 0.10 * v["u"]
    score += 0.16 * (1.0 - v["ambiguity"]) + 0.14 * (1.0 - v["familiarity"])
    score += 0.12 * v["approach"] + 0.08 * v["arousal"] + 0.16 * v["creativity"]
    score += 0.16 * v["coherence"] + 0.08 * v["valence"]
    score += 0.22 * v["originality"] + 0.10 * v["social"]
    score += 0.06 * (1.0 - v["low_confidence"])
    score += 0.12 * v["knowledge"] + 0.08 * v["novelty"] + 0.10 * v["success_breakthrough"]
    score += 0.14 * v["help_long"] - 0.10 * v["help_short"]
    score -= 0.12 * v["risk_aversion"]
    score -= 0.18 * v["threshold"]
    score -= 0.16 * v["failure_wariness"]
    score += 0.55 * v["needs_multi_source_integration"]
    score -= 0.12 * v["needs_external_evidence"]
    score -= 0.18 * v["needs_task_plan"]
    if v["cx"] >= 0.55 and v["ambiguity"] <= 0.60:
        score += 0.16
    if v["ambiguity"] >= 0.80:
        score -= 0.28
    if v["verify_request"]:
        score -= 0.25
    return score


def _apply_action_adjustments(action: str, score: float, v: dict) -> float:
    if action == "act_clarify":
        return _adjust_clarify(score, v)
    if action == "act_respond":
        return _adjust_respond(score, v)
    if action == "act_search":
        return _adjust_search(score, v)
    if action == "act_verify":
        return _adjust_verify(score, v)
    if action == "act_decompose":
        return _adjust_decompose(score, v)
    if action == "act_think":
        return _adjust_think(score, v)
    if action == "act_synthesize":
        return _adjust_synthesize(score, v)
    return score


def _safety_risk(action: str, v: dict) -> float:
    return {
        "act_respond": clamp_to_unit_interval(
            0.55 + 0.20 * v["cx"] + 0.25 * v["threshold"] + 0.20 * v["ambiguity"]
        ),
        "act_search": clamp_to_unit_interval(0.35 + 0.20 * v["threshold"]),
        "act_verify": 0.08,
        "act_clarify": 0.10,
        "act_decompose": 0.25,
        "act_synthesize": 0.12,
    }.get(action, 0.30)


def _honesty_risk(action: str, v: dict) -> float:
    return {
        "act_respond": clamp_to_unit_interval(
            0.40 + 0.30 * v["low_confidence"] + 0.15 * v["ambiguity"]
        ),
        "act_search": 0.18,
        "act_verify": 0.05,
        "act_clarify": 0.10,
        "act_decompose": 0.16,
        "act_synthesize": 0.08,
    }.get(action, 0.20)


def _beneficial_risk(action: str, v: dict) -> float:
    return {
        "act_respond": clamp_to_unit_interval(
            0.50 + 0.20 * v["cx"] + 0.20 * v["threshold"] + 0.20 * v["low_confidence"]
        ),
        "act_search": 0.22,
        "act_verify": 0.06,
        "act_clarify": 0.10,
        "act_decompose": 0.18,
        "act_synthesize": 0.10,
    }.get(action, 0.20)


def _apply_penalties_and_overgoals(action: str, score: float, v: dict) -> float:
    score -= v["anti_hall"] * _hallucination_penalty(action, cx=v["cx"], ambiguity=v["ambiguity"])
    score -= (
        v["anti_redundant"]
        * _redundancy_penalty(action, cx=v["cx"], familiarity=v["familiarity"], urgency=v["u"])
        * (0.70 + 0.30 * (1.0 - v["u"]))
    )
    score -= (
        v["anti_premature"]
        * _premature_penalty(action, cx=v["cx"], ambiguity=v["ambiguity"], threshold=v["threshold"])
        * (0.60 + 0.40 * v["threshold"])
    )

    rabbit_hole_scale = 0.40 + 0.22 * v["help_short"]
    if action == "act_decompose":
        rabbit_hole_scale *= 1.0 - 0.35 * v["needs_task_plan"]
    score -= (
        v["anti_rabbit_hole"]
        * _rabbit_hole_penalty(action, cx=v["cx"], ambiguity=v["ambiguity"])
        * rabbit_hole_scale
    )

    safety_risk = _safety_risk(action, v)
    honesty_risk = _honesty_risk(action, v)
    beneficial_risk = _beneficial_risk(action, v)
    score -= v["over_safety"] * safety_risk * (0.65 + 0.35 * v["securing"])
    score -= v["over_honesty"] * honesty_risk * (0.60 + 0.40 * v["low_confidence"])
    score -= v["over_beneficial"] * beneficial_risk * (0.60 + 0.40 * v["securing"])
    return score


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
