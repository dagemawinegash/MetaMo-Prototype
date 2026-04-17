from __future__ import annotations

import json
import os
import re
import importlib
import time
from typing import Any

from config import get_context_parser_system_prompt
from dotenv import load_dotenv
from pipeline.llm_client import build_chat_llm
from utils import (
    clamp_to_signed_unit_interval,
    clamp_to_unit_interval,
    resolve_provider_and_model_name,
)


def parse_context(
    query: str,
    history_turns: list[dict[str, str]] | None = None,
    model: str | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    active_provider, resolved_model = resolve_provider_and_model_name(
        explicit_provider_name=provider
    )
    active_model = model or resolved_model
    if active_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing (check .env)")
    else:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is missing (check .env)")

    last_error = ""
    last_provider_error = ""
    for attempt in range(3):
        if active_provider == "openai":
            parsed, provider_error = _parse_with_openai(
                query=query,
                history_turns=history_turns,
                api_key=api_key,
                model=active_model,
            )
        else:
            parsed, provider_error = _parse_with_gemini(
                query=query,
                history_turns=history_turns,
                api_key=api_key,
                model=active_model,
            )

        if parsed is not None:
            return parsed

        last_error = f"parse_attempt_{attempt + 1}_failed"
        if provider_error:
            last_provider_error = provider_error
        if attempt < 2:
            time.sleep(0.35 * (attempt + 1))

    raise RuntimeError(
        f"{active_provider} parsing failed (no valid JSON returned) after 3 attempts; "
        f"last_error={last_error}; provider_error={last_provider_error}"
    )


def _calibrate_action_signals(
    *,
    needs_external_evidence: float,
    needs_task_plan: float,
    needs_multi_source_integration: float,
    ambiguity: float,
    intent_type: str,
    reflective_intent: float,
) -> tuple[float, float, float]:
    evid = clamp_to_unit_interval(needs_external_evidence)
    plan = clamp_to_unit_interval(needs_task_plan)
    multi = clamp_to_unit_interval(needs_multi_source_integration)
    amb = clamp_to_unit_interval(ambiguity)
    refl = clamp_to_unit_interval(reflective_intent)
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

    return (
        clamp_to_unit_interval(evid),
        clamp_to_unit_interval(plan),
        clamp_to_unit_interval(multi),
    )


def _build_context_input(
    query: str, history_turns: list[dict[str, str]] | None = None
) -> str:
    if not history_turns:
        return f"Current user query:\n{query}"

    parts = ["Recent conversation context:"]
    for i, turn in enumerate(history_turns, start=1):
        user_q = str(turn.get("query", "")).strip()
        assistant_a = str(turn.get("answer", "")).strip()
        parts.append(f"Turn -{len(history_turns) - i + 1} user: {user_q}")
        parts.append(f"Turn -{len(history_turns) - i + 1} assistant: {assistant_a}")
    parts.append(f"Current user query:\n{query}")
    return "\n".join(parts)


def _normalize_context_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
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
        complexity = clamp_to_unit_interval(float(complexity_raw))
        ambiguity = clamp_to_unit_interval(float(ambiguity_raw))
        expertise = clamp_to_unit_interval(float(expertise_raw))
        threshold = clamp_to_unit_interval(float(threshold_raw))
        topic_familiarity = clamp_to_unit_interval(float(topic_familiarity_raw))
        failure_signal = clamp_to_unit_interval(float(failure_signal_raw))
        reflective_intent = clamp_to_unit_interval(float(reflective_intent_raw))
        needs_external_evidence = clamp_to_unit_interval(
            float(needs_external_evidence_raw)
        )
        needs_task_plan = clamp_to_unit_interval(float(needs_task_plan_raw))
        needs_multi_source_integration = clamp_to_unit_interval(
            float(needs_multi_source_integration_raw)
        )
        valence = clamp_to_signed_unit_interval(float(valence_raw))
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


def _parse_with_provider(
    *,
    provider_name: str,
    query: str,
    history_turns: list[dict[str, str]] | None,
    api_key: str,
    model: str,
) -> tuple[dict[str, Any] | None, str]:
    try:
        messages_mod = importlib.import_module("langchain_core.messages")
        HumanMessage = getattr(messages_mod, "HumanMessage")
        SystemMessage = getattr(messages_mod, "SystemMessage")

        llm = build_chat_llm(
            provider_name=provider_name,
            model=model,
            temperature=0,
            api_key=api_key,
        )

        user_input = _build_context_input(query, history_turns)
        system_prompt = get_context_parser_system_prompt()
        if provider_name == "gemini":
            combined_prompt = (
                "SYSTEM INSTRUCTION:\n"
                + system_prompt
                + "\n\nINPUT:\n"
                + user_input
                + "\n\nReturn JSON only."
            )
            out = llm.invoke([HumanMessage(content=combined_prompt)])
        else:
            out = llm.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_input),
                ]
            )
        raw = out.content if hasattr(out, "content") else str(out)
        payload = _extract_json(_to_text(raw))
        normalized = _normalize_context_payload(payload)
        if normalized is None:
            return None, "payload_normalization_failed"
        return normalized, ""
    except Exception as exc:
        return None, str(exc)


def _parse_with_gemini(
    query: str,
    history_turns: list[dict[str, str]] | None,
    api_key: str,
    model: str,
) -> tuple[dict[str, Any] | None, str]:
    return _parse_with_provider(
        provider_name="gemini",
        query=query,
        history_turns=history_turns,
        api_key=api_key,
        model=model,
    )


def _parse_with_openai(
    query: str,
    history_turns: list[dict[str, str]] | None,
    api_key: str,
    model: str,
) -> tuple[dict[str, Any] | None, str]:
    return _parse_with_provider(
        provider_name="openai",
        query=query,
        history_turns=history_turns,
        api_key=api_key,
        model=model,
    )


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
