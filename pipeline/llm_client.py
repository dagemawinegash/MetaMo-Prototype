from __future__ import annotations

import importlib
import os
from typing import Any


def _build_openai_default_headers() -> dict[str, str]:
    referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
    app_title = os.getenv("OPENROUTER_X_TITLE", "").strip()
    headers: dict[str, str] = {}
    if referer:
        headers["HTTP-Referer"] = referer
    if app_title:
        headers["X-OpenRouter-Title"] = app_title
    return headers


def build_chat_llm(
    *,
    provider_name: str,
    model: str,
    temperature: float,
    api_key: str,
) -> Any:
    if provider_name == "openai":
        openai_mod = importlib.import_module("langchain_openai")
        ChatOpenAI = getattr(openai_mod, "ChatOpenAI")
        base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
        default_headers = _build_openai_default_headers()

        openai_kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "api_key": api_key,
        }
        if base_url:
            openai_kwargs["base_url"] = base_url
        if default_headers:
            openai_kwargs["default_headers"] = default_headers

        return ChatOpenAI(**openai_kwargs)

    if provider_name == "gemini":
        genai_mod = importlib.import_module("langchain_google_genai")
        ChatGoogleGenerativeAI = getattr(genai_mod, "ChatGoogleGenerativeAI")
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key,
        )

    raise RuntimeError(f"Unsupported provider '{provider_name}'")
