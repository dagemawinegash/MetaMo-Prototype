from __future__ import annotations

from config import DEFAULT_ALPHA_PARAMS
from utils import clamp_to_signed_unit_interval, clamp_to_unit_interval

from .constants import _coerce_verify_request


def _extract_appraisal_alpha_params(params: dict) -> dict[str, float]:
    return {
        "urgency_alpha": float(
            params.get("urgency_alpha", DEFAULT_ALPHA_PARAMS["urgency_alpha"])
        ),
        "resolution_alpha": float(
            params.get("resolution_alpha", DEFAULT_ALPHA_PARAMS["resolution_alpha"])
        ),
        "expertise_alpha": float(
            params.get("expertise_alpha", DEFAULT_ALPHA_PARAMS["expertise_alpha"])
        ),
        "threshold_alpha": float(
            params.get("threshold_alpha", DEFAULT_ALPHA_PARAMS["threshold_alpha"])
        ),
        "familiarity_alpha": float(
            params.get("familiarity_alpha", DEFAULT_ALPHA_PARAMS["familiarity_alpha"])
        ),
        "failure_alpha": float(
            params.get("failure_alpha", DEFAULT_ALPHA_PARAMS["failure_alpha"])
        ),
        "failure_decay": float(
            params.get("failure_decay", DEFAULT_ALPHA_PARAMS["failure_decay"])
        ),
        "securing_alpha": float(
            params.get("securing_alpha", DEFAULT_ALPHA_PARAMS["securing_alpha"])
        ),
        "approach_alpha": float(
            params.get("approach_alpha", DEFAULT_ALPHA_PARAMS["approach_alpha"])
        ),
        "arousal_alpha": float(
            params.get("arousal_alpha", DEFAULT_ALPHA_PARAMS["arousal_alpha"])
        ),
        "risk_aversion_alpha": float(
            params.get(
                "risk_aversion_alpha", DEFAULT_ALPHA_PARAMS["risk_aversion_alpha"]
            )
        ),
        "error_tolerance_alpha": float(
            params.get(
                "error_tolerance_alpha", DEFAULT_ALPHA_PARAMS["error_tolerance_alpha"]
            )
        ),
        "creativity_alpha": float(
            params.get("creativity_alpha", DEFAULT_ALPHA_PARAMS["creativity_alpha"])
        ),
        "valence_alpha": float(
            params.get("valence_alpha", DEFAULT_ALPHA_PARAMS["valence_alpha"])
        ),
        "cold_start_horizon": float(params.get("cold_start_horizon", 2.0)),
        "cold_start_strength": float(params.get("cold_start_strength", 0.70)),
    }


def _extract_appraisal_context_signals(context: dict) -> dict[str, float | bool | str]:
    return {
        "cx": float(context.get("complexity", 0.3)),
        "ambiguity": float(context.get("ambiguity", 0.0)),
        "expertise": float(context.get("expertise", 0.5)),
        "threshold_signal": float(context.get("threshold", 0.3)),
        "familiarity_signal": float(context.get("topic_familiarity", 0.5)),
        "failure_signal": float(context.get("failure_signal", 0.0)),
        "urgent_flag": bool(context.get("urgent", False)),
        "intent_type": str(context.get("intent_type", "mixed")).strip().lower(),
        "verify_request": _coerce_verify_request(context.get("verify_request", False)),
        "reflective_intent_raw": context.get("reflective_intent", None),
        "needs_external_evidence": clamp_to_unit_interval(
            float(context.get("needs_external_evidence", 0.3))
        ),
        "needs_task_plan": clamp_to_unit_interval(
            float(context.get("needs_task_plan", 0.2))
        ),
        "needs_multi_source_integration": clamp_to_unit_interval(
            float(context.get("needs_multi_source_integration", 0.3))
        ),
        "valence_signal": clamp_to_signed_unit_interval(
            float(context.get("valence", 0.0))
        ),
    }


def _resolve_reflective_intent(intent_type: str, reflective_intent_raw: object) -> float:
    if reflective_intent_raw is None:
        if intent_type == "reflective":
            return 0.80
        if intent_type == "factual":
            return 0.15
        return 0.50
    return clamp_to_unit_interval(float(reflective_intent_raw))


