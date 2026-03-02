from __future__ import annotations

import json
import os
import re
import importlib
import time
from typing import Any

from dotenv import load_dotenv


def _get_provider() -> str:
    provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    if provider not in {"gemini", "openai"}:
        raise RuntimeError("Unsupported LLM_PROVIDER. Use 'gemini' or 'openai'.")
    return provider


def _get_model(provider: str) -> str:
    if provider == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    return os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


def parse_context(
    query: str,
    model: str | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    active_provider = (provider or _get_provider()).strip().lower()
    active_model = model or _get_model(active_provider)

    if active_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing (check .env)")
    else:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is missing (check .env)")

    last_error = ""
    for attempt in range(3):
        if active_provider == "openai":
            parsed = _parse_with_openai(
                query=query,
                api_key=api_key,
                model=active_model,
            )
        else:
            parsed = _parse_with_gemini(
                query=query,
                api_key=api_key,
                model=active_model,
            )

        if parsed is not None:
            return parsed

        last_error = f"parse_attempt_{attempt + 1}_failed"
        if attempt < 2:
            time.sleep(0.35 * (attempt + 1))

    raise RuntimeError(
        f"{active_provider} parsing failed (no valid JSON returned) after 3 attempts; last_error={last_error}"
    )


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _clamp11(value: float) -> float:
    if value < -1.0:
        return -1.0
    if value > 1.0:
        return 1.0
    return value


def _calibrate_action_signals(
    *,
    needs_external_evidence: float,
    needs_task_plan: float,
    needs_multi_source_integration: float,
    ambiguity: float,
    intent_type: str,
    reflective_intent: float,
) -> tuple[float, float, float]:
    evid = _clamp01(needs_external_evidence)
    plan = _clamp01(needs_task_plan)
    multi = _clamp01(needs_multi_source_integration)
    amb = _clamp01(ambiguity)
    refl = _clamp01(reflective_intent)
    intent = (
        intent_type if intent_type in {"reflective", "factual", "mixed"} else "mixed"
    )

    # Keep planning signal conservative when evidence/integration dominates and ambiguity is not extreme.
    if evid >= 0.75 and plan >= 0.65 and amb <= 0.70:
        plan *= 0.70
    if multi >= 0.70 and plan >= 0.60 and amb <= 0.65:
        plan *= 0.75
    if evid >= 0.85 and multi >= 0.75 and plan >= 0.60 and amb <= 0.55:
        plan = min(plan, 0.55)

    # Factual low-reflection contexts should not over-activate decomposition unless clearly needed.
    if intent == "factual" and refl <= 0.50 and evid >= 0.70 and plan >= 0.55:
        plan *= 0.75

    return (_clamp01(evid), _clamp01(plan), _clamp01(multi))


def _parse_with_gemini(query: str, api_key: str, model: str) -> dict[str, Any] | None:
    try:
        messages_mod = importlib.import_module("langchain_core.messages")
        genai_mod = importlib.import_module("langchain_google_genai")

        HumanMessage = getattr(messages_mod, "HumanMessage")
        SystemMessage = getattr(messages_mod, "SystemMessage")
        ChatGoogleGenerativeAI = getattr(genai_mod, "ChatGoogleGenerativeAI")

        llm = ChatGoogleGenerativeAI(model=model, temperature=0, google_api_key=api_key)

        system = (
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

        out = llm.invoke([SystemMessage(content=system), HumanMessage(content=query)])
        raw = out.content if hasattr(out, "content") else str(out)
        payload = _extract_json(_to_text(raw))

        urgent_raw = payload.get("urgent", None)
        complexity_raw = payload.get("complexity", None)
        ambiguity_raw = payload.get("ambiguity", None)
        expertise_raw = payload.get("expertise", None)
        threshold_raw = payload.get("threshold", 0.3)
        topic_familiarity_raw = payload.get("topic_familiarity", 0.5)
        failure_signal_raw = payload.get("failure_signal", 0.0)
        intent_type_raw = str(payload.get("intent_type", "mixed")).strip().lower()
        reflective_intent_raw = payload.get("reflective_intent", 0.5)
        verify_request_raw = payload.get("verify_request", False)
        needs_external_evidence_raw = payload.get("needs_external_evidence", 0.3)
        needs_task_plan_raw = payload.get("needs_task_plan", 0.2)
        needs_multi_source_integration_raw = payload.get(
            "needs_multi_source_integration", 0.3
        )
        valence_raw = payload.get("valence", 0.0)

        urgent = _coerce_bool(urgent_raw)
        if urgent is None:
            return None
        verify_request = _coerce_bool(verify_request_raw)
        if verify_request is None:
            verify_request = False

        try:
            complexity = _clamp01(float(complexity_raw))
            ambiguity = _clamp01(float(ambiguity_raw))
            expertise = _clamp01(float(expertise_raw))
            threshold = _clamp01(float(threshold_raw))
            topic_familiarity = _clamp01(float(topic_familiarity_raw))
            failure_signal = _clamp01(float(failure_signal_raw))
            reflective_intent = _clamp01(float(reflective_intent_raw))
            needs_external_evidence = _clamp01(float(needs_external_evidence_raw))
            needs_task_plan = _clamp01(float(needs_task_plan_raw))
            needs_multi_source_integration = _clamp01(
                float(needs_multi_source_integration_raw)
            )
            valence = _clamp11(float(valence_raw))
        except Exception:
            return None

        if intent_type_raw not in {"reflective", "factual", "mixed"}:
            intent_type_raw = "mixed"
        (
            needs_external_evidence,
            needs_task_plan,
            needs_multi_source_integration,
        ) = _calibrate_action_signals(
            needs_external_evidence=needs_external_evidence,
            needs_task_plan=needs_task_plan,
            needs_multi_source_integration=needs_multi_source_integration,
            ambiguity=ambiguity,
            intent_type=intent_type_raw,
            reflective_intent=reflective_intent,
        )

        return {
            "urgent": urgent,
            "complexity": complexity,
            "ambiguity": ambiguity,
            "expertise": expertise,
            "threshold": threshold,
            "topic_familiarity": topic_familiarity,
            "failure_signal": failure_signal,
            "intent_type": intent_type_raw,
            "reflective_intent": reflective_intent,
            "verify_request": verify_request,
            "needs_external_evidence": needs_external_evidence,
            "needs_task_plan": needs_task_plan,
            "needs_multi_source_integration": needs_multi_source_integration,
            "valence": valence,
        }

    except Exception:
        return None


def _parse_with_openai(query: str, api_key: str, model: str) -> dict[str, Any] | None:
    try:
        messages_mod = importlib.import_module("langchain_core.messages")
        openai_mod = importlib.import_module("langchain_openai")

        HumanMessage = getattr(messages_mod, "HumanMessage")
        SystemMessage = getattr(messages_mod, "SystemMessage")
        ChatOpenAI = getattr(openai_mod, "ChatOpenAI")

        llm = ChatOpenAI(model=model, temperature=0, api_key=api_key)

        system = (
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

        out = llm.invoke([SystemMessage(content=system), HumanMessage(content=query)])
        raw = out.content if hasattr(out, "content") else str(out)
        payload = _extract_json(_to_text(raw))

        urgent_raw = payload.get("urgent", None)
        complexity_raw = payload.get("complexity", None)
        ambiguity_raw = payload.get("ambiguity", None)
        expertise_raw = payload.get("expertise", None)
        threshold_raw = payload.get("threshold", 0.3)
        topic_familiarity_raw = payload.get("topic_familiarity", 0.5)
        failure_signal_raw = payload.get("failure_signal", 0.0)
        intent_type_raw = str(payload.get("intent_type", "mixed")).strip().lower()
        reflective_intent_raw = payload.get("reflective_intent", 0.5)
        verify_request_raw = payload.get("verify_request", False)
        needs_external_evidence_raw = payload.get("needs_external_evidence", 0.3)
        needs_task_plan_raw = payload.get("needs_task_plan", 0.2)
        needs_multi_source_integration_raw = payload.get(
            "needs_multi_source_integration", 0.3
        )
        valence_raw = payload.get("valence", 0.0)

        urgent = _coerce_bool(urgent_raw)
        if urgent is None:
            return None
        verify_request = _coerce_bool(verify_request_raw)
        if verify_request is None:
            verify_request = False

        try:
            complexity = _clamp01(float(complexity_raw))
            ambiguity = _clamp01(float(ambiguity_raw))
            expertise = _clamp01(float(expertise_raw))
            threshold = _clamp01(float(threshold_raw))
            topic_familiarity = _clamp01(float(topic_familiarity_raw))
            failure_signal = _clamp01(float(failure_signal_raw))
            reflective_intent = _clamp01(float(reflective_intent_raw))
            needs_external_evidence = _clamp01(float(needs_external_evidence_raw))
            needs_task_plan = _clamp01(float(needs_task_plan_raw))
            needs_multi_source_integration = _clamp01(
                float(needs_multi_source_integration_raw)
            )
            valence = _clamp11(float(valence_raw))
        except Exception:
            return None

        if intent_type_raw not in {"reflective", "factual", "mixed"}:
            intent_type_raw = "mixed"
        (
            needs_external_evidence,
            needs_task_plan,
            needs_multi_source_integration,
        ) = _calibrate_action_signals(
            needs_external_evidence=needs_external_evidence,
            needs_task_plan=needs_task_plan,
            needs_multi_source_integration=needs_multi_source_integration,
            ambiguity=ambiguity,
            intent_type=intent_type_raw,
            reflective_intent=reflective_intent,
        )

        return {
            "urgent": urgent,
            "complexity": complexity,
            "ambiguity": ambiguity,
            "expertise": expertise,
            "threshold": threshold,
            "topic_familiarity": topic_familiarity,
            "failure_signal": failure_signal,
            "intent_type": intent_type_raw,
            "reflective_intent": reflective_intent,
            "verify_request": verify_request,
            "needs_external_evidence": needs_external_evidence,
            "needs_task_plan": needs_task_plan,
            "needs_multi_source_integration": needs_multi_source_integration,
            "valence": valence,
        }

    except Exception:
        return None


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for v in value:
            if isinstance(v, dict) and isinstance(v.get("text"), str):
                parts.append(v["text"])
            else:
                parts.append(_to_text(v))
        return "\n".join(parts)
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        return json.dumps(value)
    return str(value)


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*$", "", cleaned)
    decoder = json.JSONDecoder()
    for i, ch in enumerate(cleaned):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(cleaned[i:])
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    raise ValueError("No JSON object found")


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "y", "1"}:
            return True
        if text in {"false", "no", "n", "0"}:
            return False
    return None
