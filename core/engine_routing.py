from __future__ import annotations

from core.state import ACTION_ACTIVE_FLOOR, ACTION_BLOCKED_SCORE
from schemas import RoutingInputs


def _extract_routing_context(inputs: RoutingInputs) -> dict[str, float | bool | str]:
    return {
        "cx": float(inputs["cx"]),
        "ambiguity": float(inputs["ambiguity"]),
        "threshold": float(inputs["threshold"]),
        "threshold_signal": float(inputs["threshold_signal"]),
        "familiarity_signal": float(inputs["familiarity_signal"]),
        "failure_signal": float(inputs["failure_signal"]),
        "urgent_flag": bool(inputs["urgent_flag"]),
        "intent_type": str(inputs["intent_type"]),
        "verify_request": bool(inputs["verify_request"]),
        "reflective_intent": float(inputs["reflective_intent"]),
        "needs_external_evidence": float(inputs["needs_external_evidence"]),
        "needs_task_plan": float(inputs["needs_task_plan"]),
        "needs_multi_source_integration": float(inputs["needs_multi_source_integration"]),
        "low_confidence": float(inputs["low_confidence"]),
        "failure_wariness": float(inputs["failure_wariness"]),
        "approach": float(inputs["approach"]),
        "help_short": float(inputs["help_short"]),
        "decompose_min_complexity": float(inputs["decompose_min_complexity"]),
        "decompose_urgent_min_complexity": float(inputs["decompose_urgent_min_complexity"]),
        "decompose_max_ambiguity": float(inputs["decompose_max_ambiguity"]),
    }


def _apply_decompose_guards(scores: dict[str, float], ctx: dict[str, float | bool | str]) -> None:
    cx = float(ctx["cx"])
    ambiguity = float(ctx["ambiguity"])
    urgent_flag = bool(ctx["urgent_flag"])
    reflective_intent = float(ctx["reflective_intent"])
    needs_external_evidence = float(ctx["needs_external_evidence"])
    needs_task_plan = float(ctx["needs_task_plan"])
    decompose_min_complexity = float(ctx["decompose_min_complexity"])
    decompose_urgent_min_complexity = float(ctx["decompose_urgent_min_complexity"])
    decompose_max_ambiguity = float(ctx["decompose_max_ambiguity"])

    decompose_min = (
        decompose_urgent_min_complexity if urgent_flag else decompose_min_complexity
    )
    if (
        cx < decompose_min or ambiguity >= decompose_max_ambiguity
    ) and "act_decompose" in scores:
        scores["act_decompose"] = ACTION_BLOCKED_SCORE
    if "act_decompose" in scores:
        if needs_task_plan < 0.45 and not (
            cx >= 0.78 and ambiguity <= 0.35 and reflective_intent >= 0.75
        ):
            scores["act_decompose"] = ACTION_BLOCKED_SCORE
        elif needs_external_evidence >= 0.75 and needs_task_plan <= 0.55:
            scores["act_decompose"] -= 0.30
        if needs_task_plan >= 0.60:
            scores["act_decompose"] += 0.10
        elif needs_task_plan <= 0.18 and cx < 0.55:
            scores["act_decompose"] -= 0.30


def _apply_search_synthesize_local_guards(
    scores: dict[str, float], ctx: dict[str, float | bool | str]
) -> None:
    needs_external_evidence = float(ctx["needs_external_evidence"])
    needs_task_plan = float(ctx["needs_task_plan"])
    needs_multi_source_integration = float(ctx["needs_multi_source_integration"])
    verify_request = bool(ctx["verify_request"])

    if "act_search" in scores:
        if needs_external_evidence >= 0.60:
            scores["act_search"] += 0.30
            if needs_task_plan <= 0.45:
                scores["act_search"] += 0.12
        elif needs_external_evidence <= 0.22 and not verify_request:
            scores["act_search"] -= 0.18

    if "act_synthesize" in scores:
        if needs_multi_source_integration >= 0.65:
            scores["act_synthesize"] += 0.20
        elif needs_multi_source_integration < 0.65 and not verify_request:
            scores["act_synthesize"] = ACTION_BLOCKED_SCORE
        if (
            needs_task_plan >= 0.70
            and needs_task_plan >= needs_multi_source_integration
        ):
            scores["act_synthesize"] -= 0.22
        if needs_external_evidence >= 0.85 and needs_task_plan <= 0.45:
            scores["act_synthesize"] -= 0.15