def _compute_appraisal_targets(
    *,
    cx: float,
    ambiguity: float,
    threshold_signal: float,
    familiarity_signal: float,
    failure_signal: float,
    urgent_flag: bool,
    reflective_intent: float,
    valence_signal: float,
) -> dict[str, float]:
    target_u = 1.0 if urgent_flag else 0.0
    securing_target = clamp_to_unit_interval(
        0.50 * threshold_signal + 0.30 * failure_signal + 0.20 * ambiguity
    )
    approach_target = clamp_to_unit_interval(
        0.45 * cx
        + 0.25 * (1.0 - ambiguity)
        + 0.20 * (1.0 - threshold_signal)
        + 0.10 * (1.0 - failure_signal)
    )
    novelty_signal = clamp_to_unit_interval(
        0.35 * cx
        + 0.35 * (1.0 - familiarity_signal)
        + 0.20 * reflective_intent
        + 0.10 * ambiguity
    )
    arousal_target = clamp_to_unit_interval(
        0.25 + 0.40 * target_u + 0.35 * novelty_signal + 0.20 * cx
    )
    risk_aversion_target = clamp_to_unit_interval(
        0.40 * threshold_signal
        + 0.30 * failure_signal
        + 0.20 * ambiguity
        + 0.10 * (1.0 if urgent_flag else 0.0)
    )
    error_tolerance_target = clamp_to_unit_interval(
        0.45
        + 0.25 * (1.0 - threshold_signal)
        + 0.20 * familiarity_signal
        + 0.15 * (1.0 - failure_signal)
        - 0.20 * ambiguity
        - 0.10 * (1.0 if urgent_flag else 0.0)
    )
    creativity_target = clamp_to_unit_interval(
        0.30
        + 0.30 * (1.0 - familiarity_signal)
        + 0.20 * cx
        + 0.15 * (1.0 - threshold_signal)
        + 0.20 * reflective_intent
        - 0.10 * failure_signal
    )
    valence_target = clamp_to_signed_unit_interval(valence_signal - 0.10 * failure_signal)
    return {
        "target_u": target_u,
        "securing_target": securing_target,
        "approach_target": approach_target,
        "arousal_target": arousal_target,
        "risk_aversion_target": risk_aversion_target,
        "error_tolerance_target": error_tolerance_target,
        "creativity_target": creativity_target,
        "valence_target": valence_target,
    }


def _effective_with_cold_start(smoothed: float, raw_signal: float, cold_weight: float) -> float:
    return clamp_to_unit_interval(
        (1.0 - cold_weight) * smoothed + cold_weight * raw_signal
    )


