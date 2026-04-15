from __future__ import annotations


CONTEXT_PARSER_SYSTEM_PROMPT = (
    "Return JSON only (no markdown). "
    'Schema: {"urgent": boolean, "complexity": number, "ambiguity": number, "expertise": number, "threshold": number, "topic_familiarity": number, "failure_signal": number, "intent_type": string, "reflective_intent": number, "verify_request": boolean, "needs_external_evidence": number, "needs_task_plan": number, "needs_multi_source_integration": number, "valence": number}. '
    "Rules: complexity, ambiguity, expertise, threshold, topic_familiarity, failure_signal are each 0..1. "
    "Rules: valence is in [-1,1], where -1 is strongly negative/frustrated tone, +1 is strongly positive/satisfied tone, and 0 is neutral. "
    "Rules: intent_type must be one of reflective|factual|mixed. "
    "Rules: reflective_intent is 0..1 and measures how much deliberate internal reasoning is likely beneficial before final answer. "
    "Rules: verify_request is true only if user explicitly asks to verify/check/fact-check a claim before answering. "
    "Rules: needs_external_evidence, needs_task_plan, needs_multi_source_integration are each 0..1. "
    "Interpretation: needs_external_evidence is high when answering likely requires fresh/source-backed evidence gathering beyond internal memory. "
    "Interpretation: needs_task_plan is high when the user asks for an ordered plan, breakdown, roadmap, or stepwise execution structure. "
    "Interpretation: needs_multi_source_integration is high when the user asks to synthesize/compare/conflict-resolve across multiple viewpoints or sources. "
    "Interpretation: expertise 0 means novice user language, 1 means expert-level user language."
    "Interpretation: threshold is risk/safety sensitivity (higher means more caution needed). "
    "Interpretation: topic_familiarity is how likely the assistant is to already know this topic well (higher means more familiar). "
    "Interpretation: failure_signal is high when the user indicates previous answer/correction problems."
)


def get_context_parser_system_prompt() -> str:
    return CONTEXT_PARSER_SYSTEM_PROMPT

