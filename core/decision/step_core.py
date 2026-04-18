from __future__ import annotations

from config import DEFAULT_ANTI_GOALS
from core.engine_routing import _apply_routing_guards, _select_action
from core.scoring import _action_reason, _score_actions
from core.state import _appraise_modulators, _goal_weights
from schemas import RoutingInputs, ScoringInputs, StyleInputs
from utils import clamp_to_unit_interval

from .style import _determine_respond_style


def _extract_step_settings(params: dict) -> dict[str, float]:
    return {
        "decompose_min_complexity": float(params.get("decompose_min_complexity", 0.60)),
        "decompose_urgent_min_complexity": float(
            params.get("decompose_urgent_min_complexity", 0.70)
        ),
        "decompose_max_ambiguity": float(params.get("decompose_max_ambiguity", 0.70)),
        "reflective_think_bonus": float(params.get("reflective_think_bonus", 0.14)),
        "reflective_search_penalty": float(
            params.get("reflective_search_penalty", 0.10)
        ),
        "intent_margin": float(
            params.get("intent_margin", params.get("think_search_tie_margin", 0.12))
        ),
    }


def _extract_appraisal_values(appraisal: dict) -> dict[str, float | bool | str]:
    return {
        "turn_count": int(appraisal["turn_count"]),
        "cold_weight": float(appraisal["cold_weight"]),
        "cx": float(appraisal["cx"]),
        "ambiguity": float(appraisal["ambiguity"]),
        "threshold_signal": float(appraisal["threshold_signal"]),
        "familiarity_signal": float(appraisal["familiarity_signal"]),
        "failure_signal": float(appraisal["failure_signal"]),
        "urgent_flag": bool(appraisal["urgent_flag"]),
        "intent_type": str(appraisal["intent_type"]),
        "verify_request": bool(appraisal["verify_request"]),
        "reflective_intent": float(appraisal["reflective_intent"]),
        "needs_external_evidence": float(appraisal["needs_external_evidence"]),
        "needs_task_plan": float(appraisal["needs_task_plan"]),
        "needs_multi_source_integration": float(
            appraisal["needs_multi_source_integration"]
        ),
        "u": float(appraisal["u"]),
        "res": float(appraisal["res"]),
        "ux": float(appraisal["ux"]),
        "threshold": float(appraisal["threshold"]),
        "familiarity": float(appraisal["familiarity"]),
        "failure_wariness": float(appraisal["failure_wariness"]),
        "securing": float(appraisal["securing"]),
        "approach": float(appraisal["approach"]),
        "arousal": float(appraisal["arousal"]),
        "risk_aversion": float(appraisal["risk_aversion"]),
        "error_tolerance": float(appraisal["error_tolerance"]),
        "creativity": float(appraisal["creativity"]),
        "valence": float(appraisal["valence"]),
    }


def _extract_goal_and_anti_values(goals: dict, anti_goals: dict) -> dict[str, float]:
    return {
        "anti_hall": float(anti_goals.get("hallucinate", 0.35)),
        "anti_redundant": float(anti_goals.get("redundant", 0.30)),
        "anti_rabbit_hole": float(anti_goals.get("rabbit_hole", 0.28)),
        "anti_premature": float(anti_goals.get("premature", 0.30)),
        "success_moderate": float(goals.get("success_moderate", 0.62)),
        "knowledge": float(goals.get("knowledge", 0.52)),
        "novelty": float(goals.get("novelty", 0.46)),
        "success_breakthrough": float(goals.get("success_breakthrough", 0.44)),
        "coherence": float(goals.get("coherence", 0.58)),
        "originality": float(goals.get("originality", 0.48)),
        "social": float(goals.get("social", 0.50)),
        "help_short": float(goals.get("help_short", 0.55)),
        "help_long": float(goals.get("help_long", 0.45)),
        "over_beneficial": float(goals.get("over_beneficial", 0.60)),
        "over_safety": float(goals.get("over_safety", 0.65)),
        "over_honesty": float(goals.get("over_honesty", 0.65)),
    }