def _apply_search_synthesize_arbitration(
    scores: dict[str, float], ctx: dict[str, float | bool | str]
) -> None:
    needs_external_evidence = float(ctx["needs_external_evidence"])
    needs_task_plan = float(ctx["needs_task_plan"])
    needs_multi_source_integration = float(ctx["needs_multi_source_integration"])

    if (
        "act_search" in scores
        and "act_decompose" in scores
        and "act_synthesize" in scores
        and scores["act_search"] > ACTION_ACTIVE_FLOOR
        and scores["act_decompose"] > ACTION_ACTIVE_FLOOR
    ):
        if (
            needs_external_evidence >= 0.70
            and needs_external_evidence >= needs_task_plan + 0.15
            and needs_external_evidence >= needs_multi_source_integration - 0.02
        ):
            scores["act_search"] += 0.26
            scores["act_decompose"] -= 0.26
            if scores["act_synthesize"] > ACTION_ACTIVE_FLOOR:
                scores["act_synthesize"] -= 0.12
        elif (
            needs_task_plan >= 0.72
            and needs_task_plan >= needs_external_evidence + 0.18
            and needs_task_plan >= needs_multi_source_integration + 0.12
        ):
            scores["act_decompose"] += 0.18
            scores["act_search"] -= 0.12
            if scores["act_synthesize"] > ACTION_ACTIVE_FLOOR:
                scores["act_synthesize"] -= 0.10
        elif (
            scores["act_synthesize"] > ACTION_ACTIVE_FLOOR
            and needs_multi_source_integration >= 0.72
            and needs_multi_source_integration >= needs_task_plan + 0.15
        ):
            scores["act_synthesize"] += 0.16
            scores["act_decompose"] -= 0.16

    if (
        "act_search" in scores
        and "act_synthesize" in scores
        and scores["act_search"] > ACTION_ACTIVE_FLOOR
        and scores["act_synthesize"] > ACTION_ACTIVE_FLOOR
    ):
        if (
            needs_external_evidence >= 0.85
            and needs_multi_source_integration >= 0.75
            and needs_task_plan <= 0.55
        ):
            scores["act_search"] += 0.18
            scores["act_synthesize"] -= 0.18


def _apply_verify_guards(scores: dict[str, float], ctx: dict[str, float | bool | str]) -> None:
    ambiguity = float(ctx["ambiguity"])
    threshold = float(ctx["threshold"])
    low_confidence = float(ctx["low_confidence"])
    failure_wariness = float(ctx["failure_wariness"])
    verify_request = bool(ctx["verify_request"])
    cx = float(ctx["cx"])
    intent_type = str(ctx["intent_type"])

    if "act_verify" in scores:
        if ambiguity >= 0.85:
            scores["act_verify"] = ACTION_BLOCKED_SCORE
        elif not (
            verify_request
            or (threshold >= 0.55 and low_confidence >= 0.40)
            or failure_wariness >= 0.45
        ):
            scores["act_verify"] = ACTION_BLOCKED_SCORE

    if verify_request and "act_verify" in scores:
        scores["act_verify"] += 0.45
        if "act_synthesize" in scores:
            scores["act_synthesize"] -= 0.35

    if (
        not verify_request
        and cx >= 0.70
        and ambiguity <= 0.65
        and intent_type in {"mixed", "reflective"}
        and "act_verify" in scores
    ):
        scores["act_verify"] -= 0.20


def _apply_intent_and_ambiguity_guards(
    scores: dict[str, float], ctx: dict[str, float | bool | str]
) -> None:
    intent_type = str(ctx["intent_type"])
    verify_request = bool(ctx["verify_request"])
    ambiguity = float(ctx["ambiguity"])
    cx = float(ctx["cx"])

    if (
        intent_type == "factual"
        and not verify_request
        and ambiguity <= 0.55
        and cx >= 0.45
        and "act_search" in scores
    ):
        scores["act_search"] += 0.20

    if ambiguity >= 0.75 and not verify_request:
        if "act_clarify" in scores:
            scores["act_clarify"] += 0.24
        if "act_synthesize" in scores:
            scores["act_synthesize"] -= 0.35


