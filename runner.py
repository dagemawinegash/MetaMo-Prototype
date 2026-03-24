from __future__ import annotations

from pathlib import Path
import importlib.util
import json

from graph import build_graph
from engine import init_state as init_engine_state
from run_logger import RunLogger


def load_sessions(base_dir: Path) -> list[dict]:
    sessions_file = base_dir / "tests" / "sessions" / "session_short.py"
    spec = importlib.util.spec_from_file_location("session_short", sessions_file)
    if spec is None or spec.loader is None:
        raise ValueError("Could not load session file")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sessions = getattr(module, "SESSIONS", None)

    if not isinstance(sessions, list):
        raise ValueError("Session file must contain a list")

    for i, session in enumerate(sessions, start=1):
        if not isinstance(session, dict):
            raise ValueError(f"Session #{i} must be an object")
        if "name" not in session or "queries" not in session:
            raise ValueError(f"Session #{i} must include 'name' and 'queries'")
        if not isinstance(session["queries"], list):
            raise ValueError(f"Session #{i} queries must be a list")
        if "expected_actions" not in session:
            raise ValueError(f"Session #{i} must include 'expected_actions'")
        if not isinstance(session["expected_actions"], list):
            raise ValueError(f"Session #{i} expected_actions must be a list")
        if len(session["expected_actions"]) != len(session["queries"]):
            raise ValueError(
                f"Session #{i} expected_actions length must match queries length"
            )

    return sessions


