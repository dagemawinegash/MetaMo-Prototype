from __future__ import annotations

from core.homeostasis import apply_homeostatic_contractivity
from core.state import _anti_goal_targets, _blend, _goal_targets


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

    apply_homeostatic_contractivity(state)

    state["turn_count"] = int(state.get("turn_count", 0)) + 1
    return state

