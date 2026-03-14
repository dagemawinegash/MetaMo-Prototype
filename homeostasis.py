from __future__ import annotations

from engine_state import _clamp01


# Homeostatic scope
OVERGOAL_KEYS = ("over_beneficial", "over_safety", "over_honesty")
MODULATOR_KEYS = (
    "threshold",
    "arousal",
    "securing",
    "risk_aversion",
    "failure_wariness",
)

MODULATOR_BOUNDS = {
    "threshold": (0.2, 0.95),
    "arousal": (0.1, 0.9),
    "securing": (0.0, 1.0),
    "risk_aversion": (0.0, 1.0),
    "failure_wariness": (0.0, 1.0),
}

DEFAULT_CENTERS = {
    "over_beneficial": 0.60,
    "over_safety": 0.65,
    "over_honesty": 0.65,
    "threshold": 0.30,
    "arousal": 0.40,
    "securing": 0.30,
    "risk_aversion": 0.40,
    "failure_wariness": 0.10,
}


def _clamp_range(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _near_boundary(value: float, lo: float, hi: float, eta: float) -> bool:
    return value <= (lo + eta) or value >= (hi - eta)


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

    theta_safe = _clamp01(float(params.get("homeostasis_theta_safe", 0.55)))
    eta = _clamp01(float(params.get("homeostasis_eta", 0.05)))
    alpha_near = _clamp01(float(params.get("homeostasis_alpha_near", 0.10)))

    trigger_keys: list[str] = []

    # Overgoals: bounded by [theta_safe, 1.0]
    for key in OVERGOAL_KEYS:
        if key not in goals:
            continue
        lo, hi = theta_safe, 1.0
        current = float(goals.get(key, DEFAULT_CENTERS[key]))
        if _near_boundary(current, lo, hi, eta):
            center = float(DEFAULT_CENTERS[key])
            updated = (1.0 - alpha_near) * current + alpha_near * center
            goals[key] = _clamp_range(updated, lo, hi)
            trigger_keys.append(f"goals.{key}")
        else:
            goals[key] = _clamp_range(current, lo, hi)

    # Selected modulators with explicit bounds from the paper
    for key in MODULATOR_KEYS:
        if key not in modulators:
            continue
        lo, hi = MODULATOR_BOUNDS[key]
        current = float(modulators.get(key, DEFAULT_CENTERS[key]))
        if _near_boundary(current, lo, hi, eta):
            center = float(DEFAULT_CENTERS[key])
            updated = (1.0 - alpha_near) * current + alpha_near * center
            modulators[key] = _clamp_range(updated, lo, hi)
            trigger_keys.append(f"modulators.{key}")
        else:
            modulators[key] = _clamp_range(current, lo, hi)

    debug = {
        "enabled": True,
        "mode": "near_boundary" if trigger_keys else "interior",
        "trigger_keys": trigger_keys,
        "trigger_count": len(trigger_keys),
    }
    state["homeostasis_debug"] = debug
    return debug
