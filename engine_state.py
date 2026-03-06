from __future__ import annotations

# Constants / baselines
ACTION_BLOCKED_SCORE = -1e9
ACTION_ACTIVE_FLOOR = -1e8

DEFAULT_ANTI_GOALS = {
    "hallucinate": 0.35,
    "redundant": 0.30,
    "rabbit_hole": 0.28,
    "premature": 0.30,
}

DEFAULT_ALPHA_PARAMS = {
    "urgency_alpha": 0.60,
    "resolution_alpha": 0.45,
    "expertise_alpha": 0.45,
    "threshold_alpha": 0.40,
    "familiarity_alpha": 0.35,
    "failure_alpha": 0.55,
    "failure_decay": 0.20,
    "securing_alpha": 0.45,
    "approach_alpha": 0.40,
    "arousal_alpha": 0.40,
    "risk_aversion_alpha": 0.45,
    "error_tolerance_alpha": 0.40,
    "creativity_alpha": 0.40,
    "valence_alpha": 0.40,
}


# Utility helpers
def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _clamp11(value: float) -> float:
    if value < -1.0:
        return -1.0
    if value > 1.0:
        return 1.0
    return value


def _blend(prev: float, target: float, alpha: float) -> float:
    return _clamp01((1.0 - alpha) * prev + alpha * target)


