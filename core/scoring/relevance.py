from __future__ import annotations

from utils import clamp_to_unit_interval


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

