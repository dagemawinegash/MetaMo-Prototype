from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


CSV_FIELDS = [
    "run_id",
    "timestamp",
    "session",
    "turn",
    "query",
    "action",
    "style_modifier",
    "intent_type",
    "complexity",
    "ambiguity",
    "threshold",
    "arousal",
    "risk_aversion",
    "resolution",
    "topic_familiarity",
    "confidence",
    "low_confidence",
    "over_beneficial",
    "over_safety",
    "over_honesty",
    "hallucinate",
    "redundant",
    "rabbit_hole",
    "premature",
    "homeo_mode",
    "homeo_trigger_count",
    "homeo_trigger_keys",
    "score_top3",
    "answer",
]


class RunLogger:
    def __init__(self, sessions: list[dict[str, Any]], base_dir: Path) -> None:
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"run_{run_timestamp}"
        self.logs_dir = base_dir / "logs" / self.run_id
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.turns_json_path = self.logs_dir / "turns.json"
        self.turns_csv_path = self.logs_dir / "turns.csv"
        self.run_meta_path = self.logs_dir / "run_meta.json"

        with self.run_meta_path.open("w", encoding="utf-8") as meta_file:
            json.dump(
                {
                    "run_id": self.run_id,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "sessions": [s.get("name", "") for s in sessions],
                },
                meta_file,
                ensure_ascii=True,
                indent=2,
            )

        self._turn_records: list[dict[str, Any]] = []
        self._turns_json_path = self.turns_json_path
        self._csv_file = self.turns_csv_path.open("w", newline="", encoding="utf-8")
        self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=CSV_FIELDS)
        self._csv_writer.writeheader()

    def close(self) -> None:
        self._csv_file.close()

    def __enter__(self) -> "RunLogger":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    @staticmethod
    def extract_homeostasis(homeo_debug: Any) -> tuple[str, int, list[str], str]:
        homeo_mode = "disabled"
        homeo_trigger_count = 0
        homeo_trigger_keys: list[str] = []
        homeo_suffix = ""

        if isinstance(homeo_debug, dict) and bool(homeo_debug.get("enabled", False)):
            homeo_mode = str(homeo_debug.get("mode", "interior"))
            homeo_trigger_count = int(homeo_debug.get("trigger_count", 0))
            raw_keys = homeo_debug.get("trigger_keys", [])
            homeo_trigger_keys = raw_keys if isinstance(raw_keys, list) else []
            homeo_suffix = f" homeo={homeo_mode}:{homeo_trigger_count}"

        return homeo_mode, homeo_trigger_count, homeo_trigger_keys, homeo_suffix

    @staticmethod
    def format_score_top3(score_top3: Any) -> tuple[list[str], str]:
        score_parts: list[str] = []
        if isinstance(score_top3, list) and score_top3:
            for item in score_top3:
                if (
                    isinstance(item, (list, tuple))
                    and len(item) == 2
                    and isinstance(item[0], str)
                ):
                    try:
                        score_parts.append(f"{item[0]}={float(item[1]):.3f}")
                    except Exception:
                        continue

        return score_parts, " | ".join(score_parts)

    def log_turn(
        self,
        *,
        session_name: str,
        turn: int,
        query: str,
        action: str,
        style_modifier: str,
        intent_type: str,
        complexity: float,
        ambiguity: float,
        threshold: float,
        arousal: float,
        risk_aversion: float,
        resolution: float,
        topic_familiarity: float,
        confidence: float,
        low_confidence: float,
        over_beneficial: float,
        over_safety: float,
        over_honesty: float,
        hallucinate: float,
        redundant: float,
        rabbit_hole: float,
        premature: float,
        homeo_mode: str,
        homeo_trigger_count: int,
        homeo_trigger_keys: list[str],
        score_top3: Any,
        score_top3_text: str,
        answer: str,
        context: dict[str, Any],
        decision: dict[str, Any],
        modulators: dict[str, Any],
        goals: dict[str, Any],
        anti_goals: dict[str, Any],
    ) -> None:
        turn_timestamp = datetime.now().isoformat(timespec="seconds")

        turn_record = {
            "run_id": self.run_id,
            "timestamp": turn_timestamp,
            "session": session_name,
            "turn": turn,
            "query": query,
            "action": action,
            "style_modifier": style_modifier,
            "score_top3": score_top3,
            "context": context,
            "decision": decision,
            "modulators": modulators,
            "goals": goals,
            "anti_goals": anti_goals,
            "homeostasis": {
                "mode": homeo_mode,
                "trigger_count": homeo_trigger_count,
                "trigger_keys": homeo_trigger_keys,
            },
            "answer": answer,
        }
        self._turn_records.append(turn_record)
        with self._turns_json_path.open("w", encoding="utf-8") as turns_file:
            json.dump(self._turn_records, turns_file, ensure_ascii=True, indent=2)

        self._csv_writer.writerow(
            {
                "run_id": self.run_id,
                "timestamp": turn_timestamp,
                "session": session_name,
                "turn": turn,
                "query": query,
                "action": action,
                "style_modifier": style_modifier,
                "intent_type": intent_type,
                "complexity": f"{complexity:.4f}",
                "ambiguity": f"{ambiguity:.4f}",
                "threshold": f"{threshold:.4f}",
                "arousal": f"{arousal:.4f}",
                "risk_aversion": f"{risk_aversion:.4f}",
                "resolution": f"{resolution:.4f}",
                "topic_familiarity": f"{topic_familiarity:.4f}",
                "confidence": f"{confidence:.4f}",
                "low_confidence": f"{low_confidence:.4f}",
                "over_beneficial": f"{over_beneficial:.4f}",
                "over_safety": f"{over_safety:.4f}",
                "over_honesty": f"{over_honesty:.4f}",
                "hallucinate": f"{hallucinate:.4f}",
                "redundant": f"{redundant:.4f}",
                "rabbit_hole": f"{rabbit_hole:.4f}",
                "premature": f"{premature:.4f}",
                "homeo_mode": homeo_mode,
                "homeo_trigger_count": homeo_trigger_count,
                "homeo_trigger_keys": "|".join(homeo_trigger_keys),
                "score_top3": score_top3_text,
                "answer": answer,
            }
        )
        self._csv_file.flush()