def _build_scoring_inputs(
    values: dict[str, float | bool | str],
    goal_values: dict[str, float],
    weights: dict,
    settings: dict[str, float],
    confidence: float,
    low_confidence: float,
    answerability: float,
) -> ScoringInputs:
    return {
        "cx": float(values["cx"]),
        "ambiguity": float(values["ambiguity"]),
        "ux": float(values["ux"]),
        "u": float(values["u"]),
        "res": float(values["res"]),
        "threshold": float(values["threshold"]),
        "threshold_signal": float(values["threshold_signal"]),
        "familiarity": float(values["familiarity"]),
        "familiarity_signal": float(values["familiarity_signal"]),
        "failure_wariness": float(values["failure_wariness"]),
        "failure_signal": float(values["failure_signal"]),
        "securing": float(values["securing"]),
        "approach": float(values["approach"]),
        "arousal": float(values["arousal"]),
        "risk_aversion": float(values["risk_aversion"]),
        "error_tolerance": float(values["error_tolerance"]),
        "creativity": float(values["creativity"]),
        "valence": float(values["valence"]),
        "low_confidence": low_confidence,
        "answerability": answerability,
        "needs_external_evidence": float(values["needs_external_evidence"]),
        "needs_task_plan": float(values["needs_task_plan"]),
        "needs_multi_source_integration": float(
            values["needs_multi_source_integration"]
        ),
        "reflective_intent": float(values["reflective_intent"]),
        "verify_request": bool(values["verify_request"]),
        "anti_hall": goal_values["anti_hall"],
        "anti_redundant": goal_values["anti_redundant"],
        "anti_rabbit_hole": goal_values["anti_rabbit_hole"],
        "anti_premature": goal_values["anti_premature"],
        "coherence": goal_values["coherence"],
        "originality": goal_values["originality"],
        "social": goal_values["social"],
        "help_short": goal_values["help_short"],
        "help_long": goal_values["help_long"],
        "over_beneficial": goal_values["over_beneficial"],
        "over_safety": goal_values["over_safety"],
        "over_honesty": goal_values["over_honesty"],
        "knowledge": goal_values["knowledge"],
        "novelty": goal_values["novelty"],
        "success_breakthrough": goal_values["success_breakthrough"],
        "reflective_think_bonus": settings["reflective_think_bonus"],
        "reflective_search_penalty": settings["reflective_search_penalty"],
        "weights": weights,
    }


def _build_routing_inputs(
    values: dict[str, float | bool | str],
    goal_values: dict[str, float],
    settings: dict[str, float],
    low_confidence: float,
) -> RoutingInputs:
    return {
        "cx": float(values["cx"]),
        "ambiguity": float(values["ambiguity"]),
        "threshold": float(values["threshold"]),
        "threshold_signal": float(values["threshold_signal"]),
        "familiarity_signal": float(values["familiarity_signal"]),
        "failure_signal": float(values["failure_signal"]),
        "urgent_flag": bool(values["urgent_flag"]),
        "intent_type": str(values["intent_type"]),
        "verify_request": bool(values["verify_request"]),
        "reflective_intent": float(values["reflective_intent"]),
        "needs_external_evidence": float(values["needs_external_evidence"]),
        "needs_task_plan": float(values["needs_task_plan"]),
        "needs_multi_source_integration": float(
            values["needs_multi_source_integration"]
        ),
        "low_confidence": low_confidence,
        "failure_wariness": float(values["failure_wariness"]),
        "approach": float(values["approach"]),
        "help_short": goal_values["help_short"],
        "decompose_min_complexity": settings["decompose_min_complexity"],
        "decompose_urgent_min_complexity": settings["decompose_urgent_min_complexity"],
        "decompose_max_ambiguity": settings["decompose_max_ambiguity"],
    }


def _build_style_inputs(
    values: dict[str, float | bool | str],
    *,
    urgency: float,
    complexity: float,
    ambiguity: float,
    threshold: float,
    low_confidence: float,
    resolution: float,
) -> StyleInputs:
    return {
        "urgency": urgency,
        "complexity": complexity,
        "ambiguity": ambiguity,
        "user_expertise": float(values["ux"]),
        "threshold": threshold,
        "failure_wariness": float(values["failure_wariness"]),
        "low_confidence": low_confidence,
        "resolution": resolution,
        "approach": float(values["approach"]),
        "creativity": float(values["creativity"]),
        "risk_aversion": float(values["risk_aversion"]),
        "verify_request": bool(values["verify_request"]),
    }


