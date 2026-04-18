from __future__ import annotations

from utils import clamp_to_unit_interval


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

