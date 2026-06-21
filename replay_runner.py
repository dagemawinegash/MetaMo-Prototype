from __future__ import annotations

import argparse
import copy
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from config import DEFAULT_ABLATION_SWITCHES
from core.decision import post_update, step
from core.state import init_state
from pipeline.parser import _calibrate_action_signals


ABLATION_SWITCH_HELP = {
    "disable_parser_calibration": "Disable parser action-signal calibration.",
    "disable_cold_start": "Disable early-turn cold-start blending.",
    "disable_routing_guards": "Disable post-scoring routing guardrails.",
    "disable_action_arbitration": (
        "Disable evidence, planning, and synthesis arbitration."
    ),
    "disable_action_adjustments": "Disable action-specific scoring adjustments.",
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay a MetaMo run with frozen parser contexts."
    )
    parser.add_argument(
        "--source-run",
        required=True,
        help="Existing run directory containing turns.json and eval files.",
    )
    for switch_name, help_text in ABLATION_SWITCH_HELP.items():
        parser.add_argument(
            f"--{switch_name.replace('_', '-')}",
            action="store_true",
            help=help_text,
        )
    return parser.parse_args(argv)


def _ablation_switches_from_args(args: argparse.Namespace) -> dict[str, bool]:
    return {
        switch_name: bool(getattr(args, switch_name))
        for switch_name in DEFAULT_ABLATION_SWITCHES
    }


def _resolve_source_run(source_run: str, base_dir: Path) -> Path:
    requested_path = Path(source_run).expanduser()
    candidates = [requested_path]
    if not requested_path.is_absolute():
        candidates = [Path.cwd() / requested_path, base_dir / requested_path]

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_dir():
            return resolved

    raise FileNotFoundError(f"Source run directory not found: {source_run}")


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Required replay input not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_source_records(source_run: Path) -> tuple[list[dict], list[dict], dict]:
    turns = _load_json(source_run / "turns.json")
    turn_evaluations = _load_json(source_run / "eval" / "strict_per_turn.json")
    overall_evaluation = _load_json(source_run / "eval" / "strict_overall.json")

    if not isinstance(turns, list) or not isinstance(turn_evaluations, list):
        raise ValueError("Source turns and per-turn evaluation files must contain lists.")
    if not isinstance(overall_evaluation, dict):
        raise ValueError("Source overall evaluation file must contain an object.")
    if len(turns) != len(turn_evaluations):
        raise ValueError(
            "Source turns and per-turn evaluations have different turn counts."
        )
    return turns, turn_evaluations, overall_evaluation


def _index_evaluations(turn_evaluations: list[dict]) -> dict[tuple[str, int], dict]:
    indexed: dict[tuple[str, int], dict] = {}
    for evaluation in turn_evaluations:
        key = (str(evaluation["session"]), int(evaluation["turn"]))
        if key in indexed:
            raise ValueError(f"Duplicate source evaluation for {key}.")
        indexed[key] = evaluation
    return indexed


def _build_replay_context(
    source_context: dict, *, apply_parser_calibration: bool
) -> dict:
    context = copy.deepcopy(source_context)
    calibration_record = context.get("parser_calibration")
    if not isinstance(calibration_record, dict):
        raise ValueError("Source context is missing parser_calibration diagnostics.")

    raw_signals = calibration_record.get("raw")
    if not isinstance(raw_signals, dict):
        raise ValueError("Source context is missing raw parser action signals.")

    evidence = float(raw_signals["needs_external_evidence"])
    task_plan = float(raw_signals["needs_task_plan"])
    multi_source = float(raw_signals["needs_multi_source_integration"])

    if apply_parser_calibration:
        evidence, task_plan, multi_source = _calibrate_action_signals(
            needs_external_evidence=evidence,
            needs_task_plan=task_plan,
            needs_multi_source_integration=multi_source,
            ambiguity=float(context["ambiguity"]),
            intent_type=str(context["intent_type"]),
            reflective_intent=float(context["reflective_intent"]),
        )

    context["needs_external_evidence"] = evidence
    context["needs_task_plan"] = task_plan
    context["needs_multi_source_integration"] = multi_source
    context["parser_calibration"] = {
        "enabled": apply_parser_calibration,
        "raw": copy.deepcopy(raw_signals),
        "output": {
            "needs_external_evidence": evidence,
            "needs_task_plan": task_plan,
            "needs_multi_source_integration": multi_source,
        },
    }
    return context


