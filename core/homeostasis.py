from __future__ import annotations

from utils import clamp_to_unit_interval


# Homeostatic scope
OVERGOAL_KEYS = ("over_beneficial", "over_safety", "over_honesty")
ANTI_GOAL_KEYS = ("hallucinate", "redundant", "rabbit_hole", "premature")
GOAL_KEYS = (
    "accuracy",
    "coherence",
    "efficiency",
    "originality",
    "social",
    "help_short",
    "help_long",
    "knowledge",
    "novelty",
    "success_moderate",
    "success_breakthrough",
)
MODULATOR_KEYS = (
    "threshold",
    "arousal",
    "securing",
    "risk_aversion",
    "failure_wariness",
    "topic_familiarity",
    "resolution",
    "user_expertise",
)

GOAL_DEFAULT_BOUNDS = (0.0, 1.0)

MODULATOR_BOUNDS = {
    "threshold": (0.2, 0.95),
    "arousal": (0.1, 0.9),
    "securing": (0.0, 1.0),
    "risk_aversion": (0.0, 1.0),
    "failure_wariness": (0.0, 1.0),
    "topic_familiarity": (0.0, 1.0),
    "resolution": (0.0, 1.0),
    "user_expertise": (0.0, 1.0),
}

DEFAULT_CENTERS = {
    "over_beneficial": 0.60,
    "over_safety": 0.65,
    "over_honesty": 0.65,
    "accuracy": 0.70,
    "coherence": 0.58,
    "efficiency": 0.60,
    "originality": 0.48,
    "social": 0.50,
    "help_short": 0.55,
    "help_long": 0.45,
    "knowledge": 0.52,
    "novelty": 0.46,
    "success_moderate": 0.62,
    "success_breakthrough": 0.44,
    "threshold": 0.30,
    "arousal": 0.40,
    "securing": 0.30,
    "risk_aversion": 0.40,
    "failure_wariness": 0.10,
    "topic_familiarity": 0.50,
    "resolution": 0.40,
    "user_expertise": 0.50,
    "hallucinate": 0.35,
    "redundant": 0.30,
    "rabbit_hole": 0.28,
    "premature": 0.30,
}


def _clamp_range(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _near_boundary(value: float, lo: float, hi: float, eta: float) -> bool:
    return value <= (lo + eta) or value >= (hi - eta)


def _apply_scope_contractivity(
    container: dict,
    keys: tuple[str, ...],
    bounds: tuple[float, float] | dict[str, tuple[float, float]],
    eta: float,
    alpha_near: float,
    trigger_prefix: str,
    trigger_keys: list[str],
) -> None:
    for key in keys:
        if key not in container:
            continue
        if isinstance(bounds, dict):
            lo, hi = bounds[key]
        else:
            lo, hi = bounds
        current = float(container.get(key, DEFAULT_CENTERS[key]))
        if _near_boundary(current, lo, hi, eta):
            center = float(DEFAULT_CENTERS[key])
            updated = (1.0 - alpha_near) * current + alpha_near * center
            container[key] = _clamp_range(updated, lo, hi)
            trigger_keys.append(f"{trigger_prefix}.{key}")
        else:
            container[key] = _clamp_range(current, lo, hi)


def apply_homeostatic_contractivity(state: dict) -> dict:
    # apply homeostatic contractivity to selected state variables
    params = state.get("params", {})
    enabled = bool(params.get("enable_homeostasis", False))
    if not enabled:
        debug = {
            "enabled": False,
            "mode": "disabled",
            "trigger_keys": [],
            "trigger_count": 0,
        }
        state["homeostasis_debug"] = debug
        return debug

    goals = state.get("goals", {})
    modulators = state.get("modulators", {})
    anti_goals = state.get("anti_goals", {})

    theta_safe = clamp_to_unit_interval(float(params.get("homeostasis_theta_safe", 0.55)))
    eta = clamp_to_unit_interval(float(params.get("homeostasis_eta", 0.05)))
    alpha_near = clamp_to_unit_interval(float(params.get("homeostasis_alpha_near", 0.10)))

    trigger_keys: list[str] = []

    scope_specs = [
        (goals, GOAL_KEYS, GOAL_DEFAULT_BOUNDS, "goals"),
        (goals, OVERGOAL_KEYS, (theta_safe, 1.0), "goals"),
        (anti_goals, ANTI_GOAL_KEYS, GOAL_DEFAULT_BOUNDS, "anti_goals"),
        (modulators, MODULATOR_KEYS, MODULATOR_BOUNDS, "modulators"),
    ]
    for container, keys, bounds, trigger_prefix in scope_specs:
        _apply_scope_contractivity(
            container=container,
            keys=keys,
            bounds=bounds,
            eta=eta,
            alpha_near=alpha_near,
            trigger_prefix=trigger_prefix,
            trigger_keys=trigger_keys,
        )

    debug = {
        "enabled": True,
        "mode": "near_boundary" if trigger_keys else "interior",
        "trigger_keys": trigger_keys,
        "trigger_count": len(trigger_keys),
    }
    state["homeostasis_debug"] = debug
    return debug
