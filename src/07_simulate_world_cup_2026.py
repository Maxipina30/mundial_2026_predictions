"""
Run the first deterministic World Cup 2026 simulation.

Usage:
    python src/07_simulate_world_cup_2026.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tournament.world_cup_simulator import load_simulator, write_csv


OUT_DIR = BASE_DIR / "data" / "processed" / "simulations" / "world_cup_2026"


def read_existing_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    import csv

    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def frozen_prediction_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {str(row.get("event_id", "")): row for row in rows if row.get("event_id")}


def apply_frozen_prediction(row: dict, frozen: dict[str, str]) -> dict:
    updated = dict(row)
    predicted_home = frozen.get("predicted_home_score") or frozen.get("home_score")
    predicted_away = frozen.get("predicted_away_score") or frozen.get("away_score")
    if predicted_home != "" and predicted_away != "":
        updated["predicted_home_score"] = predicted_home
        updated["predicted_away_score"] = predicted_away
        updated["home_elo"] = frozen.get("home_elo", updated.get("home_elo", ""))
        updated["away_elo"] = frozen.get("away_elo", updated.get("away_elo", ""))
        updated["home_xg"] = frozen.get("home_xg", updated.get("home_xg", ""))
        updated["away_xg"] = frozen.get("away_xg", updated.get("away_xg", ""))
        updated["home_win_90"] = frozen.get("home_win_90", updated.get("home_win_90", ""))
        updated["draw_90"] = frozen.get("draw_90", updated.get("draw_90", ""))
        updated["away_win_90"] = frozen.get("away_win_90", updated.get("away_win_90", ""))
    return updated


def finished_history_rows(
    outputs: dict[str, list[dict]],
    existing_history: list[dict[str, str]] | None = None,
    frozen_predictions: list[dict[str, str]] | None = None,
) -> list[dict]:
    rows = outputs["group_predictions"] + outputs["knockout_predictions"]
    fields = [
        "event_id", "stage", "match_number", "home_team", "away_team",
        "predicted_home_score", "predicted_away_score", "home_score", "away_score",
        "home_elo", "away_elo", "home_xg", "away_xg", "home_win_90", "draw_90",
        "away_win_90", "advancing_team", "venue",
    ]
    existing_lookup = frozen_prediction_lookup(existing_history or [])
    frozen_lookup = frozen_prediction_lookup(frozen_predictions or [])
    history_rows = []
    for row in rows:
        if row.get("result_source") != "actual":
            continue
        event_id = str(row.get("event_id", ""))
        row_with_frozen = apply_frozen_prediction(row, existing_lookup.get(event_id) or frozen_lookup.get(event_id) or {})
        history_rows.append({field: row_with_frozen.get(field, "") for field in fields})
    return history_rows


def main() -> None:
    existing_history = read_existing_rows(OUT_DIR / "prediction_history.csv")
    frozen_predictions = read_existing_rows(OUT_DIR / "knockout_predictions.csv")

    simulator = load_simulator(BASE_DIR)
    outputs = simulator.simulate()
    write_csv(OUT_DIR / "group_predictions.csv", outputs["group_predictions"])
    write_csv(OUT_DIR / "standings.csv", outputs["standings"])
    write_csv(OUT_DIR / "knockout_predictions.csv", outputs["knockout_predictions"])

    history_simulator = load_simulator(BASE_DIR)
    # Las predicciones originales de grupos usaban el Elo normal, antes de que
    # se introdujera la ponderacion extra para la forma del Mundial 2026.
    history_simulator.current_elo_weights["Group"] = 1.0
    history_outputs = history_simulator.simulate()
    write_csv(OUT_DIR / "prediction_history.csv", finished_history_rows(history_outputs, existing_history, frozen_predictions))
    final = [row for row in outputs["knockout_predictions"] if row["stage"] == "Final"]
    champion = final[0]["advancing_team"] if final else "TBD"
    print(f"Group predictions: {len(outputs['group_predictions'])}")
    print(f"Knockout predictions: {len(outputs['knockout_predictions'])}")
    print(f"Champion: {champion}")
    print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
