from __future__ import annotations


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