def _evaluate_turn(
    source_evaluation: dict, predicted_action: str, soft_credit: float
) -> dict:
    expected_action = str(source_evaluation["expected_action"])
    acceptable_actions = [
        str(action) for action in source_evaluation.get("acceptable_actions", [])
    ]
    strict_correct = int(predicted_action == expected_action)
    acceptable_hit = int(
        not strict_correct and predicted_action in acceptable_actions
    )
    soft_score = 1.0 if strict_correct else (soft_credit if acceptable_hit else 0.0)

    return {
        "session": str(source_evaluation["session"]),
        "turn": int(source_evaluation["turn"]),
        "query": str(source_evaluation["query"]),
        "expected_action": expected_action,
        "acceptable_actions": acceptable_actions,
        "predicted_action": predicted_action,
        "strict_correct": strict_correct,
        "acceptable_hit": acceptable_hit,
        "soft_score": soft_score,
    }


def _state_snapshot(state: dict) -> dict:
    return {
        "turn_count": int(state.get("turn_count", 0)),
        "modulators": copy.deepcopy(state.get("modulators", {})),
        "goals": copy.deepcopy(state.get("goals", {})),
        "anti_goals": copy.deepcopy(state.get("anti_goals", {})),
        "homeostasis_debug": copy.deepcopy(state.get("homeostasis_debug", {})),
    }


def _create_output_directory(base_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = base_dir / "logs" / f"replay_{timestamp}"
    suffix = 1
    while output_dir.exists():
        output_dir = base_dir / "logs" / f"replay_{timestamp}_{suffix:02d}"
        suffix += 1
    (output_dir / "eval").mkdir(parents=True)
    return output_dir


def _write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=True, indent=2)


def _build_session_evaluations(turn_evaluations: list[dict]) -> list[dict]:
    session_totals: dict[str, dict[str, float | int | str]] = {}
    for evaluation in turn_evaluations:
        session_name = str(evaluation["session"])
        totals = session_totals.setdefault(
            session_name,
            {
                "session": session_name,
                "strict_correct": 0,
                "turn_count": 0,
                "soft_score_sum": 0.0,
            },
        )
        totals["strict_correct"] = int(totals["strict_correct"]) + int(
            evaluation["strict_correct"]
        )
        totals["turn_count"] = int(totals["turn_count"]) + 1
        totals["soft_score_sum"] = float(totals["soft_score_sum"]) + float(
            evaluation["soft_score"]
        )

    session_evaluations: list[dict] = []
    for totals in session_totals.values():
        turn_count = int(totals["turn_count"])
        strict_correct = int(totals["strict_correct"])
        soft_score_sum = float(totals["soft_score_sum"])
        session_evaluations.append(
            {
                **totals,
                "strict_accuracy": strict_correct / turn_count if turn_count else 0.0,
                "soft_accuracy": soft_score_sum / turn_count if turn_count else 0.0,
            }
        )
    return session_evaluations


