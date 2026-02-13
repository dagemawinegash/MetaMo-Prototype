from __future__ import annotations

from graph import build_graph
from engine import init_state as init_engine_state


def main() -> None:
    app = build_graph()

    sessions = [
        {
            "name": "Session A - urgency and quick responses",
            "queries": [
                "What is the capital of France?",
                "Quickly tell me the capital of France!",
                "Give me the capital of France in one word.",
            ],
        },
        {
            "name": "Session B - growing complexity",
            "queries": [
                "What is baroque architecture?",
                "Compare baroque and rococo in a detailed way.",
                "Now create a structured deep explanation with examples and pitfalls.",
            ],
        },
    ]

    for session in sessions:
        print(f"\n{session['name']}")
        print("=" * len(session["name"]))
        engine_state = init_engine_state()

        for i, q in enumerate(session["queries"], start=1):
            out = app.invoke({"query": q, "engine_state": engine_state})
            engine_state = out.get("engine_state", engine_state)

            decision = out.get("decision", {})
            ctx = out.get("context", {})
            goals = engine_state.get("goals", {})

            action = decision.get("action", "?")
            urgency = float(decision.get("urgency", 0.0))
            complexity = float(ctx.get("complexity", 0.0))
            answer = out.get("answer", "")

            print(
                f"{i}. {action} | urgent={ctx.get('urgent')} "
                f"cx={complexity:.2f} u={urgency:.2f} "
                f"g_eff={float(goals.get('efficiency', 0.0)):.2f} "
                f"g_acc={float(goals.get('accuracy', 0.0)):.2f}"
            )
            print(answer)
            print("-" * 60)


if __name__ == "__main__":
    main()
