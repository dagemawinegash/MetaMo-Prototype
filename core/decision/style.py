from __future__ import annotations

from schemas import StyleInputs


def _determine_respond_style(
    style_inputs: StyleInputs,
) -> str:
    urgency = style_inputs["urgency"]
    complexity = style_inputs["complexity"]
    ambiguity = style_inputs["ambiguity"]
    user_expertise = style_inputs["user_expertise"]
    threshold = style_inputs["threshold"]
    failure_wariness = style_inputs["failure_wariness"]
    low_confidence = style_inputs["low_confidence"]
    resolution = style_inputs["resolution"]
    approach = style_inputs["approach"]
    creativity = style_inputs["creativity"]
    risk_aversion = style_inputs["risk_aversion"]
    verify_request = style_inputs["verify_request"]

    style_scores = {
        "style_concise": 0.40
        + 0.70 * urgency
        + 0.20 * (1.0 - complexity)
        + 0.15 * (1.0 - ambiguity),
        "style_thorough": 0.35
        + 0.55 * complexity
        + 0.45 * resolution
        + 0.15 * ambiguity
        - 0.35 * urgency,
        "style_exploratory": 0.30
        + 0.55 * creativity
        + 0.40 * approach
        + 0.20 * complexity
        - 0.35 * threshold
        - 0.20 * risk_aversion
        - 0.20 * failure_wariness,
        "style_cautious": 0.35
        + 0.55 * threshold
        + 0.45 * low_confidence
        + 0.30 * failure_wariness
        + 0.20 * risk_aversion
        + (0.25 if verify_request else 0.0),
        "style_tutorial": 0.35
        + 0.70 * (1.0 - user_expertise)
        + 0.20 * ambiguity
        + 0.10 * complexity,
    }
    return max(style_scores, key=style_scores.get)