def main() -> None:
    app = build_graph()
    sessions = load_sessions(Path(__file__).resolve().parent)
    strict_turn_records: list[dict] = []
    strict_session_records: list[dict] = []
    total_correct = 0
    total_turns = 0

    with RunLogger(sessions, Path(__file__).resolve().parent) as run_logger:
        for session in sessions:
            print(f"\n{session['name']}")
            print("=" * len(session["name"]))
            engine_state = init_engine_state()
            expected_actions = session["expected_actions"]
            session_correct = 0
            session_turns = 0

            for i, (q, expected_action) in enumerate(
                zip(session["queries"], expected_actions), start=1
            ):
                out = app.invoke({"query": q, "engine_state": engine_state})
                engine_state = out.get("engine_state", engine_state)

                decision = out.get("decision", {})
                ctx = out.get("context", {})
                mods = engine_state.get("modulators", {})
                goals = engine_state.get("goals", {})
                anti_goals = engine_state.get("anti_goals", {})

                action = decision.get("action", "?")
                strict_correct = int(action == expected_action)
                strict_turn_records.append(
                    {
                        "session": session["name"],
                        "turn": i,
                        "query": q,
                        "expected_action": expected_action,
                        "predicted_action": action,
                        "strict_correct": strict_correct,
                    }
                )
                session_correct += strict_correct
                session_turns += 1
                total_correct += strict_correct
                total_turns += 1
                style_modifier = str(
                    decision.get("style_modifier")
                    if decision.get("style_modifier") is not None
                    else ""
                )
                urgency = float(decision.get("urgency", 0.0))
                resolution = float(decision.get("resolution", 0.0))
                user_expertise = float(decision.get("user_expertise", 0.0))
                threshold = float(decision.get("threshold", 0.0))
                topic_familiarity = float(decision.get("topic_familiarity", 0.0))
                failure_wariness = float(decision.get("failure_wariness", 0.0))
                securing = float(decision.get("securing", 0.0))
                approach = float(decision.get("approach", 0.0))
                arousal = float(decision.get("arousal", 0.0))
                risk_aversion = float(decision.get("risk_aversion", 0.0))
                anti_hall = float(decision.get("anti_hallucinate", 0.0))
                anti_redundant = float(decision.get("anti_redundant", 0.0))
                anti_rabbit_hole = float(decision.get("anti_rabbit_hole", 0.0))
                anti_premature = float(decision.get("anti_premature", 0.0))
                success_moderate = float(decision.get("success_moderate", 0.0))
                knowledge = float(decision.get("knowledge", 0.0))
                novelty = float(decision.get("novelty", 0.0))
                success_breakthrough = float(decision.get("success_breakthrough", 0.0))
                coherence = float(decision.get("coherence", 0.0))
                originality = float(decision.get("originality", 0.0))
                social = float(decision.get("social", 0.0))
                help_short = float(decision.get("help_short", 0.0))
                help_long = float(decision.get("help_long", 0.0))
                over_beneficial = float(decision.get("over_beneficial", 0.0))
                over_safety = float(decision.get("over_safety", 0.0))
                over_honesty = float(decision.get("over_honesty", 0.0))
                confidence = float(decision.get("confidence", 0.0))
                low_confidence = float(decision.get("low_confidence", 0.0))
                intent_type = str(decision.get("intent_type", "mixed"))
                reflective_intent = float(decision.get("reflective_intent", 0.0))
                needs_external_evidence = float(
                    decision.get("needs_external_evidence", 0.0)
                )
                needs_task_plan = float(decision.get("needs_task_plan", 0.0))
                needs_multi_source_integration = float(
                    decision.get("needs_multi_source_integration", 0.0)
                )
                valence = float(decision.get("valence", 0.0))
                error_tolerance = float(decision.get("error_tolerance", 0.0))
                creativity = float(decision.get("creativity", 0.0))
                score_top3 = decision.get("score_top3", [])
                homeo_debug = engine_state.get("homeostasis_debug", {})
                complexity = float(ctx.get("complexity", 0.0))
                ambiguity = float(ctx.get("ambiguity", 0.0))
                expertise = float(ctx.get("expertise", 0.0))
                threshold_signal = float(ctx.get("threshold", 0.0))
                topic_familiarity_signal = float(ctx.get("topic_familiarity", 0.0))
                failure_signal = float(ctx.get("failure_signal", 0.0))
                intent_type_signal = str(ctx.get("intent_type", "mixed"))
                reflective_intent_signal = float(ctx.get("reflective_intent", 0.0))
                needs_external_evidence_signal = float(
                    ctx.get("needs_external_evidence", 0.0)
                )
                needs_task_plan_signal = float(ctx.get("needs_task_plan", 0.0))
                needs_multi_source_integration_signal = float(
                    ctx.get("needs_multi_source_integration", 0.0)
                )
                valence_signal = float(ctx.get("valence", 0.0))
                answer = out.get("answer", "")

                homeo_mode, homeo_trigger_count, homeo_trigger_keys, homeo_suffix = (
                    run_logger.extract_homeostasis(homeo_debug)
                )
                score_parts, score_top3_text = run_logger.format_score_top3(score_top3)
                style_suffix = (
                    f" style={style_modifier}"
                    if action == "act_respond" and style_modifier
                    else ""
                )

                run_logger.log_turn(
                    session_name=session["name"],
                    turn=i,
                    query=q,
                    action=action,
                    style_modifier=style_modifier,
                    intent_type=intent_type,
                    complexity=complexity,
                    ambiguity=ambiguity,
                    threshold=threshold,
                    arousal=arousal,
                    risk_aversion=risk_aversion,
                    resolution=resolution,
                    topic_familiarity=topic_familiarity,
                    confidence=confidence,
                    low_confidence=low_confidence,
                    over_beneficial=over_beneficial,
                    over_safety=over_safety,
                    over_honesty=over_honesty,
                    hallucinate=anti_hall,
                    redundant=anti_redundant,
                    rabbit_hole=anti_rabbit_hole,
                    premature=anti_premature,
                    homeo_mode=homeo_mode,
                    homeo_trigger_count=homeo_trigger_count,
                    homeo_trigger_keys=homeo_trigger_keys,
                    score_top3=score_top3,
                    score_top3_text=score_top3_text,
                    answer=answer,
                    context=ctx,
                    decision=decision,
                    modulators=mods,
                    goals=goals,
                    anti_goals=anti_goals,
                )

                print(
                    f"{i}. {action} | urgent={ctx.get('urgent')} "
                    f"cx={complexity:.2f} amb={ambiguity:.2f} exp={expertise:.2f} "
                    f"thr_s={threshold_signal:.2f} fam_s={topic_familiarity_signal:.2f} fail_s={failure_signal:.2f} "
                    f"intent_s={intent_type_signal} refl_s={reflective_intent_signal:.2f} "
                    f"evid_s={needs_external_evidence_signal:.2f} "
                    f"plan_s={needs_task_plan_signal:.2f} "
                    f"multi_s={needs_multi_source_integration_signal:.2f} "
                    f"val_s={valence_signal:.2f} "
                    f"u={urgency:.2f} r={resolution:.2f} ux={user_expertise:.2f} "
                    f"thr={threshold:.2f} fam={topic_familiarity:.2f} fw={failure_wariness:.2f} sec={securing:.2f} app={approach:.2f} "
                    f"m_r={float(mods.get('resolution', 0.0)):.2f} "
                    f"m_ux={float(mods.get('user_expertise', 0.0)):.2f} "
                    f"m_thr={float(mods.get('threshold', 0.0)):.2f} "
                    f"m_fam={float(mods.get('topic_familiarity', 0.0)):.2f} "
                    f"m_fw={float(mods.get('failure_wariness', 0.0)):.2f} "
                    f"m_sec={float(mods.get('securing', 0.0)):.2f} "
                    f"m_app={float(mods.get('approach', 0.0)):.2f} "
                    f"m_aro={float(mods.get('arousal', 0.0)):.2f} "
                    f"m_risk={float(mods.get('risk_aversion', 0.0)):.2f} "
                    f"m_err={float(mods.get('error_tolerance', 0.0)):.2f} "
                    f"m_cre={float(mods.get('creativity', 0.0)):.2f} "
                    f"m_val={float(mods.get('valence', 0.0)):.2f} "
                    f"g_eff={float(goals.get('efficiency', 0.0)):.2f} "
                    f"g_acc={float(goals.get('accuracy', 0.0)):.2f} "
                    f"g_succ_m={float(goals.get('success_moderate', 0.0)):.2f} "
                    f"g_kn={float(goals.get('knowledge', 0.0)):.2f} "
                    f"g_nov={float(goals.get('novelty', 0.0)):.2f} "
                    f"g_succ_b={float(goals.get('success_breakthrough', 0.0)):.2f} "
                    f"g_coh={float(goals.get('coherence', 0.0)):.2f} "
                    f"g_ori={float(goals.get('originality', 0.0)):.2f} "
                    f"g_soc={float(goals.get('social', 0.0)):.2f} "
                    f"g_help_s={float(goals.get('help_short', 0.0)):.2f} "
                    f"g_help={float(goals.get('help_long', 0.0)):.2f} "
                    f"g_ben={float(goals.get('over_beneficial', 0.0)):.2f} "
                    f"g_safe={float(goals.get('over_safety', 0.0)):.2f} "
                    f"g_hon={float(goals.get('over_honesty', 0.0)):.2f} "
                    f"g_anti_h={float(anti_goals.get('hallucinate', 0.0)):.2f} "
                    f"g_anti_r={float(anti_goals.get('redundant', 0.0)):.2f} "
                    f"g_anti_rh={float(anti_goals.get('rabbit_hole', 0.0)):.2f} "
                    f"g_anti_p={float(anti_goals.get('premature', 0.0)):.2f} "
                    f"anti_h_now={anti_hall:.2f} anti_r_now={anti_redundant:.2f} anti_rh_now={anti_rabbit_hole:.2f} anti_p_now={anti_premature:.2f} "
                    f"succ_m_now={success_moderate:.2f} "
                    f"kn_now={knowledge:.2f} nov_now={novelty:.2f} succ_b_now={success_breakthrough:.2f} "
                    f"coh_now={coherence:.2f} "
                    f"ori_now={originality:.2f} soc_now={social:.2f} "
                    f"help_s_now={help_short:.2f} help_l_now={help_long:.2f} "
                    f"over_b_now={over_beneficial:.2f} over_s_now={over_safety:.2f} over_h_now={over_honesty:.2f} "
                    f"conf={confidence:.2f} low_conf={low_confidence:.2f} "
                    f"intent={intent_type} refl={reflective_intent:.2f} "
                    f"evid={needs_external_evidence:.2f} "
                    f"plan={needs_task_plan:.2f} "
                    f"multi={needs_multi_source_integration:.2f} "
                    f"valence={valence:.2f} "
                    f"arousal={arousal:.2f} risk_aversion={risk_aversion:.2f} "
                    f"err_tol={error_tolerance:.2f} creativity={creativity:.2f}"
                    f"{style_suffix}"
                    f"{homeo_suffix}"
                )
                if score_parts:
                    print("scores_top3: " + " | ".join(score_parts))
                print(answer)
                print("-" * 60)

            session_accuracy = (
                float(session_correct) / float(session_turns) if session_turns else 0.0
            )
            strict_session_records.append(
                {
                    "session": session["name"],
                    "strict_correct": session_correct,
                    "turn_count": session_turns,
                    "strict_accuracy": session_accuracy,
                }
            )

        eval_dir = run_logger.logs_dir / "eval"
        eval_dir.mkdir(parents=True, exist_ok=True)
        strict_per_turn_path = eval_dir / "strict_per_turn.json"
        strict_per_session_path = eval_dir / "strict_per_session.json"
        strict_overall_path = eval_dir / "strict_overall.json"

        overall_accuracy = (
            float(total_correct) / float(total_turns) if total_turns else 0.0
        )
        strict_overall = {
            "strict_correct": total_correct,
            "turn_count": total_turns,
            "strict_accuracy": overall_accuracy,
        }

        with strict_per_turn_path.open("w", encoding="utf-8") as f:
            json.dump(strict_turn_records, f, ensure_ascii=True, indent=2)
        with strict_per_session_path.open("w", encoding="utf-8") as f:
            json.dump(strict_session_records, f, ensure_ascii=True, indent=2)
        with strict_overall_path.open("w", encoding="utf-8") as f:
            json.dump(strict_overall, f, ensure_ascii=True, indent=2)

        print(
            f"\nStrict accuracy: {total_correct}/{total_turns} = {overall_accuracy:.3f}"
        )
        print(f"Saved strict eval files to {eval_dir}")

    print(f"\nSaved logs to {run_logger.logs_dir}")


if __name__ == "__main__":
    main()
