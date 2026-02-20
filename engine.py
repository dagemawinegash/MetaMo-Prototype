from __future__ import annotations


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def init_state() -> dict:
    return {
        "goals": {
            "efficiency": 0.60,
            "accuracy": 0.70,
            "help_long": 0.45,
            "over_safety": 0.65,
            "over_honesty": 0.65,
        },
        "anti_goals": {"hallucinate": 0.35},
        "modulators": {
            "urgency": 0.20,
            "resolution": 0.40,
            "user_expertise": 0.50,
            "threshold": 0.30,
            "topic_familiarity": 0.50,
            "failure_wariness": 0.10,
            "securing": 0.30,
            "approach": 0.40,
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
            "goal_alpha": 0.25,
            "anti_goal_alpha": 0.20,
            "decompose_min_complexity": 0.80,
            "decompose_urgent_min_complexity": 0.90,
            "decompose_max_ambiguity": 0.70,
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
) -> dict:
    efficiency_base = float(goals["efficiency"]) * (1.0 - 0.30 * complexity)
    accuracy_base = float(goals["accuracy"]) * (0.60 + 0.80 * complexity)
    safety_base = float(goals.get("over_safety", 0.65)) * (
        0.60 + 0.45 * complexity + 0.55 * threshold + 0.50 * securing
    )
    honesty_base = float(goals.get("over_honesty", 0.65)) * (
        0.60 + 0.60 * low_confidence + 0.30 * threshold
    )
    return {
        "efficiency": efficiency_base * (0.70 + 0.60 * urgency),
        "accuracy": accuracy_base * (0.70 - 0.40 * urgency + 0.50 * resolution),
        "help_long": float(goals["help_long"])
        * (0.55 + 0.65 * resolution + 0.30 * complexity),
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
    target_help_long = 0.30 + 0.55 * cx + 0.15 * (1.0 - ambiguity)
    target_over_safety = 0.45 + 0.40 * float(context.get("threshold", 0.3))
    target_over_honesty = (
        0.45 + 0.35 * ambiguity + 0.20 * float(context.get("failure_signal", 0.0))
    )

    if decision.get("action") == "act_search":
        target_accuracy += 0.05
    elif decision.get("action") == "act_verify":
        target_accuracy += 0.06
        target_help_long += 0.02
        target_over_safety += 0.05
        target_over_honesty += 0.06
    elif decision.get("action") == "act_think":
        target_accuracy += 0.04
        target_help_long += 0.04
        target_over_honesty += 0.04
    elif decision.get("action") == "act_respond":
        target_efficiency += 0.05
        target_over_safety -= 0.02
    elif decision.get("action") == "act_clarify":
        target_accuracy += 0.03
        target_over_honesty += 0.04
    elif decision.get("action") == "act_decompose":
        target_accuracy += 0.04
        target_efficiency += 0.01
        target_help_long += 0.06

    return {
        "efficiency": _clamp01(target_efficiency),
        "accuracy": _clamp01(target_accuracy),
        "help_long": _clamp01(target_help_long),
        "over_safety": _clamp01(target_over_safety),
        "over_honesty": _clamp01(target_over_honesty),
    }


def _anti_goal_target(context: dict) -> float:
    threshold = float(context.get("threshold", 0.3))
    familiarity = float(context.get("topic_familiarity", 0.5))
    failure_signal = float(context.get("failure_signal", 0.0))
    target = (
        0.15 + 0.55 * threshold + 0.25 * (1.0 - familiarity) + 0.20 * failure_signal
    )
    return _clamp01(target)


def _hallucination_penalty(action: str, cx: float, ambiguity: float) -> float:
    base = {
        "act_respond": 0.90,
        "act_search": 0.30,
        "act_verify": 0.12,
        "act_clarify": 0.15,
        "act_decompose": 0.40,
        "act_think": 0.22,
    }.get(action, 0.50)
    if action == "act_respond":
        base += 0.25 * cx + 0.20 * ambiguity
    elif action == "act_search":
        base += 0.10 * ambiguity
    elif action == "act_decompose":
        base += 0.10 * cx
    return _clamp01(base)


ACTIONS = {
    "act_respond": {
        "efficiency": 1.00,
        "accuracy": lambda cx: _clamp01(1.00 - 1.10 * cx),
        "help_long": lambda cx: _clamp01(0.25 + 0.20 * cx),
        "over_safety": lambda cx: _clamp01(0.45 - 0.20 * cx),
        "over_honesty": 0.60,
    },
    "act_clarify": {
        "efficiency": 0.65,
        "accuracy": lambda cx: _clamp01(0.55 + 0.25 * cx),
        "help_long": lambda cx: _clamp01(0.40 + 0.20 * cx),
        "over_safety": 0.90,
        "over_honesty": 0.95,
    },
    "act_search": {
        "efficiency": 0.25,
        "accuracy": lambda cx: _clamp01(0.30 + 0.90 * cx),
        "help_long": lambda cx: _clamp01(0.55 + 0.35 * cx),
        "over_safety": 0.78,
        "over_honesty": 0.82,
    },
    "act_verify": {
        "efficiency": 0.35,
        "accuracy": lambda cx: _clamp01(0.75 + 0.20 * cx),
        "help_long": lambda cx: _clamp01(0.50 + 0.20 * cx),
        "over_safety": 0.97,
        "over_honesty": 0.97,
    },
    "act_decompose": {
        "efficiency": 0.45,
        "accuracy": lambda cx: _clamp01(0.55 + 0.35 * cx),
        "help_long": lambda cx: _clamp01(0.70 + 0.25 * cx),
        "over_safety": 0.76,
        "over_honesty": 0.80,
    },
    "act_think": {
        "efficiency": 0.40,
        "accuracy": lambda cx: _clamp01(0.60 + 0.25 * cx),
        "help_long": lambda cx: _clamp01(0.60 + 0.25 * cx),
        "over_safety": 0.84,
        "over_honesty": 0.90,
    },
}


def step(context: dict, state: dict) -> dict:
    goals = state["goals"]
    anti_goals = state.get("anti_goals", {"hallucinate": 0.35})
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
    decompose_min_complexity = float(params.get("decompose_min_complexity", 0.80))
    decompose_urgent_min_complexity = float(
        params.get("decompose_urgent_min_complexity", 0.90)
    )
    decompose_max_ambiguity = float(params.get("decompose_max_ambiguity", 0.70))

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

    u = float(mods["urgency"])
    res = float(mods["resolution"])
    ux = float(mods["user_expertise"])
    threshold = float(mods["threshold"])
    familiarity = float(mods["topic_familiarity"])
    failure_wariness = float(mods["failure_wariness"])
    securing = float(mods["securing"])
    approach = float(mods["approach"])

    confidence = _clamp01(
        0.55 * familiarity + 0.25 * (1.0 - ambiguity) + 0.20 * (1.0 - cx)
    )
    low_confidence = _clamp01(1.0 - confidence)

    weights = _goal_weights(
        goals=goals,
        urgency=u,
        resolution=res,
        complexity=cx,
        threshold=threshold,
        securing=securing,
        low_confidence=low_confidence,
    )
    anti_hall = float(anti_goals.get("hallucinate", 0.35))
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
        elif action == "act_respond":
            score += 0.35 * u + 0.25 * (1.0 - ambiguity) + 0.15 * ux - 0.20 * cx
            score += 0.20 * familiarity - 0.35 * threshold - 0.30 * failure_wariness
            score -= 0.35 * securing + 0.20 * low_confidence
        elif action == "act_search":
            score += 0.35 * cx + 0.20 * res - 0.15 * u
            score += (
                0.35 * threshold + 0.35 * (1.0 - familiarity) + 0.30 * failure_wariness
            )
            score += 0.15 * securing
        elif action == "act_verify":
            score += 0.65 * threshold + 0.75 * low_confidence + 0.35 * failure_wariness
            score += 0.15 * cx - 0.20 * u - 0.10 * ambiguity
            score += 0.30 * securing
        elif action == "act_decompose":
            score += 0.45 * cx + 0.45 * res + 0.20 * (1.0 - ambiguity) - 0.15 * u
            score -= 0.25 * ambiguity
            if cx >= 0.75 and ambiguity <= 0.45:
                score += 0.45
            if cx < 0.45:
                score -= 0.35
            score += 0.10 * approach
        elif action == "act_think":
            score += 0.35 * cx + 0.25 * ambiguity + 0.35 * approach
            score += 0.10 * low_confidence + 0.10 * (1.0 - u)
            score -= 0.10 * threshold

        score -= anti_hall * _hallucination_penalty(action, cx=cx, ambiguity=ambiguity)

        safety_risk = {
            "act_respond": _clamp01(
                0.55 + 0.20 * cx + 0.25 * threshold + 0.20 * ambiguity
            ),
            "act_search": _clamp01(0.35 + 0.20 * threshold),
            "act_verify": 0.08,
            "act_clarify": 0.10,
            "act_decompose": 0.25,
        }.get(action, 0.30)
        honesty_risk = {
            "act_respond": _clamp01(0.40 + 0.30 * low_confidence + 0.15 * ambiguity),
            "act_search": 0.18,
            "act_verify": 0.05,
            "act_clarify": 0.10,
            "act_decompose": 0.16,
        }.get(action, 0.20)

        score -= over_safety * safety_risk * (0.65 + 0.35 * securing)
        score -= over_honesty * honesty_risk * (0.60 + 0.40 * low_confidence)

        scores[action] = score

    decompose_min = (
        decompose_urgent_min_complexity if urgent_flag else decompose_min_complexity
    )
    if (
        cx < decompose_min or ambiguity >= decompose_max_ambiguity
    ) and "act_decompose" in scores:
        scores["act_decompose"] = -1e9

    # clarify vs verify split
    # very high ambiguity => clarify (missing specifics)
    # medium ambiguity + high risk/low confidence => verify
    if "act_verify" in scores:
        if ambiguity >= 0.85:
            scores["act_verify"] = -1e9
        elif not (
            threshold >= 0.45 or low_confidence >= 0.45 or failure_wariness >= 0.35
        ):
            scores["act_verify"] = -1e9

    # keep simple clear prompts on direct response using current-turn risk signals
    # to avoid over-carrying caution from previous risky turns
    if (
        cx <= 0.30
        and ambiguity <= 0.30
        and threshold_signal <= 0.25
        and failure_signal <= 0.25
        and familiarity_signal >= 0.70
        and low_confidence <= 0.35
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

    if "act_think" in scores and not (
        cx >= 0.55
        or ambiguity >= 0.40
        or low_confidence >= 0.45
        or (approach >= 0.62 and cx >= 0.50)
    ):
        scores["act_think"] = -1e9

    best_action = max(scores, key=scores.get)
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
    else:
        reason = "Ambiguity requires clarification."

    return {
        "action": best_action,
        "reason": reason,
        "urgency": u,
        "resolution": res,
        "user_expertise": ux,
        "threshold": threshold,
        "topic_familiarity": familiarity,
        "failure_wariness": failure_wariness,
        "securing": securing,
        "approach": approach,
        "anti_hallucinate": anti_hall,
        "over_safety": over_safety,
        "over_honesty": over_honesty,
        "confidence": confidence,
        "low_confidence": low_confidence,
    }


def post_update(context: dict, state: dict, decision: dict) -> dict:
    goals = state["goals"]
    anti_goals = state.get("anti_goals")
    alpha = float(state["params"].get("goal_alpha", 0.25))
    anti_alpha = float(state["params"].get("anti_goal_alpha", 0.20))
    targets = _goal_targets(context, decision)

    goals["efficiency"] = _blend(
        float(goals["efficiency"]), targets["efficiency"], alpha
    )
    goals["accuracy"] = _blend(float(goals["accuracy"]), targets["accuracy"], alpha)
    goals["help_long"] = _blend(
        float(goals.get("help_long", 0.45)), targets["help_long"], alpha
    )
    goals["over_safety"] = _blend(
        float(goals.get("over_safety", 0.65)), targets["over_safety"], alpha
    )
    goals["over_honesty"] = _blend(
        float(goals.get("over_honesty", 0.65)), targets["over_honesty"], alpha
    )

    if anti_goals is not None:
        anti_goals["hallucinate"] = _blend(
            float(anti_goals.get("hallucinate", 0.35)),
            _anti_goal_target(context),
            anti_alpha,
        )

    return state
