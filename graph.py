from __future__ import annotations

import os
import importlib
from typing import Any, TypedDict, Literal

from dotenv import load_dotenv

from engine import init_state as init_engine_state
from engine import post_update as engine_post_update
from engine import step as engine_step
from parser import parse_context


Action = Literal["act_respond", "act_search", "act_clarify", "act_decompose"]


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


def _get_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


def _llm() -> Any:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing (check .env)")

    genai_mod = importlib.import_module("langchain_google_genai")
    ChatGoogleGenerativeAI = getattr(genai_mod, "ChatGoogleGenerativeAI")

    return ChatGoogleGenerativeAI(
        model=_get_model(),
        temperature=0.3,
        google_api_key=api_key,
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


# -----------------------------
# Graph nodes
# -----------------------------


def node_context_parser(state: GraphState) -> GraphState:
    query = state["query"]
    ctx = parse_context(query, model=_get_model())
    return {"context": ctx}


def node_engine(state: GraphState) -> GraphState:
    engine_state = state.get("engine_state") or init_engine_state()
    decision = engine_step(state["context"], engine_state)
    return {"decision": decision, "engine_state": engine_state}


def node_prompt_shaper(state: GraphState) -> GraphState:
    decision = state["decision"]
    ctx = state["context"]

    urgency = float(decision.get("urgency", 0.0))
    expertise = float(decision.get("user_expertise", 0.5))
    complexity = float(ctx.get("complexity", 0.3))

    if decision["action"] == "act_respond":
        style = "Be concise and direct."
        if expertise <= 0.4:
            style += " Use beginner-friendly language."
        elif expertise >= 0.7:
            style += " Use expert-level concise wording."
        if urgency >= 0.6:
            style = "Be extremely concise and direct."
        system = f"You are Qwestor. {style} Do not add greetings or self-introductions."
    elif decision["action"] == "act_clarify":
        system = (
            "You are Qwestor. Ask exactly one short clarifying question. "
            "Do not answer yet. Do not add greetings or self-introductions."
        )
    elif decision["action"] == "act_decompose":
        system = (
            "You are Qwestor. Break the user request into a short numbered plan "
            "(3-7 concrete steps) with dependencies and execution order. "
            "Do not provide the full final solution yet. "
            "Do not add greetings or self-introductions."
        )
    else:
        depth = "Provide a deeper, structured explanation with examples."
        if complexity >= 0.7:
            depth = "Provide a deep, structured explanation with clear sections and examples."
        if expertise <= 0.4:
            depth += " Keep terminology beginner-friendly."
        elif expertise >= 0.7:
            depth += " You can use precise technical terminology."
        system = f"You are Qwestor. {depth} Do not add greetings or self-introductions."

    return {"system_prompt": system}


def route_action(state: GraphState) -> Action:
    return state["decision"]["action"]


def node_quick_answer(state: GraphState) -> GraphState:
    llm = _llm()
    prompt = state["system_prompt"] + "\n\nUser query: " + state["query"]
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
    prompt = state["system_prompt"] + "\n\nUser query: " + state["query"]
    out = llm.invoke(prompt)
    return {"answer": _llm_text(out)}


def node_decompose(state: GraphState) -> GraphState:
    llm = _llm()
    prompt = state["system_prompt"] + "\n\nUser query: " + state["query"]
    out = llm.invoke(prompt)
    return {"answer": _llm_text(out)}


def node_research_synthesis(state: GraphState) -> GraphState:
    llm = _llm()
    findings_text = "\n".join(f"- {f}" for f in state.get("findings", []))
    prompt = (
        state["system_prompt"]
        + "\n\nUse these notes:\n"
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
    graph.add_node("simulated_search", node_simulated_search)
    graph.add_node("research_synthesis", node_research_synthesis)
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
            "act_search": "simulated_search",
        },
    )

    graph.add_edge("quick_answer", "post_update")
    graph.add_edge("clarify", "post_update")
    graph.add_edge("decompose", "post_update")
    graph.add_edge("simulated_search", "research_synthesis")
    graph.add_edge("research_synthesis", "post_update")
    graph.add_edge("post_update", END)

    return graph.compile()
