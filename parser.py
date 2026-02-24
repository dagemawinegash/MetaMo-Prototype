from __future__ import annotations

import json
import os
import re
import importlib
import time
from typing import Any

from dotenv import load_dotenv


def parse_context(query: str, model: str = "gemini-3-flash-preview") -> dict[str, Any]:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing (check .env)")

    last_error = ""
    for attempt in range(3):
        parsed = _parse_with_gemini(query=query, api_key=api_key, model=model)
        if parsed is not None:
            return parsed

        last_error = f"parse_attempt_{attempt + 1}_failed"
        if attempt < 2:
            time.sleep(0.35 * (attempt + 1))

    raise RuntimeError(
        f"Gemini parsing failed (no valid JSON returned) after 3 attempts; last_error={last_error}"
    )


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


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
            'Schema: {"urgent": boolean, "complexity": number, "ambiguity": number, "expertise": number, "threshold": number, "topic_familiarity": number, "failure_signal": number, "intent_type": string, "reflective_intent": number}. '
            "Rules: complexity, ambiguity, expertise, threshold, topic_familiarity, failure_signal are each 0..1. "
            "Rules: intent_type must be one of reflective|factual|mixed. "
            "Rules: reflective_intent is 0..1 and measures how much deliberate internal reasoning is likely beneficial before final answer. "
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

        urgent = _coerce_bool(urgent_raw)
        if urgent is None:
            return None

        try:
            complexity = _clamp01(float(complexity_raw))
            ambiguity = _clamp01(float(ambiguity_raw))
            expertise = _clamp01(float(expertise_raw))
            threshold = _clamp01(float(threshold_raw))
            topic_familiarity = _clamp01(float(topic_familiarity_raw))
            failure_signal = _clamp01(float(failure_signal_raw))
            reflective_intent = _clamp01(float(reflective_intent_raw))
        except Exception:
            return None

        if intent_type_raw not in {"reflective", "factual", "mixed"}:
            intent_type_raw = "mixed"

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
