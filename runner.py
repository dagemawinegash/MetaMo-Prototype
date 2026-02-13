from __future__ import annotations

from graph import build_graph


def main() -> None:
    app = build_graph()

    queries = [
        "What is the capital of France?",
        "Quickly tell me the capital of France!",
        "Explain the detailed distinct architectural differences between baroque and rococo styles with examples",
    ]

    for i, q in enumerate(queries, start=1):
        out = app.invoke({"query": q})

        decision = out.get("decision", {})
        ctx = out.get("context", {})

        action = decision.get("action", "?")
        urgency = float(decision.get("urgency", 0.0))
        complexity = float(ctx.get("complexity", 0.0))
        answer = out.get("answer", "")

        print(
            f"{i}. {action} | urgent={ctx.get('urgent')} "
            f"cx={complexity:.2f} u={urgency:.2f}"
        )
        print(answer)
        print("-" * 60)


if __name__ == "__main__":
    main()
