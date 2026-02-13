from __future__ import annotations

from graph import build_graph
from engine import init_state as init_engine_state


def main() -> None:
    app = build_graph()

    sessions = [
        {
            "name": "Session - 10 turn mixed stress",
            "queries": [
                "What is the capital of France?",
                "Quickly tell me the capital of France!",
                "Can you help me with it?",
                "Explain baroque architecture in simple terms for a beginner.",
                "Compare baroque and rococo in detail with examples.",
                "I am writing a paper, deconstruct epistemic uncertainty in Bayesian modeling.",
                "Could you explain that again?",
                "Give me a concise answer: what is overfitting?",
                "I need an exact, step-by-step detailed guide to compare model calibration methods.",
                "Which one is better?",
            ],
        }
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
            mods = engine_state.get("modulators", {})
            goals = engine_state.get("goals", {})

            action = decision.get("action", "?")
            urgency = float(decision.get("urgency", 0.0))
            resolution = float(decision.get("resolution", 0.0))
            user_expertise = float(decision.get("user_expertise", 0.0))
            complexity = float(ctx.get("complexity", 0.0))
            ambiguity = float(ctx.get("ambiguity", 0.0))
            expertise = float(ctx.get("expertise", 0.0))
            answer = out.get("answer", "")

            print(
                f"{i}. {action} | urgent={ctx.get('urgent')} "
                f"cx={complexity:.2f} amb={ambiguity:.2f} exp={expertise:.2f} "
                f"u={urgency:.2f} r={resolution:.2f} ux={user_expertise:.2f} "
                f"m_r={float(mods.get('resolution', 0.0)):.2f} "
                f"m_ux={float(mods.get('user_expertise', 0.0)):.2f} "
                f"g_eff={float(goals.get('efficiency', 0.0)):.2f} "
                f"g_acc={float(goals.get('accuracy', 0.0)):.2f}"
            )
            print(answer)
            print("-" * 60)


if __name__ == "__main__":
    main()
