from __future__ import annotations

import os

from config import (
    DEFAULT_GEMINI_MODEL_NAME,
    DEFAULT_LLM_PROVIDER_NAME,
    DEFAULT_OPENAI_MODEL_NAME,
    SUPPORTED_LLM_PROVIDER_NAMES,
)


def clamp_to_unit_interval(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def clamp_to_signed_unit_interval(value: float) -> float:
    if value < -1.0:
        return -1.0
    if value > 1.0:
        return 1.0
    return value


def resolve_provider_name(
    *,
    environment_variable_name: str,
    default_provider_name: str,
    supported_provider_names: set[str],
) -> str:
    provider_name = os.getenv(environment_variable_name, default_provider_name)
    normalized_provider_name = provider_name.strip().lower()
    if normalized_provider_name not in supported_provider_names:
        raise RuntimeError(
            f"Unsupported provider '{normalized_provider_name}'. "
            f"Supported providers: {sorted(supported_provider_names)}"
        )
    return normalized_provider_name


def resolve_model_name(
    *,
    environment_variable_name: str,
    default_model_name: str,
) -> str:
    model_name = os.getenv(environment_variable_name, default_model_name).strip()
    if not model_name:
        raise RuntimeError(
            f"Model name from '{environment_variable_name}' cannot be empty."
        )
    return model_name


def resolve_provider_and_model_name(
    *,
    explicit_provider_name: str | None = None,
) -> tuple[str, str]:
    if explicit_provider_name is None:
        provider_name = resolve_provider_name(
            environment_variable_name="LLM_PROVIDER",
            default_provider_name=DEFAULT_LLM_PROVIDER_NAME,
            supported_provider_names=SUPPORTED_LLM_PROVIDER_NAMES,
        )
    else:
        provider_name = explicit_provider_name.strip().lower()
        if provider_name not in SUPPORTED_LLM_PROVIDER_NAMES:
            raise RuntimeError(
                f"Unsupported provider '{provider_name}'. "
                f"Supported providers: {sorted(SUPPORTED_LLM_PROVIDER_NAMES)}"
            )

    if provider_name == "openai":
        model_name = resolve_model_name(
            environment_variable_name="OPENAI_MODEL",
            default_model_name=DEFAULT_OPENAI_MODEL_NAME,
        )
    else:
        model_name = resolve_model_name(
            environment_variable_name="GEMINI_MODEL",
            default_model_name=DEFAULT_GEMINI_MODEL_NAME,
        )

    return provider_name, model_name
