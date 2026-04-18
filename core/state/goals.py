from __future__ import annotations

from utils import clamp_to_unit_interval


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
        + 0.08 * clamp_to_unit_interval((valence + 1.0) * 0.5)
    )
    originality_base = float(goals.get("originality", 0.48)) * (
        0.45
        + 0.40 * complexity
        + 0.30 * resolution
        + 0.20 * clamp_to_unit_interval((valence + 1.0) * 0.5)
        - 0.15 * urgency
        - 0.10 * threshold
    )
    social_base = float(goals.get("social", 0.50)) * (
        0.55
        + 0.35 * (1.0 - low_confidence)
        + 0.20 * urgency
        + 0.10 * clamp_to_unit_interval((valence + 1.0) * 0.5)
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
        "efficiency": clamp_to_unit_interval(target_efficiency),
        "accuracy": clamp_to_unit_interval(target_accuracy),
        "success_moderate": clamp_to_unit_interval(target_success_moderate),
        "knowledge": clamp_to_unit_interval(target_knowledge),
        "novelty": clamp_to_unit_interval(target_novelty),
        "success_breakthrough": clamp_to_unit_interval(target_success_breakthrough),
        "coherence": clamp_to_unit_interval(target_coherence),
        "originality": clamp_to_unit_interval(target_originality),
        "social": clamp_to_unit_interval(target_social),
        "help_short": clamp_to_unit_interval(target_help_short),
        "help_long": clamp_to_unit_interval(target_help_long),
        "over_beneficial": clamp_to_unit_interval(target_over_beneficial),
        "over_safety": clamp_to_unit_interval(target_over_safety),
        "over_honesty": clamp_to_unit_interval(target_over_honesty),
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
        "hallucinate": clamp_to_unit_interval(hallucinate_target),
        "redundant": clamp_to_unit_interval(redundant_target),
        "rabbit_hole": clamp_to_unit_interval(rabbit_hole_target),
        "premature": clamp_to_unit_interval(premature_target),
    }

