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
def _score_actions(
    inputs: ScoringInputs,
) -> dict[str, float]:
    """Score all actions using weighted relevance and anti-goal penalties."""
    cx = float(inputs["cx"])
    ambiguity = float(inputs["ambiguity"])
    ux = float(inputs["ux"])
    u = float(inputs["u"])
    res = float(inputs["res"])
    threshold = float(inputs["threshold"])
    threshold_signal = float(inputs["threshold_signal"])
    familiarity = float(inputs["familiarity"])
    familiarity_signal = float(inputs["familiarity_signal"])
    failure_wariness = float(inputs["failure_wariness"])
    failure_signal = float(inputs["failure_signal"])
    securing = float(inputs["securing"])
    approach = float(inputs["approach"])
    arousal = float(inputs["arousal"])
    risk_aversion = float(inputs["risk_aversion"])
    error_tolerance = float(inputs["error_tolerance"])
    creativity = float(inputs["creativity"])
    valence = float(inputs["valence"])
    low_confidence = float(inputs["low_confidence"])
    answerability = float(inputs["answerability"])
    needs_external_evidence = float(inputs["needs_external_evidence"])
    needs_task_plan = float(inputs["needs_task_plan"])
    needs_multi_source_integration = float(inputs["needs_multi_source_integration"])
    reflective_intent = float(inputs["reflective_intent"])
    verify_request = bool(inputs["verify_request"])
    anti_hall = float(inputs["anti_hall"])
    anti_redundant = float(inputs["anti_redundant"])
    anti_rabbit_hole = float(inputs["anti_rabbit_hole"])
    anti_premature = float(inputs["anti_premature"])
    coherence = float(inputs["coherence"])
    originality = float(inputs["originality"])
    social = float(inputs["social"])
    help_short = float(inputs["help_short"])
    help_long = float(inputs["help_long"])
    over_beneficial = float(inputs["over_beneficial"])
    over_safety = float(inputs["over_safety"])
    over_honesty = float(inputs["over_honesty"])
    knowledge = float(inputs["knowledge"])
    novelty = float(inputs["novelty"])
    success_breakthrough = float(inputs["success_breakthrough"])
    reflective_think_bonus = float(inputs["reflective_think_bonus"])
    reflective_search_penalty = float(inputs["reflective_search_penalty"])
    weights = inputs["weights"]

    scores: dict[str, float] = {}
    for action, effects in ACTIONS.items():
        score = 0.0
        for goal, weight in weights.items():
            effect = effects.get(goal)
            if effect is None:
                continue
            rel = effect(cx) if callable(effect) else float(effect)
            score += float(weight) * float(rel)

        if action == "act_clarify":
            score += 0.90 * ambiguity - 0.35 * ux - 0.15 * u + 0.20 * threshold
            score += 0.20 * securing
            score += 0.10 * coherence - 0.08 * valence
            score += 0.22 * social - 0.06 * originality
            score += 0.08 * (1.0 - error_tolerance)
            score -= 0.55 * answerability
            score -= 0.20 * help_short
            score -= 0.15 * anti_redundant
            if ambiguity > 0.75 and (threshold_signal > 0.55 or low_confidence > 0.45):
                score += 0.18
        elif action == "act_respond":
            score += 0.35 * u + 0.25 * (1.0 - ambiguity) + 0.15 * ux - 0.20 * cx
            score += 0.20 * familiarity - 0.35 * threshold - 0.30 * failure_wariness
            score -= 0.35 * securing + 0.20 * low_confidence
            score += 0.10 * (1.0 - arousal)
            score += 0.12 * coherence + 0.10 * valence
            score += 0.14 * social - 0.06 * originality
            score -= 0.18 * risk_aversion
            score += 0.30 * help_short - 0.15 * help_long
            score += 0.45 * answerability
            score += 0.22 * error_tolerance
            score += 0.16 * help_short
            score += 0.12 * anti_redundant
            if cx >= 0.50:
                score -= 0.08 * knowledge + 0.10 * success_breakthrough
        elif action == "act_search":
            score += 0.35 * cx + 0.20 * res - 0.15 * u
            score += (
                0.35 * threshold + 0.35 * (1.0 - familiarity) + 0.30 * failure_wariness
            )
            score += 0.15 * securing
            score += 0.08 * arousal
            score += 0.06 * coherence + 0.02 * valence
            score += 0.10 * originality + 0.06 * social
            score += 0.08 * (1.0 - risk_aversion)
            score += 0.10 * (1.0 - error_tolerance)
            score += 0.10 * creativity
            score += 0.06 * help_long - 0.08 * help_short
            score += 0.14 * knowledge + 0.12 * novelty + 0.08 * success_breakthrough
            score += 0.50 * needs_external_evidence
            score += 0.12 * needs_multi_source_integration
            score -= 0.08 * needs_task_plan
            score -= reflective_search_penalty * reflective_intent
        elif action == "act_verify":
            score += 0.65 * threshold + 0.75 * low_confidence + 0.35 * failure_wariness
            score += 0.15 * cx - 0.20 * u - 0.10 * ambiguity
            score += 0.30 * securing
            score += 0.14 * coherence - 0.14 * valence
            score += 0.10 * social - 0.08 * originality
            score += 0.25 * risk_aversion
            score -= 0.08 * arousal
            score += 0.55 * (1.0 - error_tolerance)
            score += 0.08 * (1.0 - creativity)
            score += 0.08 * help_long - 0.10 * help_short
            score += 0.32 * (1.0 if verify_request else 0.0)
            score += 0.05 * knowledge
        elif action == "act_decompose":
            score += 0.30 * cx + 0.30 * res + 0.10 * (1.0 - ambiguity) - 0.12 * u
            score -= 0.28 * ambiguity
            if cx >= 0.60 and ambiguity <= 0.60:
                score += 0.10
            if cx < 0.35:
                score -= 0.35
            score += 0.10 * approach
            score += 0.10 * arousal
            score += 0.10 * coherence + 0.04 * valence
            score += 0.12 * originality + 0.08 * social
            score += 0.08 * creativity
            score -= 0.08 * (1.0 - error_tolerance)
            score += 0.12 * help_long - 0.12 * help_short
            score += 0.08 * knowledge + 0.06 * novelty + 0.10 * success_breakthrough
            score += 0.24 * needs_task_plan
            score -= 0.12 * needs_external_evidence
            score += 0.02 * needs_multi_source_integration
        elif action == "act_think":
            score += 0.35 * cx + 0.25 * ambiguity + 0.35 * approach
            score += 0.10 * low_confidence + 0.10 * (1.0 - u)
            score -= 0.10 * threshold
            score += 0.20 * arousal
            score += 0.08 * coherence + 0.02 * valence
            score += 0.14 * originality + 0.04 * social
            score += 0.10 * (1.0 - risk_aversion)
            score += 0.26 * creativity
            score -= 0.14 * (1.0 - error_tolerance)
            score += 0.10 * help_long - 0.08 * help_short
            score += 0.10 * knowledge + 0.12 * novelty + 0.16 * success_breakthrough
            score += reflective_think_bonus * reflective_intent
            score -= 0.30 * anti_redundant * (0.70 + 0.30 * familiarity)
            score -= 0.16 * answerability
            if (
                cx >= 0.70
                and approach >= 0.62
                and (ambiguity >= 0.25 or low_confidence >= 0.30)
            ):
                score += 0.07
            elif (
                cx >= 0.65
                and approach >= 0.58
                and (ambiguity >= 0.22 or low_confidence >= 0.28)
            ):
                score += 0.03
        elif action == "act_synthesize":
            score += 0.24 * cx + 0.12 * res - 0.10 * u
            score += 0.16 * (1.0 - ambiguity) + 0.14 * (1.0 - familiarity)
            score += 0.12 * approach + 0.08 * arousal + 0.16 * creativity
            score += 0.16 * coherence + 0.08 * valence
            score += 0.22 * originality + 0.10 * social
            score += 0.06 * (1.0 - low_confidence)
            score += 0.12 * knowledge + 0.08 * novelty + 0.10 * success_breakthrough
            score += 0.14 * help_long - 0.10 * help_short
            score -= 0.12 * risk_aversion
            score -= 0.18 * threshold
            score -= 0.16 * failure_wariness
            score += 0.55 * needs_multi_source_integration
            score -= 0.12 * needs_external_evidence
            score -= 0.18 * needs_task_plan
            if cx >= 0.55 and ambiguity <= 0.60:
                score += 0.16
            if ambiguity >= 0.80:
                score -= 0.28
            if verify_request:
                score -= 0.25

        score -= anti_hall * _hallucination_penalty(action, cx=cx, ambiguity=ambiguity)
        score -= (
            anti_redundant
            * _redundancy_penalty(action, cx=cx, familiarity=familiarity, urgency=u)
            * (0.70 + 0.30 * (1.0 - u))
        )
        score -= (
            anti_premature
            * _premature_penalty(
                action, cx=cx, ambiguity=ambiguity, threshold=threshold
            )
            * (0.60 + 0.40 * threshold)
        )
        rabbit_hole_scale = 0.40 + 0.22 * help_short
        if action == "act_decompose":
            rabbit_hole_scale *= 1.0 - 0.35 * needs_task_plan
        score -= (
            anti_rabbit_hole
            * _rabbit_hole_penalty(action, cx=cx, ambiguity=ambiguity)
            * rabbit_hole_scale
        )

        safety_risk = {
            "act_respond": clamp_to_unit_interval(
                0.55 + 0.20 * cx + 0.25 * threshold + 0.20 * ambiguity
            ),
            "act_search": clamp_to_unit_interval(0.35 + 0.20 * threshold),
            "act_verify": 0.08,
            "act_clarify": 0.10,
            "act_decompose": 0.25,
            "act_synthesize": 0.12,
        }.get(action, 0.30)
        honesty_risk = {
            "act_respond": clamp_to_unit_interval(0.40 + 0.30 * low_confidence + 0.15 * ambiguity),
            "act_search": 0.18,
            "act_verify": 0.05,
            "act_clarify": 0.10,
            "act_decompose": 0.16,
            "act_synthesize": 0.08,
        }.get(action, 0.20)

        score -= over_safety * safety_risk * (0.65 + 0.35 * securing)
        score -= over_honesty * honesty_risk * (0.60 + 0.40 * low_confidence)
        beneficial_risk = {
            "act_respond": clamp_to_unit_interval(
                0.50 + 0.20 * cx + 0.20 * threshold + 0.20 * low_confidence
            ),
            "act_search": 0.22,
            "act_verify": 0.06,
            "act_clarify": 0.10,
            "act_decompose": 0.18,
            "act_synthesize": 0.10,
        }.get(action, 0.20)
        score -= over_beneficial * beneficial_risk * (0.60 + 0.40 * securing)

        scores[action] = score

    return scores
