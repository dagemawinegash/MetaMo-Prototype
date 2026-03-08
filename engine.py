from __future__ import annotations

from engine_routing import _apply_routing_guards, _select_action
from engine_scoring import _action_reason, _score_actions
from engine_state import (
    DEFAULT_ANTI_GOALS,
    _anti_goal_targets,
    _appraise_modulators,
    _blend,
    _clamp01,
    _goal_targets,
    _goal_weights,
    init_state,
)
from homeostasis import apply_homeostatic_contractivity


# Decision orchestration
def step(context: dict, state: dict) -> dict:
    goals = state["goals"]
    anti_goals = state.get("anti_goals", DEFAULT_ANTI_GOALS.copy())
    mods = state["modulators"]
    params = state["params"]
    decompose_min_complexity = float(params.get("decompose_min_complexity", 0.60))
    decompose_urgent_min_complexity = float(
        params.get("decompose_urgent_min_complexity", 0.70)
    )
    decompose_max_ambiguity = float(params.get("decompose_max_ambiguity", 0.70))
    reflective_think_bonus = float(params.get("reflective_think_bonus", 0.14))
    reflective_search_penalty = float(params.get("reflective_search_penalty", 0.10))
    intent_margin = float(
        params.get("intent_margin", params.get("think_search_tie_margin", 0.12))
    )

    appraisal = _appraise_modulators(
        context=context, state=state, mods=mods, params=params
    )
    turn_count = int(appraisal["turn_count"])
    cold_weight = float(appraisal["cold_weight"])
    cx = float(appraisal["cx"])
    ambiguity = float(appraisal["ambiguity"])
    threshold_signal = float(appraisal["threshold_signal"])
    familiarity_signal = float(appraisal["familiarity_signal"])
    failure_signal = float(appraisal["failure_signal"])
    urgent_flag = bool(appraisal["urgent_flag"])
    intent_type = str(appraisal["intent_type"])
    verify_request = bool(appraisal["verify_request"])
    reflective_intent = float(appraisal["reflective_intent"])
    needs_external_evidence = float(appraisal["needs_external_evidence"])
    needs_task_plan = float(appraisal["needs_task_plan"])
    needs_multi_source_integration = float(appraisal["needs_multi_source_integration"])
    u = float(appraisal["u"])
    res = float(appraisal["res"])
    ux = float(appraisal["ux"])
    threshold = float(appraisal["threshold"])
    familiarity = float(appraisal["familiarity"])
    failure_wariness = float(appraisal["failure_wariness"])
    securing = float(appraisal["securing"])
    approach = float(appraisal["approach"])
    arousal = float(appraisal["arousal"])
    risk_aversion = float(appraisal["risk_aversion"])
    error_tolerance = float(appraisal["error_tolerance"])
    creativity = float(appraisal["creativity"])
    valence = float(appraisal["valence"])

    confidence = _clamp01(
        0.55 * familiarity + 0.25 * (1.0 - ambiguity) + 0.20 * (1.0 - cx)
    )
    low_confidence = _clamp01(1.0 - confidence)
    answerability = _clamp01(
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
    anti_hall = float(anti_goals.get("hallucinate", 0.35))
    anti_redundant = float(anti_goals.get("redundant", 0.30))
    anti_rabbit_hole = float(anti_goals.get("rabbit_hole", 0.28))
    anti_premature = float(anti_goals.get("premature", 0.30))
    success_moderate = float(goals.get("success_moderate", 0.62))
    knowledge = float(goals.get("knowledge", 0.52))
    novelty = float(goals.get("novelty", 0.46))
    success_breakthrough = float(goals.get("success_breakthrough", 0.44))
    coherence = float(goals.get("coherence", 0.58))
    originality = float(goals.get("originality", 0.48))
    social = float(goals.get("social", 0.50))
    help_short = float(goals.get("help_short", 0.55))
    help_long = float(goals.get("help_long", 0.45))
    over_beneficial = float(goals.get("over_beneficial", 0.60))
    over_safety = float(goals.get("over_safety", 0.65))
    over_honesty = float(goals.get("over_honesty", 0.65))

    scores = _score_actions(
        cx=cx,
        ambiguity=ambiguity,
        ux=ux,
        u=u,
        res=res,
        threshold=threshold,
        threshold_signal=threshold_signal,
        familiarity=familiarity,
        familiarity_signal=familiarity_signal,
        failure_wariness=failure_wariness,
        failure_signal=failure_signal,
        securing=securing,
        approach=approach,
        arousal=arousal,
        risk_aversion=risk_aversion,
        error_tolerance=error_tolerance,
        creativity=creativity,
        valence=valence,
        low_confidence=low_confidence,
        answerability=answerability,
        needs_external_evidence=needs_external_evidence,
        needs_task_plan=needs_task_plan,
        needs_multi_source_integration=needs_multi_source_integration,
        reflective_intent=reflective_intent,
        verify_request=verify_request,
        anti_hall=anti_hall,
        anti_redundant=anti_redundant,
        anti_rabbit_hole=anti_rabbit_hole,
        anti_premature=anti_premature,
        coherence=coherence,
        originality=originality,
        social=social,
        help_short=help_short,
        help_long=help_long,
        over_beneficial=over_beneficial,
        over_safety=over_safety,
        over_honesty=over_honesty,
        knowledge=knowledge,
        novelty=novelty,
        success_breakthrough=success_breakthrough,
        reflective_think_bonus=reflective_think_bonus,
        reflective_search_penalty=reflective_search_penalty,
        weights=weights,
    )
    scores = _apply_routing_guards(
        scores,
        cx=cx,
        ambiguity=ambiguity,
        threshold=threshold,
        threshold_signal=threshold_signal,
        familiarity_signal=familiarity_signal,
        failure_signal=failure_signal,
        urgent_flag=urgent_flag,
        intent_type=intent_type,
        verify_request=verify_request,
        reflective_intent=reflective_intent,
        needs_external_evidence=needs_external_evidence,
        needs_task_plan=needs_task_plan,
        needs_multi_source_integration=needs_multi_source_integration,
        low_confidence=low_confidence,
        failure_wariness=failure_wariness,
        approach=approach,
        help_short=help_short,
        decompose_min_complexity=decompose_min_complexity,
        decompose_urgent_min_complexity=decompose_urgent_min_complexity,
        decompose_max_ambiguity=decompose_max_ambiguity,
    )

    best_action, top_scores = _select_action(
        scores,
        intent_type=intent_type,
        low_confidence=low_confidence,
        threshold=threshold,
        intent_margin=intent_margin,
    )
    reason = _action_reason(best_action)

    return {
        "action": best_action,
        "reason": reason,
        "cold_weight": cold_weight,
        "turn_count": turn_count,
        "urgency": u,
        "resolution": res,
        "user_expertise": ux,
        "threshold": threshold,
        "topic_familiarity": familiarity,
        "failure_wariness": failure_wariness,
        "securing": securing,
        "approach": approach,
        "arousal": arousal,
        "risk_aversion": risk_aversion,
        "error_tolerance": error_tolerance,
        "creativity": creativity,
        "valence": valence,
        "anti_hallucinate": anti_hall,
        "anti_redundant": anti_redundant,
        "anti_rabbit_hole": anti_rabbit_hole,
        "anti_premature": anti_premature,
        "success_moderate": success_moderate,
        "knowledge": knowledge,
        "novelty": novelty,
        "success_breakthrough": success_breakthrough,
        "coherence": coherence,
        "originality": originality,
        "social": social,
        "help_short": help_short,
        "help_long": help_long,
        "over_beneficial": over_beneficial,
        "over_safety": over_safety,
        "over_honesty": over_honesty,
        "confidence": confidence,
        "low_confidence": low_confidence,
        "intent_type": intent_type,
        "reflective_intent": reflective_intent,
        "verify_request": verify_request,
        "needs_external_evidence": needs_external_evidence,
        "needs_task_plan": needs_task_plan,
        "needs_multi_source_integration": needs_multi_source_integration,
        "score_top3": top_scores,
    }


# Post-decision state updates
def post_update(context: dict, state: dict, decision: dict) -> dict:
    goals = state["goals"]
    anti_goals = state.get("anti_goals")
    alpha = float(state["params"].get("goal_alpha", 0.18))
    anti_alpha = float(state["params"].get("anti_goal_alpha", 0.16))
    targets = _goal_targets(context, decision)

    goals["efficiency"] = _blend(
        float(goals["efficiency"]), targets["efficiency"], alpha
    )
    goals["accuracy"] = _blend(float(goals["accuracy"]), targets["accuracy"], alpha)
    goals["success_moderate"] = _blend(
        float(goals.get("success_moderate", 0.62)), targets["success_moderate"], alpha
    )
    goals["knowledge"] = _blend(
        float(goals.get("knowledge", 0.52)), targets["knowledge"], alpha
    )
    goals["novelty"] = _blend(
        float(goals.get("novelty", 0.46)), targets["novelty"], alpha
    )
    goals["success_breakthrough"] = _blend(
        float(goals.get("success_breakthrough", 0.44)),
        targets["success_breakthrough"],
        alpha,
    )
    goals["coherence"] = _blend(
        float(goals.get("coherence", 0.58)), targets["coherence"], alpha
    )
    goals["originality"] = _blend(
        float(goals.get("originality", 0.48)), targets["originality"], alpha
    )
    goals["social"] = _blend(float(goals.get("social", 0.50)), targets["social"], alpha)
    goals["help_short"] = _blend(
        float(goals.get("help_short", 0.55)), targets["help_short"], alpha
    )
    goals["help_long"] = _blend(
        float(goals.get("help_long", 0.45)), targets["help_long"], alpha
    )
    goals["over_beneficial"] = _blend(
        float(goals.get("over_beneficial", 0.60)), targets["over_beneficial"], alpha
    )
    goals["over_safety"] = _blend(
        float(goals.get("over_safety", 0.65)), targets["over_safety"], alpha
    )
    goals["over_honesty"] = _blend(
        float(goals.get("over_honesty", 0.65)), targets["over_honesty"], alpha
    )

    if anti_goals is not None:
        anti_targets = _anti_goal_targets(context, goals)
        anti_goals["hallucinate"] = _blend(
            float(anti_goals.get("hallucinate", 0.35)),
            float(anti_targets.get("hallucinate", 0.35)),
            anti_alpha,
        )
        anti_goals["redundant"] = _blend(
            float(anti_goals.get("redundant", 0.30)),
            float(anti_targets.get("redundant", 0.30)),
            anti_alpha,
        )
        anti_goals["rabbit_hole"] = _blend(
            float(anti_goals.get("rabbit_hole", 0.28)),
            float(anti_targets.get("rabbit_hole", 0.28)),
            anti_alpha,
        )
        anti_goals["premature"] = _blend(
            float(anti_goals.get("premature", 0.30)),
            float(anti_targets.get("premature", 0.30)),
            anti_alpha,
        )

    # Optional phase-1 contractive update near homeostatic boundaries.
    apply_homeostatic_contractivity(state)

    state["turn_count"] = int(state.get("turn_count", 0)) + 1
    return state
