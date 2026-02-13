from __future__ import annotations

import json
import os
import re
import importlib
from typing import Any

from dotenv import load_dotenv


def parse_context(query: str, model: str = "gemini-3-flash-preview") -> dict[str, Any]:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing (check .env)")

    parsed = _parse_with_gemini(query=query, api_key=api_key, model=model)
    print(parsed)

    if parsed is None:
        raise RuntimeError("Gemini parsing failed (no valid JSON returned)")

    return parsed


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
            'Schema: {"urgent": boolean, "complexity": number, "ambiguity": number, "expertise": number}. '
            "Rules: complexity, ambiguity, expertise are each 0..1. "
            "Interpretation: expertise 0 means novice user language, 1 means expert-level user language."
        )

        out = llm.invoke([SystemMessage(content=system), HumanMessage(content=query)])
        raw = out.content if hasattr(out, "content") else str(out)
        payload = _extract_json(_to_text(raw))

        urgent = payload.get("urgent", None)
        complexity_raw = payload.get("complexity", None)
        ambiguity_raw = payload.get("ambiguity", None)
        expertise_raw = payload.get("expertise", None)

        if not isinstance(urgent, bool):
            return None

        try:
            complexity = _clamp01(float(complexity_raw))
            ambiguity = _clamp01(float(ambiguity_raw))
            expertise = _clamp01(float(expertise_raw))
        except Exception:
            return None

        return {
            "urgent": urgent,
            "complexity": complexity,
            "ambiguity": ambiguity,
            "expertise": expertise,
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
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found")
    return json.loads(cleaned[start : end + 1])
