from __future__ import annotations

from pathlib import Path
import copy
import importlib.util
import json

from pipeline.graph import build_graph
from core.state import init_state as init_engine_state
from run_logger import RunLogger
from schemas import LogTurnPayload


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
        acceptable_actions = session.get("acceptable_actions")
        if acceptable_actions is None:
            acceptable_actions = [[] for _ in session["queries"]]
            session["acceptable_actions"] = acceptable_actions
        if not isinstance(acceptable_actions, list):
            raise ValueError(f"Session #{i} acceptable_actions must be a list")
        if len(acceptable_actions) != len(session["queries"]):
            raise ValueError(
                f"Session #{i} acceptable_actions length must match queries length"
            )
        for j, item in enumerate(acceptable_actions, start=1):
            if not isinstance(item, list):
                raise ValueError(
                    f"Session #{i} acceptable_actions turn #{j} must be a list"
                )

    return sessions


def _compute_turn_eval(
    *,
    session_name: str,
    turn_index: int,
    query: str,
    expected_action: str,
    acceptable_for_turn: list[str],
    predicted_action: str,
    soft_credit: float,
) -> dict:
    strict_correct = int(predicted_action == expected_action)
    acceptable_hit = int(predicted_action in acceptable_for_turn and not strict_correct)
    soft_score = 1.0 if strict_correct else (soft_credit if acceptable_hit else 0.0)
    return {
        "session": session_name,
        "turn": turn_index,
        "query": query,
        "expected_action": expected_action,
        "acceptable_actions": acceptable_for_turn,
        "predicted_action": predicted_action,
        "strict_correct": strict_correct,
        "acceptable_hit": acceptable_hit,
        "soft_score": soft_score,
    }


def _build_log_payload(
    *,
    run_logger: RunLogger,
    session_name: str,
    turn_index: int,
    query: str,
    out: dict,
    decision: dict,
    context: dict,
    pre_engine_state: dict,
    updated_engine_state: dict,
    context_memory_enabled: bool,
    context_window_turns: int,
) -> tuple[LogTurnPayload, dict]:
    action = str(decision.get("action", "?"))
    style_modifier = str(
        decision.get("style_modifier")
        if decision.get("style_modifier") is not None
        else ""
    )
    resolution = float(decision.get("resolution", 0.0))
    threshold = float(decision.get("threshold", 0.0))
    topic_familiarity = float(decision.get("topic_familiarity", 0.0))
    arousal = float(decision.get("arousal", 0.0))
    risk_aversion = float(decision.get("risk_aversion", 0.0))
    anti_hall = float(decision.get("anti_hallucinate", 0.0))
    anti_redundant = float(decision.get("anti_redundant", 0.0))
    anti_rabbit_hole = float(decision.get("anti_rabbit_hole", 0.0))
    anti_premature = float(decision.get("anti_premature", 0.0))
    over_beneficial = float(decision.get("over_beneficial", 0.0))
    over_safety = float(decision.get("over_safety", 0.0))
    over_honesty = float(decision.get("over_honesty", 0.0))
    confidence = float(decision.get("confidence", 0.0))
    low_confidence = float(decision.get("low_confidence", 0.0))
    intent_type = str(decision.get("intent_type", "mixed"))
    score_top3 = decision.get("score_top3", [])
    homeo_debug = updated_engine_state.get("homeostasis_debug", {})
    complexity = float(context.get("complexity", 0.0))
    ambiguity = float(context.get("ambiguity", 0.0))
    answer = str(out.get("answer", ""))

    homeo_mode, homeo_trigger_count, homeo_trigger_keys, homeo_suffix = (
        run_logger.extract_homeostasis(homeo_debug)
    )
    score_parts, score_top3_text = run_logger.format_score_top3(score_top3)
    style_suffix = (
        f" style={style_modifier}"
        if action == "act_respond" and style_modifier
        else ""
    )
    decision_min = {
        "action": action,
        "style_modifier": (
            style_modifier
            if action == "act_respond" and style_modifier
            else None
        ),
        "reason": str(decision.get("reason", "")),
        "score_top3": copy.deepcopy(score_top3),
    }
    pre_update = {
        "cold_weight": float(decision.get("cold_weight", 0.0)),
        "modulators": copy.deepcopy(pre_engine_state.get("modulators", {})),
        "goals": copy.deepcopy(pre_engine_state.get("goals", {})),
        "anti_goals": copy.deepcopy(pre_engine_state.get("anti_goals", {})),
    }
    post_update = {
        "modulators": copy.deepcopy(updated_engine_state.get("modulators", {})),
        "goals": copy.deepcopy(updated_engine_state.get("goals", {})),
        "anti_goals": copy.deepcopy(updated_engine_state.get("anti_goals", {})),
    }

    log_payload: LogTurnPayload = {
        "session_name": session_name,
        "turn": turn_index,
        "query": query,
        "action": action,
        "style_modifier": style_modifier,
        "intent_type": intent_type,
        "complexity": complexity,
        "ambiguity": ambiguity,
        "threshold": threshold,
        "arousal": arousal,
        "risk_aversion": risk_aversion,
        "resolution": resolution,
        "topic_familiarity": topic_familiarity,
        "confidence": confidence,
        "low_confidence": low_confidence,
        "over_beneficial": over_beneficial,
        "over_safety": over_safety,
        "over_honesty": over_honesty,
        "hallucinate": anti_hall,
        "redundant": anti_redundant,
        "rabbit_hole": anti_rabbit_hole,
        "premature": anti_premature,
        "homeo_mode": homeo_mode,
        "homeo_trigger_count": homeo_trigger_count,
        "homeo_trigger_keys": homeo_trigger_keys,
        "context_memory_enabled": context_memory_enabled,
        "context_window_turns": context_window_turns,
        "score_top3_text": score_top3_text,
        "answer": answer,
        "context": context,
        "decision": decision_min,
        "pre_update": pre_update,
        "post_update": post_update,
    }
    print_data = {
        "action": action,
        "context_memory_enabled": context_memory_enabled,
        "context_window_turns": context_window_turns,
        "style_suffix": style_suffix,
        "homeo_suffix": homeo_suffix,
        "score_parts": score_parts,
        "answer": answer,
    }
    return log_payload, print_data


