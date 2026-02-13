from __future__ import annotations


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def init_state() -> dict:
    return {
        "goals": {"efficiency": 0.60, "accuracy": 0.70},
        "modulators": {"urgency": 0.20},
        "params": {"urgency_alpha": 0.60, "goal_alpha": 0.25},
    }


def _goal_weights(goals: dict, urgency: float, complexity: float) -> dict:
    efficiency_base = float(goals["efficiency"]) * (1.0 - 0.30 * complexity)
    accuracy_base = float(goals["accuracy"]) * (0.60 + 0.80 * complexity)
    return {
        "efficiency": efficiency_base * (0.70 + 0.60 * urgency),
        "accuracy": accuracy_base * (0.90 - 0.50 * urgency),
    }


def _blend(prev: float, target: float, alpha: float) -> float:
    return _clamp01((1.0 - alpha) * prev + alpha * target)


def _goal_targets(context: dict, decision: dict) -> dict:
    cx = float(context.get("complexity", 0.3))
    urgent = bool(context.get("urgent", False))

    target_efficiency = 0.45 + (0.35 if urgent else 0.0) + 0.20 * (1.0 - cx)
    target_accuracy = 0.45 + 0.45 * cx + (0.05 if not urgent else 0.0)

    if decision.get("action") == "act_search":
        target_accuracy += 0.05
    elif decision.get("action") == "act_respond":
        target_efficiency += 0.05

    return {
        "efficiency": _clamp01(target_efficiency),
        "accuracy": _clamp01(target_accuracy),
    }


ACTIONS = {
    "act_respond": {
        "efficiency": 1.00,
        "accuracy": lambda cx: _clamp01(1.00 - 1.10 * cx),
    },
    "act_search": {
        "efficiency": 0.25,
        "accuracy": lambda cx: _clamp01(0.30 + 0.90 * cx),
    },
}


def step(context: dict, state: dict) -> dict:
    goals = state["goals"]
    mods = state["modulators"]
    alpha = float(state["params"].get("urgency_alpha", 0.60))

    target_u = 1.0 if context.get("urgent") else 0.0
    mods["urgency"] = _clamp01(
        (1.0 - alpha) * float(mods["urgency"]) + alpha * target_u
    )

    u = float(mods["urgency"])
    cx = float(context.get("complexity", 0.3))

    weights = _goal_weights(goals=goals, urgency=u, complexity=cx)

    scores: dict[str, float] = {}
    for action, effects in ACTIONS.items():
        score = 0.0
        for goal, weight in weights.items():
            effect = effects.get(goal)
            if effect is None:
                continue
            rel = effect(cx) if callable(effect) else float(effect)
            score += float(weight) * float(rel)
        scores[action] = score

    best_action = max(scores, key=scores.get)
    reason = (
        "Efficiency prevails." if best_action == "act_respond" else "Accuracy prevails."
    )
    return {"action": best_action, "reason": reason, "urgency": u}


def post_update(context: dict, state: dict, decision: dict) -> dict:
    goals = state["goals"]
    alpha = float(state["params"].get("goal_alpha", 0.25))
    targets = _goal_targets(context, decision)

    goals["efficiency"] = _blend(
        float(goals["efficiency"]), targets["efficiency"], alpha
    )
    goals["accuracy"] = _blend(float(goals["accuracy"]), targets["accuracy"], alpha)

    return state
