from __future__ import annotations

import os
import importlib
from typing import Any, TypedDict, Literal

from dotenv import load_dotenv
from pipeline.llm_client import build_chat_llm
from utils import resolve_provider_and_model_name
from config import get_action_system_prompt

from core.state import init_state as init_engine_state
from core.decision import post_update as engine_post_update
from core.decision import step as engine_step
from pipeline.parser import parse_context


Action = Literal[
    "act_respond",
    "act_search",
    "act_verify",
    "act_clarify",
    "act_decompose",
    "act_think",
    "act_synthesize",
]


class GraphState(TypedDict, total=False):
    query: str
    context: dict[str, Any]
    decision: dict[str, Any]
    system_prompt: str
    findings: list[str]
    answer: str
    engine_state: dict[str, Any]


# -----------------------------
# LLM helpers
# -----------------------------


def _llm() -> Any:
    load_dotenv()
    provider, model_name = resolve_provider_and_model_name()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing (check .env)")
        return build_chat_llm(
            provider_name="openai",
            model=model_name,
            temperature=0.3,
            api_key=api_key,
        )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing (check .env)")
    return build_chat_llm(
        provider_name="gemini",
        model=model_name,
        temperature=0.3,
        api_key=api_key,
    )


def _llm_text(out) -> str:
    content = out.content if hasattr(out, "content") else out

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict) and isinstance(p.get("text"), str):
                parts.append(p["text"])
        return "\n".join(parts)

    if isinstance(content, dict) and isinstance(content.get("text"), str):
        return content["text"]

    return str(content)


def _context_config(state: GraphState) -> tuple[bool, int]:
    engine_state = state.get("engine_state") or {}
    params = engine_state.get("params", {})
    enabled = bool(params.get("enable_context_memory", False))
    window = int(params.get("context_window_turns", 2))
    return enabled, window


def _recent_history(state: GraphState) -> list[dict[str, str]]:
    enabled, window = _context_config(state)
    if not enabled or window <= 0:
        return []
    engine_state = state.get("engine_state") or {}
    context_history = engine_state.get("context_history", [])
    if not isinstance(context_history, list):
        return []
    recent = context_history[-window:]
    turns: list[dict[str, str]] = []
    for item in recent:
        if isinstance(item, dict):
            turns.append(
                {
                    "query": str(item.get("query", "")),
                    "answer": str(item.get("answer", "")),
                }
            )
    return turns


def _history_block(state: GraphState) -> str:
    turns = _recent_history(state)
    if not turns:
        return ""
    lines = ["Recent conversation context:"]
    for i, turn in enumerate(turns, start=1):
        idx = len(turns) - i + 1
        lines.append(f"Turn -{idx} user: {turn.get('query', '')}")
        lines.append(f"Turn -{idx} assistant: {turn.get('answer', '')}")
    return "\n\n" + "\n".join(lines)


# -----------------------------
# Graph nodes
# -----------------------------


def node_context_parser(state: GraphState) -> GraphState:
    query = state["query"]
    history_turns = _recent_history(state)
    load_dotenv()
    provider_name, model_name = resolve_provider_and_model_name()

    ctx = parse_context(
        query,
        history_turns=history_turns,
        model=model_name,
        provider=provider_name,
    )
    return {"context": ctx}


def node_engine(state: GraphState) -> GraphState:
    engine_state = state.get("engine_state") or init_engine_state()
    decision = engine_step(state["context"], engine_state)
    return {"decision": decision, "engine_state": engine_state}


def node_prompt_shaper(state: GraphState) -> GraphState:
    decision = state["decision"]

    urgency = float(decision.get("urgency", 0.0))
    expertise = float(decision.get("user_expertise", 0.5))

    if decision["action"] == "act_respond":
        style_modifier = str(decision.get("style_modifier") or "style_concise")
        style_map = {
            "style_concise": "Be concise and direct.",
            "style_thorough": "Be thorough, structured, and complete.",
            "style_exploratory": "Be exploratory and connect non-obvious ideas carefully.",
            "style_cautious": "Be cautious, explicit about uncertainty, and avoid overclaiming.",
            "style_tutorial": "Be tutorial and beginner-friendly with simple explanations.",
        }
        style = style_map.get(style_modifier, "Be concise and direct.")
        if style_modifier != "style_tutorial":
            if expertise <= 0.4:
                style += " Use beginner-friendly language."
            elif expertise >= 0.7:
                style += " Use expert-level concise wording."
        if urgency >= 0.6 and style_modifier == "style_concise":
            style = "Be extremely concise and direct."
        system = (
            f"You are Qwestor. {style} "
            "Avoid unsupported precise numeric claims (percentages, exact rates, exact counts) unless grounded in provided evidence. "
            "Do not add greetings or self-introductions."
        )
    else:
        try:
            system = get_action_system_prompt(str(decision["action"]))
        except KeyError as exc:
            raise RuntimeError(str(exc)) from exc

    return {"system_prompt": system}


def route_action(state: GraphState) -> Action:
    return state["decision"]["action"]


def node_quick_answer(state: GraphState) -> GraphState:
    llm = _llm()
    prompt = (
        state["system_prompt"]
        + _history_block(state)
        + "\n\nUser query: "
        + state["query"]
    )
    out = llm.invoke(prompt)
    return {"answer": _llm_text(out)}