def _print_turn_output(*, turn_index: int, print_data: dict) -> None:
    print(
        f"{turn_index}. {print_data['action']}"
        f" | ctx_mem={'on' if print_data['context_memory_enabled'] else 'off'}"
        f" ctx_k={print_data['context_window_turns']}"
        f"{print_data['style_suffix']}"
        f"{print_data['homeo_suffix']}"
    )
    if print_data["score_parts"]:
        print("scores_top3: " + " | ".join(print_data["score_parts"]))
    print(print_data["answer"])
    print("-" * 60)


def _run_single_turn(
    *,
    app,
    run_logger: RunLogger,
    session_name: str,
    turn_index: int,
    query: str,
    expected_action: str,
    acceptable_for_turn: list[str],
    engine_state: dict,
    soft_credit: float,
) -> tuple[dict, dict]:
    pre_engine_state = copy.deepcopy(engine_state)
    out = app.invoke({"query": query, "engine_state": engine_state})
    updated_engine_state = out.get("engine_state", engine_state)

    decision = out.get("decision", {})
    ctx = out.get("context", {})
    params = updated_engine_state.get("params", {})
    context_memory_enabled = bool(params.get("enable_context_memory", False))
    context_window_turns = int(params.get("context_window_turns", 0))

    predicted_action = str(decision.get("action", "?"))
    turn_record = _compute_turn_eval(
        session_name=session_name,
        turn_index=turn_index,
        query=query,
        expected_action=expected_action,
        acceptable_for_turn=acceptable_for_turn,
        predicted_action=predicted_action,
        soft_credit=soft_credit,
    )

    log_payload, print_data = _build_log_payload(
        run_logger=run_logger,
        session_name=session_name,
        turn_index=turn_index,
        query=query,
        out=out,
        decision=decision,
        context=ctx,
        pre_engine_state=pre_engine_state,
        updated_engine_state=updated_engine_state,
        context_memory_enabled=context_memory_enabled,
        context_window_turns=context_window_turns,
    )
    run_logger.log_turn(log_payload)
    _print_turn_output(turn_index=turn_index, print_data=print_data)

    return updated_engine_state, turn_record