def _appraise_modulators(
    context: dict, state: dict, mods: dict, params: dict
) -> dict:
    alpha = _extract_appraisal_alpha_params(params)
    signals = _extract_appraisal_context_signals(context)

    cx = float(signals["cx"])
    ambiguity = float(signals["ambiguity"])
    expertise = float(signals["expertise"])
    threshold_signal = float(signals["threshold_signal"])
    familiarity_signal = float(signals["familiarity_signal"])
    failure_signal = float(signals["failure_signal"])
    urgent_flag = bool(signals["urgent_flag"])
    intent_type = str(signals["intent_type"])
    verify_request = bool(signals["verify_request"])
    reflective_intent = _resolve_reflective_intent(
        intent_type, signals["reflective_intent_raw"]
    )
    needs_external_evidence = float(signals["needs_external_evidence"])
    needs_task_plan = float(signals["needs_task_plan"])
    needs_multi_source_integration = float(signals["needs_multi_source_integration"])
    valence_signal = float(signals["valence_signal"])

    targets = _compute_appraisal_targets(
        cx=cx,
        ambiguity=ambiguity,
        threshold_signal=threshold_signal,
        familiarity_signal=familiarity_signal,
        failure_signal=failure_signal,
        urgent_flag=urgent_flag,
        reflective_intent=reflective_intent,
        valence_signal=valence_signal,
    )

    target_u = float(targets["target_u"])
    mods["urgency"] = clamp_to_unit_interval(
        (1.0 - alpha["urgency_alpha"]) * float(mods["urgency"])
        + alpha["urgency_alpha"] * target_u
    )
    mods["resolution"] = clamp_to_unit_interval(
        (1.0 - alpha["resolution_alpha"]) * float(mods.get("resolution", 0.4))
        + alpha["resolution_alpha"] * cx
    )
    mods["user_expertise"] = clamp_to_unit_interval(
        (1.0 - alpha["expertise_alpha"]) * float(mods.get("user_expertise", 0.5))
        + alpha["expertise_alpha"] * expertise
    )
    mods["threshold"] = clamp_to_unit_interval(
        (1.0 - alpha["threshold_alpha"]) * float(mods.get("threshold", 0.3))
        + alpha["threshold_alpha"] * threshold_signal
    )
    mods["topic_familiarity"] = clamp_to_unit_interval(
        (1.0 - alpha["familiarity_alpha"]) * float(mods.get("topic_familiarity", 0.5))
        + alpha["familiarity_alpha"] * familiarity_signal
    )
    mods["failure_wariness"] = clamp_to_unit_interval(
        (1.0 - alpha["failure_decay"]) * float(mods.get("failure_wariness", 0.1))
        + alpha["failure_alpha"] * failure_signal
    )

    securing_target = float(targets["securing_target"])
    mods["securing"] = clamp_to_unit_interval(
        (1.0 - alpha["securing_alpha"]) * float(mods.get("securing", 0.3))
        + alpha["securing_alpha"] * securing_target
    )

    approach_target = float(targets["approach_target"])
    mods["approach"] = clamp_to_unit_interval(
        (1.0 - alpha["approach_alpha"]) * float(mods.get("approach", 0.4))
        + alpha["approach_alpha"] * approach_target
    )

    arousal_target = float(targets["arousal_target"])
    mods["arousal"] = clamp_to_unit_interval(
        (1.0 - alpha["arousal_alpha"]) * float(mods.get("arousal", 0.4))
        + alpha["arousal_alpha"] * arousal_target
    )

    risk_aversion_target = float(targets["risk_aversion_target"])
    mods["risk_aversion"] = clamp_to_unit_interval(
        (1.0 - alpha["risk_aversion_alpha"]) * float(mods.get("risk_aversion", 0.4))
        + alpha["risk_aversion_alpha"] * risk_aversion_target
    )

    error_tolerance_target = float(targets["error_tolerance_target"])
    mods["error_tolerance"] = clamp_to_unit_interval(
        (1.0 - alpha["error_tolerance_alpha"]) * float(mods.get("error_tolerance", 0.45))
        + alpha["error_tolerance_alpha"] * error_tolerance_target
    )

    creativity_target = float(targets["creativity_target"])
    mods["creativity"] = clamp_to_unit_interval(
        (1.0 - alpha["creativity_alpha"]) * float(mods.get("creativity", 0.45))
        + alpha["creativity_alpha"] * creativity_target
    )

    valence_target = float(targets["valence_target"])
    mods["valence"] = clamp_to_signed_unit_interval(
        (1.0 - alpha["valence_alpha"]) * float(mods.get("valence", 0.0))
        + alpha["valence_alpha"] * valence_target
    )

    turn_count = int(state.get("turn_count", 0))
    if alpha["cold_start_horizon"] > 0.0 and turn_count < alpha["cold_start_horizon"]:
        cold_phase = (alpha["cold_start_horizon"] - float(turn_count)) / alpha["cold_start_horizon"]
        cold_weight = clamp_to_unit_interval(alpha["cold_start_strength"] * cold_phase)
    else:
        cold_weight = 0.0

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
        "u": _effective_with_cold_start(float(mods["urgency"]), target_u, cold_weight),
        "res": _effective_with_cold_start(float(mods["resolution"]), cx, cold_weight),
        "ux": _effective_with_cold_start(float(mods["user_expertise"]), expertise, cold_weight),
        "threshold": _effective_with_cold_start(float(mods["threshold"]), threshold_signal, cold_weight),
        "familiarity": _effective_with_cold_start(
            float(mods["topic_familiarity"]), familiarity_signal, cold_weight
        ),
        "failure_wariness": _effective_with_cold_start(
            float(mods["failure_wariness"]), failure_signal, cold_weight
        ),
        "securing": _effective_with_cold_start(float(mods["securing"]), securing_target, cold_weight),
        "approach": _effective_with_cold_start(float(mods["approach"]), approach_target, cold_weight),
        "arousal": _effective_with_cold_start(float(mods["arousal"]), arousal_target, cold_weight),
        "risk_aversion": _effective_with_cold_start(
            float(mods["risk_aversion"]), risk_aversion_target, cold_weight
        ),
        "error_tolerance": _effective_with_cold_start(
            float(mods["error_tolerance"]), error_tolerance_target, cold_weight
        ),
        "creativity": _effective_with_cold_start(
            float(mods["creativity"]), creativity_target, cold_weight
        ),
        "valence": clamp_to_signed_unit_interval(
            (1.0 - cold_weight) * float(mods.get("valence", 0.0))
            + cold_weight * valence_signal
        ),
    }