def _build_step_decision(
    *,
    best_action: str,
    style_modifier: str | None,
    reason: str,
    values: dict[str, float | bool | str],
    goal_values: dict[str, float],
    confidence: float,
    low_confidence: float,
    top_scores: list[tuple[str, float]],
) -> dict:
    return {
        "action": best_action,
        "style_modifier": style_modifier,
        "reason": reason,
        "cold_weight": float(values["cold_weight"]),
        "turn_count": int(values["turn_count"]),
        "urgency": float(values["u"]),
        "resolution": float(values["res"]),
        "user_expertise": float(values["ux"]),
        "threshold": float(values["threshold"]),
        "topic_familiarity": float(values["familiarity"]),
        "failure_wariness": float(values["failure_wariness"]),
        "securing": float(values["securing"]),
        "approach": float(values["approach"]),
        "arousal": float(values["arousal"]),
        "risk_aversion": float(values["risk_aversion"]),
        "error_tolerance": float(values["error_tolerance"]),
        "creativity": float(values["creativity"]),
        "valence": float(values["valence"]),
        "anti_hallucinate": goal_values["anti_hall"],
        "anti_redundant": goal_values["anti_redundant"],
        "anti_rabbit_hole": goal_values["anti_rabbit_hole"],
        "anti_premature": goal_values["anti_premature"],
        "success_moderate": goal_values["success_moderate"],
        "knowledge": goal_values["knowledge"],
        "novelty": goal_values["novelty"],
        "success_breakthrough": goal_values["success_breakthrough"],
        "coherence": goal_values["coherence"],
        "originality": goal_values["originality"],
        "social": goal_values["social"],
        "help_short": goal_values["help_short"],
        "help_long": goal_values["help_long"],
        "over_beneficial": goal_values["over_beneficial"],
        "over_safety": goal_values["over_safety"],
        "over_honesty": goal_values["over_honesty"],
        "confidence": confidence,
        "low_confidence": low_confidence,
        "intent_type": str(values["intent_type"]),
        "reflective_intent": float(values["reflective_intent"]),
        "verify_request": bool(values["verify_request"]),
        "needs_external_evidence": float(values["needs_external_evidence"]),
        "needs_task_plan": float(values["needs_task_plan"]),
        "needs_multi_source_integration": float(
            values["needs_multi_source_integration"]
        ),
        "score_top3": top_scores,
    }


def step(context: dict, state: dict) -> dict:
    goals = state["goals"]
    anti_goals = state.get("anti_goals", DEFAULT_ANTI_GOALS.copy())
    mods = state["modulators"]
    params = state["params"]
    settings = _extract_step_settings(params)

    appraisal = _appraise_modulators(
        context=context, state=state, mods=mods, params=params
    )
    values = _extract_appraisal_values(appraisal)
    cx = float(values["cx"])
    ambiguity = float(values["ambiguity"])
    threshold_signal = float(values["threshold_signal"])
    familiarity_signal = float(values["familiarity_signal"])
    threshold = float(values["threshold"])
    u = float(values["u"])
    res = float(values["res"])
    securing = float(values["securing"])
    familiarity = float(values["familiarity"])
    valence = float(values["valence"])

    confidence = clamp_to_unit_interval(
        0.55 * familiarity + 0.25 * (1.0 - ambiguity) + 0.20 * (1.0 - cx)
    )
    low_confidence = clamp_to_unit_interval(1.0 - confidence)
    answerability = clamp_to_unit_interval(
        (1.0 - ambiguity) * (1.0 - threshold_signal) * familiarity_signal
    )

    weights = _goal_weights(
        goals=goals,
        urgency=u,
        resolution=res,
        complexity=cx,
        threshold=threshold,
        securing=securing,
        low_confidence=low_confidence,
        valence=valence,
    )
    goal_values = _extract_goal_and_anti_values(goals, anti_goals)
    scoring_inputs = _build_scoring_inputs(
        values=values,
        goal_values=goal_values,
        weights=weights,
        settings=settings,
        confidence=confidence,
        low_confidence=low_confidence,
        answerability=answerability,
    )
    scores = _score_actions(scoring_inputs)

    routing_inputs = _build_routing_inputs(
        values=values,
        goal_values=goal_values,
        settings=settings,
        low_confidence=low_confidence,
    )
    scores = _apply_routing_guards(scores, routing_inputs)

    best_action, top_scores = _select_action(
        scores,
        intent_type=str(values["intent_type"]),
        low_confidence=low_confidence,
        threshold=threshold,
        intent_margin=settings["intent_margin"],
    )
    style_modifier = None
    if best_action == "act_respond":
        style_inputs = _build_style_inputs(
            values,
            urgency=u,
            complexity=cx,
            ambiguity=ambiguity,
            threshold=threshold,
            low_confidence=low_confidence,
            resolution=res,
        )
        style_modifier = _determine_respond_style(style_inputs)
    reason = _action_reason(best_action)

    return _build_step_decision(
        best_action=best_action,
        style_modifier=style_modifier,
        reason=reason,
        values=values,
        goal_values=goal_values,
        confidence=confidence,
        low_confidence=low_confidence,
        top_scores=top_scores,
    )