def _run_single_session(
    *,
    app,
    run_logger: RunLogger,
    session: dict,
    soft_credit: float,
) -> tuple[list[dict], dict]:
    print(f"\n{session['name']}")
    print("=" * len(session["name"]))
    engine_state = init_engine_state()
    expected_actions = session["expected_actions"]
    acceptable_actions = session["acceptable_actions"]
    session_turn_records: list[dict] = []
    session_correct = 0
    session_turns = 0
    session_soft_score = 0.0

    for turn_index, (query, expected_action, acceptable_for_turn) in enumerate(
        zip(session["queries"], expected_actions, acceptable_actions), start=1
    ):
        engine_state, turn_record = _run_single_turn(
            app=app,
            run_logger=run_logger,
            session_name=session["name"],
            turn_index=turn_index,
            query=query,
            expected_action=expected_action,
            acceptable_for_turn=acceptable_for_turn,
            engine_state=engine_state,
            soft_credit=soft_credit,
        )
        session_turn_records.append(turn_record)
        session_correct += int(turn_record["strict_correct"])
        session_turns += 1
        session_soft_score += float(turn_record["soft_score"])

    session_accuracy = float(session_correct) / float(session_turns) if session_turns else 0.0
    session_record = {
        "session": session["name"],
        "strict_correct": session_correct,
        "turn_count": session_turns,
        "strict_accuracy": session_accuracy,
        "soft_score_sum": session_soft_score,
        "soft_accuracy": (
            float(session_soft_score) / float(session_turns) if session_turns else 0.0
        ),
    }
    return session_turn_records, session_record


def _save_eval_files(
    *,
    eval_dir: Path,
    strict_turn_records: list[dict],
    strict_session_records: list[dict],
    strict_overall: dict,
) -> None:
    strict_per_turn_path = eval_dir / "strict_per_turn.json"
    strict_per_session_path = eval_dir / "strict_per_session.json"
    strict_overall_path = eval_dir / "strict_overall.json"

    with strict_per_turn_path.open("w", encoding="utf-8") as f:
        json.dump(strict_turn_records, f, ensure_ascii=True, indent=2)
    with strict_per_session_path.open("w", encoding="utf-8") as f:
        json.dump(strict_session_records, f, ensure_ascii=True, indent=2)
    with strict_overall_path.open("w", encoding="utf-8") as f:
        json.dump(strict_overall, f, ensure_ascii=True, indent=2)


def main() -> None:
    app = build_graph()
    sessions = load_sessions(Path(__file__).resolve().parent)
    strict_turn_records: list[dict] = []
    strict_session_records: list[dict] = []
    total_correct = 0
    total_turns = 0
    soft_total_score = 0.0
    soft_credit = 0.8

    with RunLogger(sessions, Path(__file__).resolve().parent) as run_logger:
        for session in sessions:
            session_turn_records, session_record = _run_single_session(
                app=app,
                run_logger=run_logger,
                session=session,
                soft_credit=soft_credit,
            )
            strict_turn_records.extend(session_turn_records)
            strict_session_records.append(session_record)
            total_correct += int(session_record["strict_correct"])
            total_turns += int(session_record["turn_count"])
            soft_total_score += float(session_record["soft_score_sum"])

        eval_dir = run_logger.logs_dir / "eval"
        eval_dir.mkdir(parents=True, exist_ok=True)
        overall_accuracy = (
            float(total_correct) / float(total_turns) if total_turns else 0.0
        )
        strict_overall = {
            "strict_correct": total_correct,
            "turn_count": total_turns,
            "strict_accuracy": overall_accuracy,
            "soft_score_sum": soft_total_score,
            "soft_accuracy": (
                float(soft_total_score) / float(total_turns) if total_turns else 0.0
            ),
            "soft_credit_for_acceptable": soft_credit,
        }

        _save_eval_files(
            eval_dir=eval_dir,
            strict_turn_records=strict_turn_records,
            strict_session_records=strict_session_records,
            strict_overall=strict_overall,
        )

        print(
            f"\nStrict accuracy: {total_correct}/{total_turns} = {overall_accuracy:.3f}"
        )
        print(
            f"Soft accuracy: {soft_total_score:.1f}/{total_turns} = {strict_overall['soft_accuracy']:.3f}"
        )
        print(f"Saved eval files to {eval_dir}")

    print(f"\nSaved logs to {run_logger.logs_dir}")


if __name__ == "__main__":
    main()
