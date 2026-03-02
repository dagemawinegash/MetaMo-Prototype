from __future__ import annotations


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
            "help_short": 0.55,
            "help_long": 0.45,
            "over_beneficial": 0.60,
            "over_safety": 0.65,
            "over_honesty": 0.65,
        },
        "anti_goals": {
            "hallucinate": 0.35,
            "redundant": 0.30,
            "rabbit_hole": 0.28,
            "premature": 0.30,
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
        "help_short": short_help_base,
        "help_long": float(goals["help_long"])
        * (0.55 + 0.65 * resolution + 0.30 * complexity),
        "over_beneficial": beneficial_base,
        "over_safety": safety_base,
        "over_honesty": honesty_base,
    }


def _blend(prev: float, target: float, alpha: float) -> float:
    return _clamp01((1.0 - alpha) * prev + alpha * target)


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
        target_help_short -= 0.02
    elif decision.get("action") == "act_verify":
        target_accuracy += 0.06
        target_success_moderate += 0.06
        target_knowledge += 0.03
        target_novelty -= 0.04
        target_success_breakthrough += 0.01
        target_coherence += 0.06
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
        target_help_short += 0.08
        target_help_long -= 0.02
        target_over_safety -= 0.02
    elif decision.get("action") == "act_clarify":
        target_accuracy += 0.03
        target_success_moderate += 0.03
        target_knowledge += 0.01
        target_novelty -= 0.01
        target_coherence += 0.05
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
        "help_short": _clamp01(target_help_short),
        "help_long": _clamp01(target_help_long),
        "over_beneficial": _clamp01(target_over_beneficial),
        "over_safety": _clamp01(target_over_safety),
        "over_honesty": _clamp01(target_over_honesty),
    }


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
    return _clamp01(base)