def _run_replay(
    *,
    source_turns: list[dict],
    source_evaluations: list[dict],
    ablation_switches: dict[str, bool],
    soft_credit: float,
) -> tuple[list[dict], list[dict]]:
    evaluations_by_turn = _index_evaluations(source_evaluations)
    session_states: dict[str, dict] = {}
    replay_records: list[dict] = []
    replay_evaluations: list[dict] = []
    apply_parser_calibration = not ablation_switches[
        "disable_parser_calibration"
    ]

    for source_turn in source_turns:
        session_name = str(source_turn["session"])
        turn_index = int(source_turn["turn"])
        key = (session_name, turn_index)
        source_evaluation = evaluations_by_turn.get(key)
        if source_evaluation is None:
            raise ValueError(f"No source evaluation found for {key}.")
        if str(source_turn["query"]) != str(source_evaluation["query"]):
            raise ValueError(f"Source query mismatch for {key}.")

        state = session_states.get(session_name)
        if state is None:
            state = init_state()
            state["params"].update(ablation_switches)
            session_states[session_name] = state

        source_context = source_turn.get("context")
        if not isinstance(source_context, dict):
            raise ValueError(f"Source context is missing for {key}.")
        context = _build_replay_context(
            source_context,
            apply_parser_calibration=apply_parser_calibration,
        )

        pre_update = _state_snapshot(state)
        decision = step(context, state)
        predicted_action = str(decision["action"])
        post_update(context, state, decision)
        post_update_snapshot = _state_snapshot(state)

        evaluation = _evaluate_turn(
            source_evaluation,
            predicted_action,
            soft_credit,
        )
        replay_evaluations.append(evaluation)
        replay_records.append(
            {
                "session": session_name,
                "turn": turn_index,
                "query": str(source_turn["query"]),
                "context": context,
                "source_predicted_action": str(
                    source_evaluation.get("predicted_action", "")
                ),
                "decision": copy.deepcopy(decision),
                "pre_update": pre_update,
                "post_update": post_update_snapshot,
            }
        )

    if len(replay_evaluations) != len(evaluations_by_turn):
        raise ValueError("Not every source evaluation was replayed.")
    return replay_records, replay_evaluations


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    base_dir = Path(__file__).resolve().parent
    source_run = _resolve_source_run(args.source_run, base_dir)
    ablation_switches = _ablation_switches_from_args(args)
    source_turns, source_evaluations, source_overall = _load_source_records(
        source_run
    )
    soft_credit = float(source_overall.get("soft_credit_for_acceptable", 0.8))

    replay_records, turn_evaluations = _run_replay(
        source_turns=source_turns,
        source_evaluations=source_evaluations,
        ablation_switches=ablation_switches,
        soft_credit=soft_credit,
    )
    session_evaluations = _build_session_evaluations(turn_evaluations)
    strict_correct = sum(int(item["strict_correct"]) for item in turn_evaluations)
    soft_score_sum = sum(float(item["soft_score"]) for item in turn_evaluations)
    turn_count = len(turn_evaluations)

    overall_evaluation = {
        "strict_correct": strict_correct,
        "turn_count": turn_count,
        "strict_accuracy": strict_correct / turn_count if turn_count else 0.0,
        "soft_score_sum": soft_score_sum,
        "soft_accuracy": soft_score_sum / turn_count if turn_count else 0.0,
        "soft_credit_for_acceptable": soft_credit,
        "source_run": source_run.name,
        "source_session_set": source_overall.get("session_set"),
        "ablation_switches": ablation_switches,
    }

    output_dir = _create_output_directory(base_dir)
    replay_meta = {
        "replay_id": output_dir.name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_run": str(source_run),
        "source_run_id": source_run.name,
        "turn_count": turn_count,
        "ablation_switches": ablation_switches,
        "uses_frozen_parser_contexts": True,
        "runs_parser_llm": False,
        "runs_answer_llm": False,
    }

    _write_json(output_dir / "replay_meta.json", replay_meta)
    _write_json(output_dir / "decisions.json", replay_records)
    _write_json(output_dir / "eval" / "strict_per_turn.json", turn_evaluations)
    _write_json(
        output_dir / "eval" / "strict_per_session.json", session_evaluations
    )
    _write_json(output_dir / "eval" / "strict_overall.json", overall_evaluation)

    print(f"Source run: {source_run}")
    print(f"Ablation switches: {ablation_switches}")
    print(
        f"Strict accuracy: {strict_correct}/{turn_count} = "
        f"{overall_evaluation['strict_accuracy']:.3f}"
    )
    print(
        f"Soft accuracy: {soft_score_sum:.1f}/{turn_count} = "
        f"{overall_evaluation['soft_accuracy']:.3f}"
    )
    print(f"Saved replay to {output_dir}")


if __name__ == "__main__":
    main()