def node_simulated_search(state: GraphState) -> GraphState:
    q = state["query"].strip()
    findings = [
        f"Finding 1: Key facts relevant to '{q}'.",
        f"Finding 2: Important distinctions and examples for '{q}'.",
        f"Finding 3: Common pitfalls and clarifications for '{q}'.",
    ]
    return {"findings": findings}


def node_clarify(state: GraphState) -> GraphState:
    llm = _llm()
    prompt = (
        state["system_prompt"]
        + _history_block(state)
        + "\n\nUser query: "
        + state["query"]
    )
    out = llm.invoke(prompt)
    return {"answer": _llm_text(out)}


def node_decompose(state: GraphState) -> GraphState:
    llm = _llm()
    prompt = (
        state["system_prompt"]
        + _history_block(state)
        + "\n\nUser query: "
        + state["query"]
    )
    out = llm.invoke(prompt)
    return {"answer": _llm_text(out)}


def node_think(state: GraphState) -> GraphState:
    llm = _llm()
    prompt = (
        state["system_prompt"]
        + _history_block(state)
        + "\n\nUser query: "
        + state["query"]
    )
    out = llm.invoke(prompt)
    return {"answer": _llm_text(out)}


def node_research_synthesis(state: GraphState) -> GraphState:
    llm = _llm()
    findings_text = "\n".join(f"- {f}" for f in state.get("findings", []))
    prompt = (
        state["system_prompt"]
        + _history_block(state)
        + "\n\nUse these notes:\n"
        + findings_text
        + "\n\nUser query: "
        + state["query"]
    )
    out = llm.invoke(prompt)
    return {"answer": _llm_text(out)}


def node_search_evidence(state: GraphState) -> GraphState:
    llm = _llm()
    findings_text = "\n".join(f"- {f}" for f in state.get("findings", []))
    prompt = (
        state["system_prompt"]
        + _history_block(state)
        + "\n\nEvidence notes gathered:\n"
        + findings_text
        + "\n\nUser query: "
        + state["query"]
        + "\n\nReturn only: (1) key evidence bullets, (2) open uncertainties."
    )
    out = llm.invoke(prompt)
    return {"answer": _llm_text(out)}


def node_verify_synthesis(state: GraphState) -> GraphState:
    llm = _llm()
    findings_text = "\n".join(f"- {f}" for f in state.get("findings", []))
    prompt = (
        state["system_prompt"]
        + _history_block(state)
        + "\n\nVerification notes:\n"
        + findings_text
        + "\n\nUser query: "
        + state["query"]
    )
    out = llm.invoke(prompt)
    return {"answer": _llm_text(out)}


def node_post_update(state: GraphState) -> GraphState:
    engine_state = state.get("engine_state") or init_engine_state()
    updated_state = engine_post_update(
        context=state["context"], state=engine_state, decision=state["decision"]
    )
    context_history = updated_state.get("context_history", [])
    if not isinstance(context_history, list):
        context_history = []
    context_history.append(
        {
            "query": str(state.get("query", "")),
            "answer": str(state.get("answer", "")),
        }
    )
    updated_state["context_history"] = context_history
    return {"engine_state": updated_state}


# -----------------------------
# Graph builder
# -----------------------------


def build_graph():
    graph_mod = importlib.import_module("langgraph.graph")
    StateGraph = getattr(graph_mod, "StateGraph")
    END = getattr(graph_mod, "END")

    graph = StateGraph(GraphState)

    graph.add_node("context_parser", node_context_parser)
    graph.add_node("engine", node_engine)
    graph.add_node("prompt_shaper", node_prompt_shaper)
    graph.add_node("quick_answer", node_quick_answer)
    graph.add_node("clarify", node_clarify)
    graph.add_node("decompose", node_decompose)
    graph.add_node("think", node_think)
    graph.add_node("simulated_search", node_simulated_search)
    graph.add_node("search_evidence", node_search_evidence)
    graph.add_node("research_synthesis", node_research_synthesis)
    graph.add_node("verify_synthesis", node_verify_synthesis)
    graph.add_node("post_update", node_post_update)

    graph.set_entry_point("context_parser")
    graph.add_edge("context_parser", "engine")
    graph.add_edge("engine", "prompt_shaper")

    graph.add_conditional_edges(
        "prompt_shaper",
        route_action,
        {
            "act_respond": "quick_answer",
            "act_clarify": "clarify",
            "act_decompose": "decompose",
            "act_think": "think",
            "act_search": "simulated_search",
            "act_verify": "simulated_search",
            "act_synthesize": "simulated_search",
        },
    )

    graph.add_edge("quick_answer", "post_update")
    graph.add_edge("clarify", "post_update")
    graph.add_edge("decompose", "post_update")
    graph.add_edge("think", "post_update")
    graph.add_conditional_edges(
        "simulated_search",
        route_action,
        {
            "act_search": "search_evidence",
            "act_verify": "verify_synthesis",
            "act_synthesize": "research_synthesis",
        },
    )
    graph.add_edge("search_evidence", "post_update")
    graph.add_edge("research_synthesis", "post_update")
    graph.add_edge("verify_synthesis", "post_update")
    graph.add_edge("post_update", END)

    return graph.compile()