def _apply_fast_lane_guards(scores: dict[str, float], ctx: dict[str, float | bool | str]) -> None:
    cx = float(ctx["cx"])
    ambiguity = float(ctx["ambiguity"])
    threshold_signal = float(ctx["threshold_signal"])
    failure_signal = float(ctx["failure_signal"])
    familiarity_signal = float(ctx["familiarity_signal"])
    low_confidence = float(ctx["low_confidence"])
    verify_request = bool(ctx["verify_request"])
    help_short = float(ctx["help_short"])

    if (
        cx <= 0.30
        and ambiguity <= 0.30
        and threshold_signal <= 0.25
        and failure_signal <= 0.25
        and familiarity_signal >= 0.70
        and low_confidence <= 0.35
        and not verify_request
    ):
        if "act_verify" in scores:
            scores["act_verify"] = ACTION_BLOCKED_SCORE
        if "act_search" in scores:
            scores["act_search"] = ACTION_BLOCKED_SCORE
        if "act_clarify" in scores:
            scores["act_clarify"] = ACTION_BLOCKED_SCORE
        if "act_think" in scores:
            scores["act_think"] = ACTION_BLOCKED_SCORE
        if "act_respond" in scores:
            scores["act_respond"] += 0.60

    if (
        cx <= 0.45
        and ambiguity <= 0.35
        and threshold_signal <= 0.20
        and low_confidence <= 0.30
        and familiarity_signal >= 0.80
        and help_short >= 0.55
        and not verify_request
    ):
        if "act_clarify" in scores:
            scores["act_clarify"] = ACTION_BLOCKED_SCORE
        if "act_search" in scores:
            scores["act_search"] = ACTION_BLOCKED_SCORE
        if "act_respond" in scores:
            scores["act_respond"] += 0.40


def _apply_final_think_synthesize_guards(
    scores: dict[str, float], ctx: dict[str, float | bool | str]
) -> None:
    cx = float(ctx["cx"])
    ambiguity = float(ctx["ambiguity"])
    low_confidence = float(ctx["low_confidence"])
    approach = float(ctx["approach"])
    threshold = float(ctx["threshold"])
    failure_wariness = float(ctx["failure_wariness"])
    verify_request = bool(ctx["verify_request"])
    reflective_intent = float(ctx["reflective_intent"])

    if "act_think" in scores and not (
        cx >= 0.55
        or ambiguity >= 0.40
        or low_confidence >= 0.45
        or (approach >= 0.62 and cx >= 0.50)
    ):
        scores["act_think"] = ACTION_BLOCKED_SCORE

    if "act_synthesize" in scores and not (
        (
            cx >= 0.68
            and ambiguity <= 0.55
            and threshold <= 0.55
            and failure_wariness <= 0.35
            and not verify_request
        )
        or (
            cx >= 0.72
            and reflective_intent >= 0.70
            and ambiguity <= 0.60
            and threshold <= 0.60
            and failure_wariness <= 0.35
            and not verify_request
        )
    ):
        scores["act_synthesize"] = ACTION_BLOCKED_SCORE


# Routing guardrails
def _apply_routing_guards(
    scores: dict[str, float],
    inputs: RoutingInputs,
) -> dict[str, float]:
    """Apply hard constraints and context routing arbitration on raw action scores."""
    ctx = _extract_routing_context(inputs)
    _apply_decompose_guards(scores, ctx)
    _apply_search_synthesize_local_guards(scores, ctx)
    _apply_search_synthesize_arbitration(scores, ctx)
    _apply_verify_guards(scores, ctx)
    _apply_intent_and_ambiguity_guards(scores, ctx)
    _apply_fast_lane_guards(scores, ctx)
    _apply_final_think_synthesize_guards(scores, ctx)
    return scores


# Tie-break selection
def _select_action(
    scores: dict[str, float],
    *,
    intent_type: str,
    low_confidence: float,
    threshold: float,
    intent_margin: float,
) -> tuple[str, list[tuple[str, float]]]:
    """Resolve tie-breaks and select the best action."""
    search_score = float(scores.get("act_search", ACTION_BLOCKED_SCORE))
    think_score = float(scores.get("act_think", ACTION_BLOCKED_SCORE))
    if (
        search_score > ACTION_ACTIVE_FLOOR
        and think_score > ACTION_ACTIVE_FLOOR
        and abs(search_score - think_score) <= intent_margin
    ):
        if intent_type == "reflective":
            preferred = "act_think"
        elif intent_type == "factual":
            preferred = "act_search"
        else:
            preferred = (
                "act_search"
                if (low_confidence >= 0.40 or threshold >= 0.45)
                else "act_think"
            )
        scores[preferred] = max(search_score, think_score) + intent_margin + 1e-4

    best_action = max(scores, key=scores.get)
    top_scores = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
    return best_action, top_scores
