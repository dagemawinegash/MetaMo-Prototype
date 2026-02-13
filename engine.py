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
        "params": {"urgency_alpha": 0.60},
    }


def _goal_weights(goals: dict, urgency: float, complexity: float) -> dict:
    efficiency_base = float(goals["efficiency"]) * (1.0 - 0.30 * complexity)
    accuracy_base = float(goals["accuracy"]) * (0.60 + 0.80 * complexity)
    return {
        "efficiency": efficiency_base * (0.70 + 0.60 * urgency),
        "accuracy": accuracy_base * (0.90 - 0.50 * urgency),
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