def _coerce_verify_request(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


# State init
def init_state() -> dict:
    return {
        "turn_count": 0,
        "goals": {
            "efficiency": 0.60,
            "accuracy": 0.70,
            "success_moderate": 0.62,
            "knowledge": 0.52,
            "novelty": 0.46,
            "success_breakthrough": 0.44,
            "coherence": 0.58,
            "originality": 0.48,
            "social": 0.50,
            "help_short": 0.55,
            "help_long": 0.45,
            "over_beneficial": 0.60,
            "over_safety": 0.65,
            "over_honesty": 0.65,
        },
        "anti_goals": {
            "hallucinate": DEFAULT_ANTI_GOALS["hallucinate"],
            "redundant": DEFAULT_ANTI_GOALS["redundant"],
            "rabbit_hole": DEFAULT_ANTI_GOALS["rabbit_hole"],
            "premature": DEFAULT_ANTI_GOALS["premature"],
        },
        "modulators": {
            "urgency": 0.20,
            "resolution": 0.40,
            "user_expertise": 0.50,
            "threshold": 0.30,
            "topic_familiarity": 0.50,
            "failure_wariness": 0.10,
            "securing": 0.30,
            "approach": 0.40,
            "arousal": 0.40,
            "risk_aversion": 0.40,
            "error_tolerance": 0.45,
            "creativity": 0.45,
            "valence": 0.00,
        },
        "params": {
            "urgency_alpha": 0.60,
            "resolution_alpha": 0.45,
            "expertise_alpha": 0.45,
            "threshold_alpha": 0.40,
            "familiarity_alpha": 0.35,
            "failure_alpha": 0.55,
            "failure_decay": 0.20,
            "securing_alpha": 0.45,
            "approach_alpha": 0.40,
            "arousal_alpha": 0.40,
            "risk_aversion_alpha": 0.45,
            "error_tolerance_alpha": 0.40,
            "creativity_alpha": 0.40,
            "valence_alpha": 0.40,
            "goal_alpha": 0.18,
            "anti_goal_alpha": 0.16,
            "cold_start_horizon": 2.0,
            "cold_start_strength": 0.70,
            "decompose_min_complexity": 0.60,
            "decompose_urgent_min_complexity": 0.70,
            "decompose_max_ambiguity": 0.70,
            "reflective_think_bonus": 0.14,
            "reflective_search_penalty": 0.10,
            "intent_margin": 0.12,
        },
    }


# Goal weighting / targets
def _goal_weights(
    goals: dict,
    urgency: float,
    resolution: float,
    complexity: float,
    threshold: float,
    securing: float,
    low_confidence: float,
    valence: float,
) -> dict:
    efficiency_base = float(goals["efficiency"]) * (1.0 - 0.30 * complexity)
    accuracy_base = float(goals["accuracy"]) * (0.60 + 0.80 * complexity)
    short_help_base = float(goals.get("help_short", 0.55)) * (
        0.65 + 0.55 * urgency + 0.25 * (1.0 - complexity)
    )
    success_moderate_base = float(goals.get("success_moderate", 0.62)) * (
        0.65
        + 0.35 * threshold
        + 0.35 * securing
        + 0.30 * low_confidence
        + 0.20 * complexity
        - 0.20 * urgency
    )
    knowledge_base = float(goals.get("knowledge", 0.52)) * (
        0.55 + 0.55 * complexity + 0.30 * resolution - 0.20 * urgency
    )
    novelty_base = float(goals.get("novelty", 0.46)) * (
        0.45
        + 0.45 * complexity
        + 0.35 * resolution
        + 0.25 * low_confidence
        - 0.20 * threshold
        - 0.15 * urgency
    )
    breakthrough_base = float(goals.get("success_breakthrough", 0.44)) * (
        0.45
        + 0.45 * complexity
        + 0.35 * low_confidence
        + 0.20 * threshold
        - 0.15 * urgency
    )
    coherence_base = float(goals.get("coherence", 0.58)) * (
        0.60
        + 0.30 * resolution
        + 0.25 * (1.0 - low_confidence)
        + 0.20 * threshold
        + 0.10 * (1.0 - urgency)
        + 0.08 * _clamp01((valence + 1.0) * 0.5)
    )
    originality_base = float(goals.get("originality", 0.48)) * (
        0.45
        + 0.40 * complexity
        + 0.30 * resolution
        + 0.20 * _clamp01((valence + 1.0) * 0.5)
        - 0.15 * urgency
        - 0.10 * threshold
    )
    social_base = float(goals.get("social", 0.50)) * (
        0.55
        + 0.35 * (1.0 - low_confidence)
        + 0.20 * urgency
        + 0.10 * _clamp01((valence + 1.0) * 0.5)
    )
    beneficial_base = float(goals.get("over_beneficial", 0.60)) * (
        0.60 + 0.45 * threshold + 0.40 * securing + 0.30 * low_confidence
    )
    safety_base = float(goals.get("over_safety", 0.65)) * (
        0.60 + 0.45 * complexity + 0.55 * threshold + 0.50 * securing
    )
    honesty_base = float(goals.get("over_honesty", 0.65)) * (
        0.60 + 0.60 * low_confidence + 0.30 * threshold
    )
    return {
        "efficiency": efficiency_base * (0.70 + 0.60 * urgency),
        "accuracy": accuracy_base * (0.70 - 0.40 * urgency + 0.50 * resolution),
        "success_moderate": success_moderate_base,
        "knowledge": knowledge_base,
        "novelty": novelty_base,
        "success_breakthrough": breakthrough_base,
        "coherence": coherence_base,
        "originality": originality_base,
        "social": social_base,
        "help_short": short_help_base,
        "help_long": float(goals["help_long"])
        * (0.55 + 0.65 * resolution + 0.30 * complexity),
        "over_beneficial": beneficial_base,
        "over_safety": safety_base,
        "over_honesty": honesty_base,
    }


def _goal_targets(context: dict, decision: dict) -> dict:
    cx = float(context.get("complexity", 0.3))
    urgent = bool(context.get("urgent", False))
    ambiguity = float(context.get("ambiguity", 0.0))

    target_efficiency = 0.45 + (0.35 if urgent else 0.0) + 0.20 * (1.0 - cx)
    target_accuracy = (
        0.45 + 0.45 * cx + 0.10 * ambiguity + (0.05 if not urgent else 0.0)
    )
    target_success_moderate = (
        0.45
        + 0.30 * cx
        + 0.25 * ambiguity
        + 0.25 * float(context.get("threshold", 0.3))
        + 0.20 * float(context.get("failure_signal", 0.0))
        - (0.08 if urgent else 0.0)
    )
    target_knowledge = (
        0.35
        + 0.50 * cx
        + 0.20 * ambiguity
        + 0.10 * float(context.get("expertise", 0.5))
    )
    target_novelty = (
        0.30
        + 0.35 * cx
        + 0.25 * (1.0 - float(context.get("topic_familiarity", 0.5)))
        + 0.20 * float(context.get("reflective_intent", 0.5))
        + 0.10 * ambiguity
        - (0.05 if urgent else 0.0)
    )
    target_success_breakthrough = (
        0.30
        + 0.45 * cx
        + 0.25 * ambiguity
        + 0.20 * float(context.get("reflective_intent", 0.5))
        - (0.08 if urgent else 0.0)
    )
    target_coherence = (
        0.45
        + 0.25 * (1.0 - ambiguity)
        + 0.25 * (1.0 - float(context.get("failure_signal", 0.0)))
        + 0.20 * float(context.get("threshold", 0.3))
        + (0.10 if not urgent else 0.0)
    )
    target_originality = (
        0.30
        + 0.40 * cx
        + 0.25 * float(context.get("reflective_intent", 0.5))
        + 0.20 * (1.0 - float(context.get("topic_familiarity", 0.5)))
        + 0.10 * ambiguity
        - (0.08 if urgent else 0.0)
    )
    target_social = (
        0.35
        + 0.30 * ambiguity
        + 0.20 * float(context.get("failure_signal", 0.0))
        + 0.20 * (1.0 - float(context.get("expertise", 0.5)))
        + (0.10 if urgent else 0.0)
    )
    target_help_short = (
        0.35 + 0.35 * (1.0 - cx) + 0.20 * (1.0 - ambiguity) + (0.10 if urgent else 0.0)
    )
    target_help_long = 0.30 + 0.55 * cx + 0.15 * (1.0 - ambiguity)
    target_over_beneficial = (
        0.45
        + 0.35 * float(context.get("threshold", 0.3))
        + 0.20 * float(context.get("failure_signal", 0.0))
    )
    target_over_safety = 0.45 + 0.40 * float(context.get("threshold", 0.3))
    target_over_honesty = (
        0.45 + 0.35 * ambiguity + 0.20 * float(context.get("failure_signal", 0.0))
    )

    if decision.get("action") == "act_search":
        target_accuracy += 0.05
        target_success_moderate += 0.01
        target_knowledge += 0.06
        target_novelty += 0.06
        target_success_breakthrough += 0.04
        target_coherence += 0.01
        target_originality += 0.03
        target_social += 0.01
        target_help_short -= 0.02
    elif decision.get("action") == "act_verify":
        target_accuracy += 0.06
        target_success_moderate += 0.06
        target_knowledge += 0.03
        target_novelty -= 0.04
        target_success_breakthrough += 0.01
        target_coherence += 0.06
        target_originality -= 0.03
        target_social += 0.07
        target_help_short -= 0.03
        target_help_long += 0.02
        target_over_beneficial += 0.05
        target_over_safety += 0.05
        target_over_honesty += 0.06
    elif decision.get("action") == "act_think":
        target_accuracy += 0.04
        target_success_moderate -= 0.02
        target_knowledge += 0.05
        target_novelty += 0.08
        target_success_breakthrough += 0.06
        target_coherence += 0.02
        target_originality += 0.07
        target_social += 0.01
        target_help_short -= 0.02
        target_help_long += 0.04
        target_over_beneficial += 0.03
        target_over_honesty += 0.04
    elif decision.get("action") == "act_respond":
        target_efficiency += 0.05
        target_success_moderate += 0.02
        target_knowledge -= 0.04
        target_novelty -= 0.04
        target_success_breakthrough -= 0.04
        target_coherence += 0.02
        target_originality -= 0.04
        target_social += 0.06
        target_help_short += 0.08
        target_help_long -= 0.02
        target_over_safety -= 0.02
    elif decision.get("action") == "act_clarify":
        target_accuracy += 0.03
        target_success_moderate += 0.03
        target_knowledge += 0.01
        target_novelty -= 0.01
        target_coherence += 0.05
        target_originality -= 0.02
        target_social += 0.08
        target_help_short += 0.03
        target_over_beneficial += 0.03
        target_over_honesty += 0.04
    elif decision.get("action") == "act_decompose":
        target_accuracy += 0.04
        target_success_moderate += 0.04
        target_knowledge += 0.07
        target_novelty += 0.05
        target_success_breakthrough += 0.08
        target_coherence += 0.04
        target_originality += 0.05
        target_social += 0.04
        target_help_short -= 0.04
        target_efficiency += 0.01
        target_help_long += 0.06
        target_over_beneficial += 0.02
    elif decision.get("action") == "act_synthesize":
        target_accuracy += 0.05
        target_success_moderate += 0.05
        target_knowledge += 0.08
        target_novelty += 0.04
        target_success_breakthrough += 0.05
        target_coherence += 0.05
        target_originality += 0.08
        target_social += 0.05
        target_help_short -= 0.03
        target_help_long += 0.07
        target_over_beneficial += 0.03
        target_over_safety += 0.03
        target_over_honesty += 0.04

    return {
        "efficiency": _clamp01(target_efficiency),
        "accuracy": _clamp01(target_accuracy),
        "success_moderate": _clamp01(target_success_moderate),
        "knowledge": _clamp01(target_knowledge),
        "novelty": _clamp01(target_novelty),
        "success_breakthrough": _clamp01(target_success_breakthrough),
        "coherence": _clamp01(target_coherence),
        "originality": _clamp01(target_originality),
        "social": _clamp01(target_social),
        "help_short": _clamp01(target_help_short),
        "help_long": _clamp01(target_help_long),
        "over_beneficial": _clamp01(target_over_beneficial),
        "over_safety": _clamp01(target_over_safety),
        "over_honesty": _clamp01(target_over_honesty),
    }


# Anti-goal dynamics
def _anti_goal_targets(context: dict, goals: dict) -> dict:
    threshold = float(context.get("threshold", 0.3))
    familiarity = float(context.get("topic_familiarity", 0.5))
    failure_signal = float(context.get("failure_signal", 0.0))
    urgency = 1.0 if bool(context.get("urgent", False)) else 0.0
    complexity = float(context.get("complexity", 0.3))
    ambiguity = float(context.get("ambiguity", 0.0))
    expertise = float(context.get("expertise", 0.5))
    help_short_now = float(goals.get("help_short", 0.55))

    hallucinate_target = (
        0.15 + 0.55 * threshold + 0.25 * (1.0 - familiarity) + 0.20 * failure_signal
    )
    redundant_target = (
        0.22
        + 0.45 * help_short_now
        + 0.18 * expertise
        + 0.15 * (1.0 - ambiguity)
        + 0.05 * urgency
    )
    premature_target = (
        0.20
        + 0.45 * complexity
        + 0.30 * ambiguity
        + 0.20 * threshold
        - 0.20 * help_short_now
        + 0.08 * (1.0 - familiarity)
    )
    rabbit_hole_target = (
        0.18
        + 0.40 * help_short_now
        + 0.25 * urgency
        + 0.20 * (1.0 - complexity)
        + 0.20 * (1.0 - ambiguity)
        + 0.08 * expertise
    )

    return {
        "hallucinate": _clamp01(hallucinate_target),
        "redundant": _clamp01(redundant_target),
        "rabbit_hole": _clamp01(rabbit_hole_target),
        "premature": _clamp01(premature_target),
    }


# Appraisal / modulator updates
def _appraise_modulators(context: dict, state: dict, mods: dict, params: dict) -> dict:
    urgency_alpha = float(
        params.get("urgency_alpha", DEFAULT_ALPHA_PARAMS["urgency_alpha"])
    )
    resolution_alpha = float(
        params.get("resolution_alpha", DEFAULT_ALPHA_PARAMS["resolution_alpha"])
    )
    expertise_alpha = float(
        params.get("expertise_alpha", DEFAULT_ALPHA_PARAMS["expertise_alpha"])
    )
    threshold_alpha = float(
        params.get("threshold_alpha", DEFAULT_ALPHA_PARAMS["threshold_alpha"])
    )
    familiarity_alpha = float(
        params.get("familiarity_alpha", DEFAULT_ALPHA_PARAMS["familiarity_alpha"])
    )
    failure_alpha = float(
        params.get("failure_alpha", DEFAULT_ALPHA_PARAMS["failure_alpha"])
    )
    failure_decay = float(
        params.get("failure_decay", DEFAULT_ALPHA_PARAMS["failure_decay"])
    )
    securing_alpha = float(
        params.get("securing_alpha", DEFAULT_ALPHA_PARAMS["securing_alpha"])
    )
    approach_alpha = float(
        params.get("approach_alpha", DEFAULT_ALPHA_PARAMS["approach_alpha"])
    )
    arousal_alpha = float(
        params.get("arousal_alpha", DEFAULT_ALPHA_PARAMS["arousal_alpha"])
    )
    risk_aversion_alpha = float(
        params.get("risk_aversion_alpha", DEFAULT_ALPHA_PARAMS["risk_aversion_alpha"])
    )
    error_tolerance_alpha = float(
        params.get(
            "error_tolerance_alpha", DEFAULT_ALPHA_PARAMS["error_tolerance_alpha"]
        )
    )
    creativity_alpha = float(
        params.get("creativity_alpha", DEFAULT_ALPHA_PARAMS["creativity_alpha"])
    )
    valence_alpha = float(
        params.get("valence_alpha", DEFAULT_ALPHA_PARAMS["valence_alpha"])
    )
    cold_start_horizon = float(params.get("cold_start_horizon", 2.0))
    cold_start_strength = float(params.get("cold_start_strength", 0.70))

    cx = float(context.get("complexity", 0.3))
    ambiguity = float(context.get("ambiguity", 0.0))
    expertise = float(context.get("expertise", 0.5))
    threshold_signal = float(context.get("threshold", 0.3))
    familiarity_signal = float(context.get("topic_familiarity", 0.5))
    failure_signal = float(context.get("failure_signal", 0.0))
    urgent_flag = bool(context.get("urgent", False))
    intent_type = str(context.get("intent_type", "mixed")).strip().lower()
    verify_request = _coerce_verify_request(context.get("verify_request", False))
    reflective_intent_raw = context.get("reflective_intent", None)
    if reflective_intent_raw is None:
        reflective_intent = (
            0.80
            if intent_type == "reflective"
            else 0.15 if intent_type == "factual" else 0.50
        )
    else:
        reflective_intent = _clamp01(float(reflective_intent_raw))
    needs_external_evidence = _clamp01(
        float(context.get("needs_external_evidence", 0.3))
    )
    needs_task_plan = _clamp01(float(context.get("needs_task_plan", 0.2)))
    needs_multi_source_integration = _clamp01(
        float(context.get("needs_multi_source_integration", 0.3))
    )
    valence_signal = _clamp11(float(context.get("valence", 0.0)))

    target_u = 1.0 if urgent_flag else 0.0
    mods["urgency"] = _clamp01(
        (1.0 - urgency_alpha) * float(mods["urgency"]) + urgency_alpha * target_u
    )
    mods["resolution"] = _clamp01(
        (1.0 - resolution_alpha) * float(mods.get("resolution", 0.4))
        + resolution_alpha * cx
    )
    mods["user_expertise"] = _clamp01(
        (1.0 - expertise_alpha) * float(mods.get("user_expertise", 0.5))
        + expertise_alpha * expertise
    )
    mods["threshold"] = _clamp01(
        (1.0 - threshold_alpha) * float(mods.get("threshold", 0.3))
        + threshold_alpha * threshold_signal
    )
    mods["topic_familiarity"] = _clamp01(
        (1.0 - familiarity_alpha) * float(mods.get("topic_familiarity", 0.5))
        + familiarity_alpha * familiarity_signal
    )
    mods["failure_wariness"] = _clamp01(
        (1.0 - failure_decay) * float(mods.get("failure_wariness", 0.1))
        + failure_alpha * failure_signal
    )

    securing_target = _clamp01(
        0.50 * threshold_signal + 0.30 * failure_signal + 0.20 * ambiguity
    )
    mods["securing"] = _clamp01(
        (1.0 - securing_alpha) * float(mods.get("securing", 0.3))
        + securing_alpha * securing_target
    )

    approach_target = _clamp01(
        0.45 * cx
        + 0.25 * (1.0 - ambiguity)
        + 0.20 * (1.0 - threshold_signal)
        + 0.10 * (1.0 - failure_signal)
    )
    mods["approach"] = _clamp01(
        (1.0 - approach_alpha) * float(mods.get("approach", 0.4))
        + approach_alpha * approach_target
    )

    novelty_signal = _clamp01(
        0.35 * cx
        + 0.35 * (1.0 - familiarity_signal)
        + 0.20 * reflective_intent
        + 0.10 * ambiguity
    )
    arousal_target = _clamp01(
        0.25 + 0.40 * target_u + 0.35 * novelty_signal + 0.20 * cx
    )
    mods["arousal"] = _clamp01(
        (1.0 - arousal_alpha) * float(mods.get("arousal", 0.4))
        + arousal_alpha * arousal_target
    )

    risk_aversion_target = _clamp01(
        0.40 * threshold_signal
        + 0.30 * failure_signal
        + 0.20 * ambiguity
        + 0.10 * (1.0 if urgent_flag else 0.0)
    )
    mods["risk_aversion"] = _clamp01(
        (1.0 - risk_aversion_alpha) * float(mods.get("risk_aversion", 0.4))
        + risk_aversion_alpha * risk_aversion_target
    )

    error_tolerance_target = _clamp01(
        0.45
        + 0.25 * (1.0 - threshold_signal)
        + 0.20 * familiarity_signal
        + 0.15 * (1.0 - failure_signal)
        - 0.20 * ambiguity
        - 0.10 * (1.0 if urgent_flag else 0.0)
    )
    mods["error_tolerance"] = _clamp01(
        (1.0 - error_tolerance_alpha) * float(mods.get("error_tolerance", 0.45))
        + error_tolerance_alpha * error_tolerance_target
    )

    creativity_target = _clamp01(
        0.30
        + 0.30 * (1.0 - familiarity_signal)
        + 0.20 * cx
        + 0.15 * (1.0 - threshold_signal)
        + 0.20 * reflective_intent
        - 0.10 * failure_signal
    )
    mods["creativity"] = _clamp01(
        (1.0 - creativity_alpha) * float(mods.get("creativity", 0.45))
        + creativity_alpha * creativity_target
    )

    valence_target = _clamp11(valence_signal - 0.10 * failure_signal)
    mods["valence"] = _clamp11(
        (1.0 - valence_alpha) * float(mods.get("valence", 0.0))
        + valence_alpha * valence_target
    )

    turn_count = int(state.get("turn_count", 0))
    if cold_start_horizon > 0.0 and turn_count < cold_start_horizon:
        cold_phase = (cold_start_horizon - float(turn_count)) / cold_start_horizon
        cold_weight = _clamp01(cold_start_strength * cold_phase)
    else:
        cold_weight = 0.0

    def _effective(smoothed: float, raw_signal: float) -> float:
        return _clamp01((1.0 - cold_weight) * smoothed + cold_weight * raw_signal)

    return {
        "turn_count": turn_count,
        "cold_weight": cold_weight,
        "cx": cx,
        "ambiguity": ambiguity,
        "expertise": expertise,
        "threshold_signal": threshold_signal,
        "familiarity_signal": familiarity_signal,
        "failure_signal": failure_signal,
        "urgent_flag": urgent_flag,
        "intent_type": intent_type,
        "verify_request": verify_request,
        "reflective_intent": reflective_intent,
        "needs_external_evidence": needs_external_evidence,
        "needs_task_plan": needs_task_plan,
        "needs_multi_source_integration": needs_multi_source_integration,
        "u": _effective(float(mods["urgency"]), target_u),
        "res": _effective(float(mods["resolution"]), cx),
        "ux": _effective(float(mods["user_expertise"]), expertise),
        "threshold": _effective(float(mods["threshold"]), threshold_signal),
        "familiarity": _effective(float(mods["topic_familiarity"]), familiarity_signal),
        "failure_wariness": _effective(float(mods["failure_wariness"]), failure_signal),
        "securing": _effective(float(mods["securing"]), securing_target),
        "approach": _effective(float(mods["approach"]), approach_target),
        "arousal": _effective(float(mods["arousal"]), arousal_target),
        "risk_aversion": _effective(float(mods["risk_aversion"]), risk_aversion_target),
        "error_tolerance": _effective(
            float(mods["error_tolerance"]), error_tolerance_target
        ),
        "creativity": _effective(float(mods["creativity"]), creativity_target),
        "valence": _clamp11(
            (1.0 - cold_weight) * float(mods.get("valence", 0.0))
            + cold_weight * valence_signal
        ),
    }
