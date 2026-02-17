from __future__ import annotations


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def init_state() -> dict:
    return {
        "goals": {"efficiency": 0.60, "accuracy": 0.70, "help_long": 0.45},
        "anti_goals": {"hallucinate": 0.35},
        "modulators": {
            "urgency": 0.20,
            "resolution": 0.40,
            "user_expertise": 0.50,
            "threshold": 0.30,
            "topic_familiarity": 0.50,
            "failure_wariness": 0.10,
        },
        "params": {
            "urgency_alpha": 0.60,
            "resolution_alpha": 0.45,
            "expertise_alpha": 0.45,
            "threshold_alpha": 0.40,
            "familiarity_alpha": 0.35,
            "failure_alpha": 0.55,
            "failure_decay": 0.20,
            "goal_alpha": 0.25,
            "anti_goal_alpha": 0.20,
            "decompose_min_complexity": 0.80,
            "decompose_urgent_min_complexity": 0.90,
            "decompose_max_ambiguity": 0.70,
        },
    }


def _goal_weights(
    goals: dict, urgency: float, resolution: float, complexity: float
) -> dict:
    efficiency_base = float(goals["efficiency"]) * (1.0 - 0.30 * complexity)
    accuracy_base = float(goals["accuracy"]) * (0.60 + 0.80 * complexity)
    return {
        "efficiency": efficiency_base * (0.70 + 0.60 * urgency),
        "accuracy": accuracy_base * (0.70 - 0.40 * urgency + 0.50 * resolution),
        "help_long": float(goals["help_long"])
        * (0.55 + 0.65 * resolution + 0.30 * complexity),
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

    if decision.get("action") == "act_search":
        target_accuracy += 0.05
    elif decision.get("action") == "act_respond":
        target_efficiency += 0.05
    elif decision.get("action") == "act_clarify":
        target_accuracy += 0.03
    elif decision.get("action") == "act_decompose":
        target_accuracy += 0.04
        target_efficiency += 0.01
        target_help_long += 0.06

    return {
        "efficiency": _clamp01(target_efficiency),
        "accuracy": _clamp01(target_accuracy),
        "help_long": _clamp01(target_help_long),
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
        "act_clarify": 0.15,
        "act_decompose": 0.40,
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
    },
    "act_clarify": {
        "efficiency": 0.65,
        "accuracy": lambda cx: _clamp01(0.55 + 0.25 * cx),
        "help_long": lambda cx: _clamp01(0.40 + 0.20 * cx),
    },
    "act_search": {
        "efficiency": 0.25,
        "accuracy": lambda cx: _clamp01(0.30 + 0.90 * cx),
        "help_long": lambda cx: _clamp01(0.55 + 0.35 * cx),
    },
    "act_decompose": {
        "efficiency": 0.45,
        "accuracy": lambda cx: _clamp01(0.55 + 0.35 * cx),
        "help_long": lambda cx: _clamp01(0.70 + 0.25 * cx),
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

    u = float(mods["urgency"])
    res = float(mods["resolution"])
    ux = float(mods["user_expertise"])
    threshold = float(mods["threshold"])
    familiarity = float(mods["topic_familiarity"])
    failure_wariness = float(mods["failure_wariness"])

    weights = _goal_weights(goals=goals, urgency=u, resolution=res, complexity=cx)
    anti_hall = float(anti_goals.get("hallucinate", 0.35))

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
        elif action == "act_respond":
            score += 0.35 * u + 0.25 * (1.0 - ambiguity) + 0.15 * ux - 0.20 * cx
            score += 0.20 * familiarity - 0.35 * threshold - 0.30 * failure_wariness
        elif action == "act_search":
            score += 0.35 * cx + 0.20 * res - 0.15 * u
            score += (
                0.35 * threshold + 0.35 * (1.0 - familiarity) + 0.30 * failure_wariness
            )
        elif action == "act_decompose":
            score += 0.45 * cx + 0.45 * res + 0.20 * (1.0 - ambiguity) - 0.15 * u
            score -= 0.25 * ambiguity
            if cx < 0.45:
                score -= 0.35

        score -= anti_hall * _hallucination_penalty(action, cx=cx, ambiguity=ambiguity)

        scores[action] = score

    decompose_min = (
        decompose_urgent_min_complexity if urgent_flag else decompose_min_complexity
    )
    if (
        cx < decompose_min or ambiguity >= decompose_max_ambiguity
    ) and "act_decompose" in scores:
        scores["act_decompose"] = -1e9

    best_action = max(scores, key=scores.get)
    reason = ""
    if best_action == "act_respond":
        reason = "Efficiency prevails."
    elif best_action == "act_search":
        reason = "Accuracy prevails."
    elif best_action == "act_decompose":
        reason = "Complex task benefits from decomposition."
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
        "anti_hallucinate": anti_hall,
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

    if anti_goals is not None:
        anti_goals["hallucinate"] = _blend(
            float(anti_goals.get("hallucinate", 0.35)),
            _anti_goal_target(context),
            anti_alpha,
        )

    return state