def _redundancy_penalty(
    action: str, cx: float, familiarity: float, urgency: float
) -> float:
    if action == "act_respond":
        return _clamp01(
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
        return _clamp01(0.40 + 0.35 * cx + 0.25 * ambiguity + 0.20 * threshold)
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
        return _clamp01(0.36 + 0.16 * (1.0 - cx) + 0.14 * (1.0 - ambiguity))
    if action == "act_decompose":
        return _clamp01(0.48 + 0.18 * (1.0 - cx) + 0.18 * (1.0 - ambiguity))
    if action == "act_search":
        return _clamp01(0.35 + 0.15 * (1.0 - cx) + 0.15 * (1.0 - ambiguity))
    return {
        "act_respond": 0.10,
        "act_verify": 0.18,
        "act_clarify": 0.14,
        "act_synthesize": 0.22,
    }.get(action, 0.20)


ACTIONS = {
    "act_respond": {
        "efficiency": 1.00,
        "accuracy": lambda cx: _clamp01(1.00 - 1.10 * cx),
        "success_moderate": lambda cx: _clamp01(0.80 - 0.20 * cx),
        "knowledge": lambda cx: _clamp01(0.28 + 0.18 * cx),
        "novelty": lambda cx: _clamp01(0.18 + 0.10 * cx),
        "success_breakthrough": lambda cx: _clamp01(0.18 + 0.12 * cx),
        "coherence": lambda cx: _clamp01(0.72 - 0.10 * cx),
        "help_short": lambda cx: _clamp01(0.95 - 0.20 * cx),
        "help_long": lambda cx: _clamp01(0.25 + 0.20 * cx),
        "over_beneficial": lambda cx: _clamp01(0.45 - 0.15 * cx),
        "over_safety": lambda cx: _clamp01(0.45 - 0.20 * cx),
        "over_honesty": 0.60,
    },
    "act_clarify": {
        "efficiency": 0.65,
        "accuracy": lambda cx: _clamp01(0.55 + 0.25 * cx),
        "success_moderate": 0.72,
        "knowledge": lambda cx: _clamp01(0.45 + 0.20 * cx),
        "novelty": lambda cx: _clamp01(0.28 + 0.12 * cx),
        "success_breakthrough": lambda cx: _clamp01(0.28 + 0.12 * cx),
        "coherence": 0.82,
        "help_short": lambda cx: _clamp01(0.55 + 0.10 * (1.0 - cx)),
        "help_long": lambda cx: _clamp01(0.40 + 0.20 * cx),
        "over_beneficial": 0.85,
        "over_safety": 0.90,
        "over_honesty": 0.95,
    },
    "act_search": {
        "efficiency": 0.25,
        "accuracy": lambda cx: _clamp01(0.30 + 0.90 * cx),
        "success_moderate": lambda cx: _clamp01(0.55 + 0.20 * cx),
        "knowledge": lambda cx: _clamp01(0.68 + 0.22 * cx),
        "novelty": lambda cx: _clamp01(0.58 + 0.18 * cx),
        "success_breakthrough": lambda cx: _clamp01(0.45 + 0.18 * cx),
        "coherence": 0.58,
        "help_short": lambda cx: _clamp01(0.35 + 0.10 * (1.0 - cx)),
        "help_long": lambda cx: _clamp01(0.55 + 0.35 * cx),
        "over_beneficial": 0.72,
        "over_safety": 0.78,
        "over_honesty": 0.82,
    },
    "act_verify": {
        "efficiency": 0.35,
        "accuracy": lambda cx: _clamp01(0.75 + 0.20 * cx),
        "success_moderate": 0.90,
        "knowledge": lambda cx: _clamp01(0.62 + 0.15 * cx),
        "novelty": lambda cx: _clamp01(0.25 + 0.08 * cx),
        "success_breakthrough": lambda cx: _clamp01(0.38 + 0.10 * cx),
        "coherence": 0.86,
        "help_short": lambda cx: _clamp01(0.40 + 0.10 * (1.0 - cx)),
        "help_long": lambda cx: _clamp01(0.50 + 0.20 * cx),
        "over_beneficial": 0.96,
        "over_safety": 0.97,
        "over_honesty": 0.97,
    },
    "act_decompose": {
        "efficiency": 0.45,
        "accuracy": lambda cx: _clamp01(0.55 + 0.35 * cx),
        "success_moderate": lambda cx: _clamp01(0.65 + 0.15 * cx),
        "knowledge": lambda cx: _clamp01(0.72 + 0.20 * cx),
        "novelty": lambda cx: _clamp01(0.62 + 0.18 * cx),
        "success_breakthrough": lambda cx: _clamp01(0.62 + 0.22 * cx),
        "coherence": 0.80,
        "help_short": lambda cx: _clamp01(0.30 + 0.05 * (1.0 - cx)),
        "help_long": lambda cx: _clamp01(0.70 + 0.25 * cx),
        "over_beneficial": 0.70,
        "over_safety": 0.76,
        "over_honesty": 0.80,
    },
    "act_think": {
        "efficiency": 0.40,
        "accuracy": lambda cx: _clamp01(0.60 + 0.25 * cx),
        "success_moderate": lambda cx: _clamp01(0.45 + 0.20 * cx),
        "knowledge": lambda cx: _clamp01(0.66 + 0.18 * cx),
        "novelty": lambda cx: _clamp01(0.70 + 0.18 * cx),
        "success_breakthrough": lambda cx: _clamp01(0.68 + 0.20 * cx),
        "coherence": 0.74,
        "help_short": lambda cx: _clamp01(0.35 + 0.10 * (1.0 - cx)),
        "help_long": lambda cx: _clamp01(0.60 + 0.25 * cx),
        "over_beneficial": 0.78,
        "over_safety": 0.84,
        "over_honesty": 0.90,
    },
    "act_synthesize": {
        "efficiency": 0.30,
        "accuracy": lambda cx: _clamp01(0.74 + 0.12 * cx),
        "success_moderate": 0.82,
        "knowledge": lambda cx: _clamp01(0.78 + 0.16 * cx),
        "novelty": lambda cx: _clamp01(0.56 + 0.12 * cx),
        "success_breakthrough": lambda cx: _clamp01(0.54 + 0.14 * cx),
        "coherence": 0.84,
        "help_short": lambda cx: _clamp01(0.42 + 0.08 * (1.0 - cx)),
        "help_long": lambda cx: _clamp01(0.72 + 0.18 * cx),
        "over_beneficial": 0.90,
        "over_safety": 0.92,
        "over_honesty": 0.95,
    },
}


def step(context: dict, state: dict) -> dict:
    goals = state["goals"]
    anti_goals = state.get(
        "anti_goals",
        {
            "hallucinate": 0.35,
            "redundant": 0.30,
            "rabbit_hole": 0.28,
            "premature": 0.30,
        },
    )
    mods = state["modulators"]
    params = state["params"]
    urgency_alpha = float(params.get("urgency_alpha", 0.60))
    resolution_alpha = float(params.get("resolution_alpha", 0.45))
    expertise_alpha = float(params.get("expertise_alpha", 0.45))
    threshold_alpha = float(params.get("threshold_alpha", 0.40))
    familiarity_alpha = float(params.get("familiarity_alpha", 0.35))
    failure_alpha = float(params.get("failure_alpha", 0.55))
    failure_decay = float(params.get("failure_decay", 0.20))
    securing_alpha = float(params.get("securing_alpha", 0.45))
    approach_alpha = float(params.get("approach_alpha", 0.40))
    arousal_alpha = float(params.get("arousal_alpha", 0.40))
    risk_aversion_alpha = float(params.get("risk_aversion_alpha", 0.45))
    error_tolerance_alpha = float(params.get("error_tolerance_alpha", 0.40))
    creativity_alpha = float(params.get("creativity_alpha", 0.40))
    valence_alpha = float(params.get("valence_alpha", 0.40))
    cold_start_horizon = float(params.get("cold_start_horizon", 2.0))
    cold_start_strength = float(params.get("cold_start_strength", 0.70))
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

    target_u = 1.0 if context.get("urgent") else 0.0
    mods["urgency"] = _clamp01(
        (1.0 - urgency_alpha) * float(mods["urgency"]) + urgency_alpha * target_u
    )

    cx = float(context.get("complexity", 0.3))
    ambiguity = float(context.get("ambiguity", 0.0))
    expertise = float(context.get("expertise", 0.5))
    threshold_signal = float(context.get("threshold", 0.3))
    familiarity_signal = float(context.get("topic_familiarity", 0.5))
    failure_signal = float(context.get("failure_signal", 0.0))
    urgent_flag = bool(context.get("urgent", False))
    intent_type = str(context.get("intent_type", "mixed")).strip().lower()
    verify_request_raw = context.get("verify_request", False)
    verify_request = False
    if isinstance(verify_request_raw, bool):
        verify_request = verify_request_raw
    elif isinstance(verify_request_raw, str):
        verify_request = verify_request_raw.strip().lower() in {"true", "yes", "y", "1"}
    elif isinstance(verify_request_raw, (int, float)):
        verify_request = bool(verify_request_raw)
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

    u = _effective(float(mods["urgency"]), target_u)
    res = _effective(float(mods["resolution"]), cx)
    ux = _effective(float(mods["user_expertise"]), expertise)
    threshold = _effective(float(mods["threshold"]), threshold_signal)
    familiarity = _effective(float(mods["topic_familiarity"]), familiarity_signal)
    failure_wariness = _effective(float(mods["failure_wariness"]), failure_signal)
    securing = _effective(float(mods["securing"]), securing_target)
    approach = _effective(float(mods["approach"]), approach_target)
    arousal = _effective(float(mods["arousal"]), arousal_target)
    risk_aversion = _effective(float(mods["risk_aversion"]), risk_aversion_target)
    error_tolerance = _effective(float(mods["error_tolerance"]), error_tolerance_target)
    creativity = _effective(float(mods["creativity"]), creativity_target)
    valence = _clamp11(
        (1.0 - cold_weight) * float(mods.get("valence", 0.0))
        + cold_weight * valence_signal
    )

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
    help_short = float(goals.get("help_short", 0.55))
    help_long = float(goals.get("help_long", 0.45))
    over_beneficial = float(goals.get("over_beneficial", 0.60))
    over_safety = float(goals.get("over_safety", 0.65))
    over_honesty = float(goals.get("over_honesty", 0.65))

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
            "act_respond": _clamp01(
                0.55 + 0.20 * cx + 0.25 * threshold + 0.20 * ambiguity
            ),
            "act_search": _clamp01(0.35 + 0.20 * threshold),
            "act_verify": 0.08,
            "act_clarify": 0.10,
            "act_decompose": 0.25,
            "act_synthesize": 0.12,
        }.get(action, 0.30)
        honesty_risk = {
            "act_respond": _clamp01(0.40 + 0.30 * low_confidence + 0.15 * ambiguity),
            "act_search": 0.18,
            "act_verify": 0.05,
            "act_clarify": 0.10,
            "act_decompose": 0.16,
            "act_synthesize": 0.08,
        }.get(action, 0.20)

        score -= over_safety * safety_risk * (0.65 + 0.35 * securing)
        score -= over_honesty * honesty_risk * (0.60 + 0.40 * low_confidence)
        beneficial_risk = {
            "act_respond": _clamp01(
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

    decompose_min = (
        decompose_urgent_min_complexity if urgent_flag else decompose_min_complexity
    )
    if (
        cx < decompose_min or ambiguity >= decompose_max_ambiguity
    ) and "act_decompose" in scores:
        scores["act_decompose"] = -1e9
    if "act_decompose" in scores:
        if needs_task_plan < 0.45 and not (
            cx >= 0.78 and ambiguity <= 0.35 and reflective_intent >= 0.75
        ):
            scores["act_decompose"] = -1e9
        elif needs_external_evidence >= 0.75 and needs_task_plan <= 0.55:
            scores["act_decompose"] -= 0.30
        if needs_task_plan >= 0.60:
            scores["act_decompose"] += 0.10
        elif needs_task_plan <= 0.18 and cx < 0.55:
            scores["act_decompose"] -= 0.30

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
            scores["act_synthesize"] = -1e9
        if (
            needs_task_plan >= 0.70
            and needs_task_plan >= needs_multi_source_integration
        ):
            scores["act_synthesize"] -= 0.22
        if needs_external_evidence >= 0.85 and needs_task_plan <= 0.45:
            scores["act_synthesize"] -= 0.15

    # Semantic arbitration among search/decompose/synthesize using continuous context signals.
    if (
        "act_search" in scores
        and "act_decompose" in scores
        and "act_synthesize" in scores
        and scores["act_search"] > -1e8
        and scores["act_decompose"] > -1e8
    ):
        if (
            needs_external_evidence >= 0.70
            and needs_external_evidence >= needs_task_plan + 0.15
            and needs_external_evidence >= needs_multi_source_integration - 0.02
        ):
            scores["act_search"] += 0.26
            scores["act_decompose"] -= 0.26
            if scores["act_synthesize"] > -1e8:
                scores["act_synthesize"] -= 0.12
        elif (
            needs_task_plan >= 0.72
            and needs_task_plan >= needs_external_evidence + 0.18
            and needs_task_plan >= needs_multi_source_integration + 0.12
        ):
            scores["act_decompose"] += 0.18
            scores["act_search"] -= 0.12
            if scores["act_synthesize"] > -1e8:
                scores["act_synthesize"] -= 0.10
        elif (
            scores["act_synthesize"] > -1e8
            and needs_multi_source_integration >= 0.72
            and needs_multi_source_integration >= needs_task_plan + 0.15
        ):
            scores["act_synthesize"] += 0.16
            scores["act_decompose"] -= 0.16

    if (
        "act_search" in scores
        and "act_synthesize" in scores
        and scores["act_search"] > -1e8
        and scores["act_synthesize"] > -1e8
    ):
        if (
            needs_external_evidence >= 0.85
            and needs_multi_source_integration >= 0.75
            and needs_task_plan <= 0.55
        ):
            scores["act_search"] += 0.18
            scores["act_synthesize"] -= 0.18

    # clarify vs verify split
    # very high ambiguity => clarify (missing specifics)
    # medium ambiguity + high risk/low confidence => verify
    if "act_verify" in scores:
        if ambiguity >= 0.85:
            scores["act_verify"] = -1e9
        elif not (
            verify_request
            or (threshold >= 0.55 and low_confidence >= 0.40)
            or failure_wariness >= 0.45
        ):
            scores["act_verify"] = -1e9

    if verify_request and "act_verify" in scores:
        scores["act_verify"] += 0.45
        if "act_synthesize" in scores:
            scores["act_synthesize"] -= 0.35

    # high-complexity research without explicit verify intent should not be pulled into verify
    if (
        not verify_request
        and cx >= 0.70
        and ambiguity <= 0.65
        and intent_type in {"mixed", "reflective"}
        and "act_verify" in scores
    ):
        scores["act_verify"] -= 0.20

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

    # keep simple clear prompts on direct response using current-turn risk signals
    # to avoid over-carrying caution from previous risky turns
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
            scores["act_verify"] = -1e9
        if "act_search" in scores:
            scores["act_search"] = -1e9
        if "act_clarify" in scores:
            scores["act_clarify"] = -1e9
        if "act_think" in scores:
            scores["act_think"] = -1e9
        if "act_respond" in scores:
            scores["act_respond"] += 0.60

    # do not clarify when query is answerable and risk is low
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
            scores["act_clarify"] = -1e9
        if "act_search" in scores:
            scores["act_search"] = -1e9
        if "act_respond" in scores:
            scores["act_respond"] += 0.40

    if "act_think" in scores and not (
        cx >= 0.55
        or ambiguity >= 0.40
        or low_confidence >= 0.45
        or (approach >= 0.62 and cx >= 0.50)
    ):
        scores["act_think"] = -1e9

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
        scores["act_synthesize"] = -1e9

    search_score = float(scores.get("act_search", -1e9))
    think_score = float(scores.get("act_think", -1e9))
    if (
        search_score > -1e8
        and think_score > -1e8
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
    reason = ""
    if best_action == "act_respond":
        reason = "Efficiency prevails."
    elif best_action == "act_search":
        reason = "Accuracy prevails."
    elif best_action == "act_verify":
        reason = "Risk or low confidence requires verification."
    elif best_action == "act_decompose":
        reason = "Complex task benefits from decomposition."
    elif best_action == "act_think":
        reason = "Reflective thinking improves answer quality."
    elif best_action == "act_synthesize":
        reason = "Synthesis best combines complex evidence coherently."
    else:
        reason = "Ambiguity requires clarification."

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
        float(goals.get("success_moderate", 0.62)),
        targets["success_moderate"],
        alpha,
    )
    goals["knowledge"] = _blend(
        float(goals.get("knowledge", 0.52)),
        targets["knowledge"],
        alpha,
    )
    goals["novelty"] = _blend(
        float(goals.get("novelty", 0.46)),
        targets["novelty"],
        alpha,
    )
    goals["success_breakthrough"] = _blend(
        float(goals.get("success_breakthrough", 0.44)),
        targets["success_breakthrough"],
        alpha,
    )
    goals["coherence"] = _blend(
        float(goals.get("coherence", 0.58)),
        targets["coherence"],
        alpha,
    )
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

    state["turn_count"] = int(state.get("turn_count", 0)) + 1

    return state
